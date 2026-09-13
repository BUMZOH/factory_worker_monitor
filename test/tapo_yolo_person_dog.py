import json
import os
import time
from pathlib import Path
from urllib.parse import quote

import cv2
from ultralytics import YOLO


# ================================================
#   Settings
# ================================================
BASE_DIR = Path(__file__).resolve().parent

MODEL_PATH = BASE_DIR / "yolov8n.pt"
CONFIG_PATH = BASE_DIR / "camera_config.json"

CONFIDENCE = 0.25
IOU_THRESHOLD = 0.3

DISPLAY_WIDTH = 1600
DISPLAY_HEIGHT = 900

# COCO class IDs
PERSON_CLASS_ID = 0
DOG_CLASS_ID = 16


# ================================================
#   RTSP settings
# ================================================
# Use TCP for more stable RTSP communication.
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"


def load_camera_config():
    """Load camera settings from JSON file."""

    with open(
        CONFIG_PATH,
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def create_rtsp_url(config):
    """Create the RTSP URL for the Tapo camera."""

    username = quote(
        config["username"],
        safe="",
    )

    password = quote(
        config["password"],
        safe="",
    )

    return (
        f"rtsp://{username}:{password}"
        f"@{config['camera_ip']}"
        f":{config['camera_port']}"
        f"/stream{config['stream_no']}"
    )


def resize_for_display(frame):
    """Resize a frame while preserving its aspect ratio."""

    height, width = frame.shape[:2]

    scale = min(
        DISPLAY_WIDTH / width,
        DISPLAY_HEIGHT / height,
    )

    new_width = int(width * scale)
    new_height = int(height * scale)

    return cv2.resize(
        frame,
        (new_width, new_height),
        interpolation=cv2.INTER_AREA,
    )


def main():
    """Detect people and dogs from the Tapo camera."""

    config = load_camera_config()

    model = YOLO(MODEL_PATH)

    rtsp_url = create_rtsp_url(config)

    cap = cv2.VideoCapture(
        rtsp_url,
        cv2.CAP_FFMPEG,
    )

    if not cap.isOpened():
        print("Failed to open the camera.")
        return

    print("Camera connected.")
    print("Detecting: person, dog")
    print("Press ESC to exit.")

    frame_count = 0
    start_time = time.monotonic()

    while True:
        ret, frame = cap.read()

        if not ret:
            print("Failed to receive frame.")
            break

        results = model.predict(
            source=frame,
            conf=CONFIDENCE,
            iou=IOU_THRESHOLD,
            classes=[
                PERSON_CLASS_ID,
                DOG_CLASS_ID,
            ],
            verbose=False,
        )

        result_frame = results[0].plot()

        display_frame = resize_for_display(result_frame)

        frame_count += 1
        elapsed_time = time.monotonic() - start_time

        if elapsed_time >= 1.0:
            processing_fps = frame_count / elapsed_time

            print(f"Processing FPS: {processing_fps:.1f}")

            frame_count = 0
            start_time = time.monotonic()

        cv2.imshow(
            "Tapo YOLO - Person and Dog Detection",
            display_frame,
        )

        key = cv2.waitKey(1) & 0xFF

        if key == 27:
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()