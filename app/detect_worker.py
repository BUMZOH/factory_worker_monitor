import csv
import json
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import quote
import shutil
import threading

from create_worker_timeline import save_timeline_image
from worker_position_scatter import save_worker_position_scatter

# Speed up camera initialization on some USB cameras
# (Especially necessary when using Logitech USB cameras.)
os.environ["OPENCV_VIDEOIO_MSMF_ENABLE_HW_TRANSFORMS"] = "0"

# Use TCP for more stable RTSP communication.
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"

import cv2
from ultralytics import YOLO


# ================================================
#   Settings
# ================================================
BASE_DIR = Path(__file__).resolve().parent

MODEL_PATH = BASE_DIR / "yolov8n.pt"
SETTINGS_PATH = BASE_DIR / "settings.json"
LOGIN_PATH = BASE_DIR / "network_camera_login.json"

# Camera type: "usb" or "network"
CAMERA_TYPE = "network"

# USB camera number
CAMERA_NO = 0

CONFIDENCE = 0.25       # default=0.25
IOU_THRESHOLD = 0.3     # default=0.7

# CSV settings
CSV_DIR = BASE_DIR / "csv"
CSV_DIR.mkdir(exist_ok=True)

# USB camera settings
# (Check the resolutions available in the Windows Camera app.)
CAMERA_WIDTH = 1920
CAMERA_HEIGHT = 1080

# Save raw camera image at startup.
SAVE_IMAGE = True
IMAGE_DIR = BASE_DIR / "image"
IMAGE_DIR.mkdir(exist_ok=True)
IMAGE_PATH = IMAGE_DIR / "camera_image.png"

# Report image settings
IMAGE_UPDATE_INTERVAL = 300

REMOTE_IMAGE_DIR = Path(
    r"\\192.168.2.1\共有ファイル\M-光和共有ファイル"
    r"\P_ProductControl\yolo_detection_data\main_factory"
)

# Video settings
MOVIE_DIR = BASE_DIR / "movie"
MOVIE_DIR.mkdir(exist_ok=True)

VIDEO_FPS = 1.0
VIDEO_HEIGHT = 540      # Width is calculated automatically.

# Display settings
# (Set DISPLAY_HEIGHT smaller to allow for the taskbar and title bar.)
DISPLAY_HEIGHT = 1000   # Width is calculated automatically.


# ================================================
#   Constants
# ================================================
# OpenCV colors (BGR)
CV2_BLACK = (0, 0, 0)
CV2_WHITE = (255, 255, 255)
CV2_RED = (0, 0, 255)
CV2_GREEN = (0, 255, 0)
CV2_BLUE = (255, 0, 0)
CV2_YELLOW = (0, 255, 255)
CV2_CYAN = (255, 255, 0)
CV2_MAGENTA = (255, 0, 255)
CV2_ORANGE = (0, 165, 255)
CV2_GRAY = (128, 128, 128)


# ================================================
#   Functions
# ================================================
def load_settings() -> dict:
    """Load application settings from JSON file."""
    with SETTINGS_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def load_network_camera_login() -> dict:
    """Load network camera login information from JSON file."""
    with LOGIN_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)
    

def create_rtsp_url(
    config: dict,
    login: dict,
) -> str:
    """Create the RTSP URL for the network camera."""
    username = quote(login["username"], safe="")
    password = quote(login["password"], safe="")

    return (
        f"rtsp://{username}:{password}"
        f"@{config['camera_ip']}:{config['camera_port']}"
        f"/stream{config['stream_no']}"
    )


def open_camera():
    """Open the selected USB or network camera."""
    if CAMERA_TYPE == "usb":
        camera = cv2.VideoCapture(CAMERA_NO)

        if not camera.isOpened():
            raise RuntimeError("USB camera could not be opened.")

        camera.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)

        print(f"Camera type: USB (No. {CAMERA_NO})")

        return camera

    if CAMERA_TYPE == "network":
        settings = load_settings()
        config = settings["network_camera"]
        login = load_network_camera_login()

        rtsp_url = create_rtsp_url(
            config,
            login,
        )

        camera = cv2.VideoCapture(
            rtsp_url,
            cv2.CAP_FFMPEG,
        )

        if not camera.isOpened():
            raise RuntimeError("Network camera could not be opened.")

        print("Camera type: Network")
        print(
            f"Camera address: "
            f"{config['camera_ip']}:{config['camera_port']}"
        )
        print(f"RTSP stream: stream{config['stream_no']}")

        return camera

    raise ValueError(
        'CAMERA_TYPE must be "usb" or "network".'
    )


