import json
import os
import time
from pathlib import Path
from urllib.parse import quote

import cv2


# ================================================
#   File settings
# ================================================
BASE_DIR = Path(__file__).resolve().parent

CONFIG_PATH = BASE_DIR / "camera_config.json"


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


def main():
    """Display live video from the Tapo camera."""

    config = load_camera_config()

    rtsp_url = create_rtsp_url(config)

    cap = cv2.VideoCapture(
        rtsp_url,
        cv2.CAP_FFMPEG,
    )

    if not cap.isOpened():
        print("Failed to open the camera.")
        return

    camera_fps = cap.get(cv2.CAP_PROP_FPS)

    print("Camera connected.")
    print(f"Camera reported FPS: {camera_fps:.1f}")
    print("Press ESC to exit.")

    frame_count = 0
    start_time = time.monotonic()

    while True:
        ret, frame = cap.read()

        if not ret:
            print("Failed to receive frame.")
            break

        frame_count += 1
        elapsed_time = time.monotonic() - start_time

        if elapsed_time >= 1.0:
            actual_fps = frame_count / elapsed_time

            print(
                f"Actual received FPS: "
                f"{actual_fps:.1f}"
            )

            frame_count = 0
            start_time = time.monotonic()

        cv2.imshow(
            "Tapo Camera",
            frame,
        )

        key = cv2.waitKey(1) & 0xFF

        if key == 27:
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()