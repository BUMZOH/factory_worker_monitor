import csv
import os
import time
from datetime import datetime
from pathlib import Path

# Speed up camera initialization on some USB cameras
# (Especially necessary when using Logitech USB cameras.)
os.environ["OPENCV_VIDEOIO_MSMF_ENABLE_HW_TRANSFORMS"] = "0"

import cv2
from ultralytics import YOLO


# ================================================
#   Settings
# ================================================
BASE_DIR = Path(__file__).resolve().parent

MODEL_PATH = BASE_DIR / "yolov8n.pt"
CAMERA_NO = 0

CONFIDENCE = 0.5        # default=0.25
IOU_THRESHOLD = 0.3     # default=0.7

# CSV settings
CSV_DIR = BASE_DIR / "csv"
CSV_DIR.mkdir(exist_ok=True)

# Video settings
MOVIE_DIR = BASE_DIR / "movie"
MOVIE_DIR.mkdir(exist_ok=True)

VIDEO_FPS = 1.0
VIDEO_HEIGHT = 600      # Width is calculated automatically.

# Working area ROI1
ROI1_ENABLE = True
ROI1_X1 = 150
ROI1_Y1 = 150
ROI1_X2 = 550
ROI1_Y2 = 450

# Working area ROI2
ROI2_ENABLE = True
ROI2_X1 = 600
ROI2_Y1 = 150
ROI2_X2 = 800
ROI2_Y2 = 450


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
def get_csv_path(measured_at: datetime) -> Path:
    filename = measured_at.strftime(
        "worker_detection_%Y%m%d.csv"
    )
    return CSV_DIR / filename


def write_csv(
    measured_at: datetime,
    roi1_result: int,
    roi2_result: int,
) -> None:
    csv_path = get_csv_path(measured_at)
    file_exists = csv_path.exists()

    with csv_path.open("a", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)

        if not file_exists:
            writer.writerow(
                [
                    "measured_at",
                    "roi1_result",
                    "roi2_result",
                ]
            )

        writer.writerow(
            [
                measured_at.strftime("%Y-%m-%d %H:%M:%S"),
                roi1_result,
                roi2_result,
            ]
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
model = YOLO(MODEL_PATH)

camera = cv2.VideoCapture(CAMERA_NO)

if not camera.isOpened():
    raise RuntimeError("Camera could not be opened.")

# Set camera resolution.
# (Check the resolutions available in the Windows Camera app.)
camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

# Get the camera image size.
width = int(camera.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(camera.get(cv2.CAP_PROP_FRAME_HEIGHT))

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


try:
    while True:
        success, frame = camera.read()

        if not success:
            break

        # Detect persons using YOLO on every frame.
        result = model.predict(
            source=frame,
            classes=[0],        # Detect persons only.
            conf=CONFIDENCE,
            iou=IOU_THRESHOLD,
            verbose=False,      # Disable detailed output.
        )[0]

        roi1_detected = False
        roi2_detected = False

        for box in result.boxes:
            # Get the bounding box coordinates.
            x1, y1, x2, y2 = box.xyxy[0].tolist()

            center_x = int((x1 + x2) / 2)
            center_y = int((y1 + y2) / 2)

            if ROI1_ENABLE:
                if (
                    ROI1_X1 <= center_x <= ROI1_X2
                    and ROI1_Y1 <= center_y <= ROI1_Y2
                ):
                    roi1_detected = True

            if ROI2_ENABLE:
                if (
                    ROI2_X1 <= center_x <= ROI2_X2
                    and ROI2_Y1 <= center_y <= ROI2_Y2
                ):
                    roi2_detected = True

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

        # Draw the ROI1 work area.
        if ROI1_ENABLE:
            cv2.rectangle(
                frame,
                (ROI1_X1, ROI1_Y1),
                (ROI1_X2, ROI1_Y2),
                CV2_BLUE,
                3,                      # Thickness
            )

        # Draw the ROI2 work area.
        if ROI2_ENABLE:
            cv2.rectangle(
                frame,
                (ROI2_X1, ROI2_Y1),
                (ROI2_X2, ROI2_Y2),
                CV2_YELLOW,
                3,                      # Thickness
            )

        # ROI1 detection status
        if ROI1_ENABLE:
            roi1_status = (
                "ROI1: DETECTED"
                if roi1_detected
                else "ROI1: NOT DETECTED"
            )
        else:
            roi1_status = "ROI1: DISABLED"

        cv2.putText(
            frame,
            roi1_status,
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.0,
            CV2_RED,
            2,
        )

        # ROI2 detection status
        if ROI2_ENABLE:
            roi2_status = (
                "ROI2: DETECTED"
                if roi2_detected
                else "ROI2: NOT DETECTED"
            )
        else:
            roi2_status = "ROI2: DISABLED"

        cv2.putText(
            frame,
            roi2_status,
            (20, 80),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.0,
            CV2_RED,
            2,
        )

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
            0.6,
            CV2_WHITE,
            1,
        )

        # ----------------------------------------
        # Save CSV and video
        # ----------------------------------------
        # Run YOLO detection and display every frame,
        # but save CSV and MP4 only once per second.

        now = time.monotonic()  # Get the monotonic time in seconds.

        if now - last_record_time >= 1.0:
            measured_at = datetime.now()

            roi1_result = 1 if roi1_detected else 0
            roi2_result = 1 if roi2_detected else 0

            write_csv(
                measured_at,
                roi1_result,
                roi2_result,
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


        # Display every frame.
        cv2.imshow("Person Detection", frame)

        key = cv2.waitKey(1)

        if key == 27:   # key = ESC
            break


finally:
    # Release the video writer.
    video_writer.release()

    # Close the camera.
    camera.release()

    cv2.destroyAllWindows()