def get_factory_date(measured_at: datetime) -> str:
    """Return the factory date as YYYYMMDD."""
    factory_date = measured_at

    if measured_at.hour < 4:
        factory_date = measured_at - timedelta(days=1)

    return factory_date.strftime("%Y%m%d")


def copy_image_to_remote(image_path: Path) -> None:
    """Copy a report image to the remote directory."""
    remote_path = REMOTE_IMAGE_DIR / image_path.name

    try:
        shutil.copy2(image_path, remote_path)
    except Exception as error:
        print(
            f"Remote image copy failed: "
            f"{image_path.name}: {error}"
        )


def image_update_worker(
        stop_event: threading.Event,
        remote_copy_enabled: bool,
) -> None:
    """Update report images periodically."""
    while not stop_event.wait(IMAGE_UPDATE_INTERVAL):
        target_date = get_factory_date(datetime.now())

        try:
            image_path = save_timeline_image(target_date)

            if remote_copy_enabled:
                copy_image_to_remote(image_path)

        except Exception as error:
            print(f"Timeline image update failed: {error}")

        try:
            image_path = save_worker_position_scatter(target_date)

            if remote_copy_enabled:
                copy_image_to_remote(image_path)

        except Exception as error:
            print(f"Scatter image update failed: {error}")


def get_raw_detection_csv_path(measured_at: datetime) -> Path:
    """Return the raw detection CSV path for the factory date."""
    factory_date = measured_at

    if measured_at.hour < 4:
        factory_date = measured_at - timedelta(days=1)

    filename = factory_date.strftime(
        "detection_raw_data_%Y%m%d.csv"
    )

    return CSV_DIR / filename


def write_raw_detection_csv(
    measured_at: datetime,
    detections: list[tuple[int, int, float]],
) -> None:
    """Write raw YOLO detection results to CSV."""
    csv_path = get_raw_detection_csv_path(measured_at)
    file_exists = csv_path.exists()

    with csv_path.open("a", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)

        if not file_exists:
            writer.writerow(
                [
                    "measured_at",
                    "center_x",
                    "center_y",
                    "confidence",
                ]
            )

        if not detections:
            writer.writerow(
                [
                    measured_at.strftime("%Y-%m-%d %H:%M:%S"),
                    "",
                    "",
                    "",
                ]
            )
            return

        for center_x, center_y, confidence in detections:
            writer.writerow(
                [
                    measured_at.strftime("%Y-%m-%d %H:%M:%S"),
                    center_x,
                    center_y,
                    f"{confidence:.6f}",
                ]
            )


def draw_grid(frame, rows: int, cols: int) -> None:
    """Draw the area grid on the camera image."""
    height, width = frame.shape[:2]

    cell_width = width / cols
    cell_height = height / rows

    for col in range(1, cols):
        x = int(col * cell_width)

        cv2.line(
            frame,
            (x, 0),
            (x, height),
            CV2_WHITE,
            1,
        )

    for row in range(1, rows):
        y = int(row * cell_height)

        cv2.line(
            frame,
            (0, y),
            (width, y),
            CV2_WHITE,
            1,
        )

    for row in range(rows):
        for col in range(cols):
            x = int(col * cell_width) + 10
            y = int(row * cell_height) + 30

            cv2.putText(
                frame,
                f"{row},{col}",
                (x, y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                CV2_YELLOW,
                2,
            )


def create_video_writer(
    measured_at: datetime,
    width: int,
    height: int,
) -> tuple[cv2.VideoWriter, datetime]:
    """Create an MP4 video writer for the specified hour."""

    # Use the start of the hour as the filename.
    hour_start = measured_at.replace(
        minute=0,
        second=0,
        microsecond=0,
    )

    base_name = hour_start.strftime("%Y%m%d_%H00")
    video_path = MOVIE_DIR / f"{base_name}.mp4"

    # Add a sequential number to the filename if it already exists.
    file_no = 2

    while video_path.exists():
        video_path = MOVIE_DIR / f"{base_name}_{file_no}.mp4"
        file_no += 1

    # Set the MP4 video codec.
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")

    # Create the video writer.
    writer = cv2.VideoWriter(
        str(video_path),
        fourcc,
        VIDEO_FPS,
        (width, height),
    )

    if not writer.isOpened():
        raise RuntimeError("Video file could not be opened.")

    return writer, hour_start


# ================================================
#   Main Process
# ================================================
settings = load_settings()

remote_copy_enabled = settings["remote_copy_enabled"]

grid_settings = settings["grid"]
grid_rows = grid_settings["rows"]
grid_cols = grid_settings["cols"]

model = YOLO(MODEL_PATH)

camera = open_camera()

# Get the camera image size.
width = int(camera.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(camera.get(cv2.CAP_PROP_FRAME_HEIGHT))

if width <= 0 or height <= 0:
    raise RuntimeError("Camera resolution could not be obtained.")

# Calculate the video resolution.
video_height = VIDEO_HEIGHT
video_width = int(width * video_height / height)

# Make the width an even number.
if video_width % 2 != 0:
    video_width -= 1

print(f"Camera resolution: {width} x {height}")
print(f"Video resolution: {video_width} x {video_height}")

# Start video recording.
video_start_at = datetime.now()

video_writer, video_hour_start = create_video_writer(
    video_start_at,
    video_width,
    video_height,
)

# Time when the CSV and video were last saved.
last_record_time = 0.0

# Whether the raw camera image has already been saved.
image_saved = False


# Start the report image update thread.
stop_event = threading.Event()

image_thread = threading.Thread(
    target=image_update_worker,
    args=(stop_event, remote_copy_enabled),
    daemon=True,
)
image_thread.start()


try:
    while True:
        success, frame = camera.read()

        if not success:
            print(
                "Camera read failed: "
                f"{datetime.now():%Y-%m-%d %H:%M:%S}"
            )
            break

        # Save the raw camera image only once at startup.
        if SAVE_IMAGE and not image_saved:
            cv2.imwrite(
                str(IMAGE_PATH),
                frame,
            )

            image_saved = True

        # Detect persons using YOLO on every frame.
        result = model.predict(
            source=frame,
            classes=[0],        # Detect persons only.
            conf=CONFIDENCE,
            iou=IOU_THRESHOLD,
            verbose=False,      # Disable detailed output.
        )[0]


        raw_detections = []

        for box in result.boxes:
            # Get the bounding box coordinates.
            x1, y1, x2, y2 = box.xyxy[0].tolist()

            center_x = int((x1 + x2) / 2)
            center_y = int((y1 + y2) / 2)
            confidence = float(box.conf[0])

            raw_detections.append(
                (
                    center_x,
                    center_y,
                    confidence,
                )
            )


            # Person bounding box
            cv2.rectangle(
                frame,
                (int(x1), int(y1)),
                (int(x2), int(y2)),
                CV2_GREEN,
                2,                      # Thickness
            )

            # Person center point
            cv2.circle(
                frame,
                (center_x, center_y),
                5,                      # Radius
                CV2_RED,
                -1,                     # Filled circle
            )


        draw_grid(frame, grid_rows, grid_cols)

        # Display the current datetime.
        display_at = datetime.now()
        timestamp_text = display_at.strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        cv2.putText(
            frame,
            timestamp_text,
            (20, height - 20),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.0,
            CV2_WHITE,
            2,
        )

        # ----------------------------------------
        # Save CSV and video
        # ----------------------------------------
        # Run YOLO detection and display every frame,
        # but save CSV and MP4 only once per second.

        now = time.monotonic()

        if now - last_record_time >= 1.0:
            measured_at = datetime.now()

            write_raw_detection_csv(
                measured_at,
                raw_detections,
            )

            # Switch the video file every hour.
            current_hour_start = measured_at.replace(
                minute=0,
                second=0,
                microsecond=0,
            )

            if current_hour_start != video_hour_start:
                video_writer.release()

                video_writer, video_hour_start = create_video_writer(
                    measured_at,
                    video_width,
                    video_height,
                )

            video_frame = cv2.resize(
                frame,
                (video_width, video_height),
            )

            video_writer.write(video_frame)

            last_record_time = now

        # Resize only for display.
        display_height = DISPLAY_HEIGHT
        display_width = int(width * display_height / height)

        display_frame = cv2.resize(
            frame,
            (display_width, display_height),
        )

        # Display every frame.
        cv2.imshow("Person Detection", display_frame)

        key = cv2.waitKey(1)

        if key == 27:   # key = ESC
            break

        time.sleep(0.1)

finally:
    # Stop the report image update thread.
    stop_event.set()
    image_thread.join(timeout=5.0)
    
    # Release the video writer.
    video_writer.release()

    # Close the camera.
    camera.release()

    cv2.destroyAllWindows()
