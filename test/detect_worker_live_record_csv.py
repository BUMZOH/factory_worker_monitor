import csv
import os
import time
from datetime import datetime
from pathlib import Path

# Speed up camera initialization on some USB cameras
os.environ["OPENCV_VIDEOIO_MSMF_ENABLE_HW_TRANSFORMS"] = "0"

import cv2
from ultralytics import YOLO


# ================================================
#   設定
# ================================================
BASE_DIR = Path(__file__).resolve().parent

MODEL_PATH = BASE_DIR / "yolov8n.pt"
CAMERA_NO = 0

CONFIDENCE = 0.5        # default=0.25
IOU_THRESHOLD = 0.3     # default=0.7

# CSV保存
CSV_DIR = BASE_DIR / "csv"
CSV_DIR.mkdir(exist_ok=True)

# 動画保存
MOVIE_DIR = BASE_DIR / "movie"
MOVIE_DIR.mkdir(exist_ok=True)

VIDEO_FPS = 1.0

# 作業エリア ROI1
ROI1_X1 = 150
ROI1_Y1 = 150
ROI1_X2 = 550
ROI1_Y2 = 450


def get_csv_path(measured_at):
    filename = measured_at.strftime(
        "worker_detection_%Y%m%d.csv"
    )
    return CSV_DIR / filename


def write_csv(measured_at, roi1_result):
    csv_path = get_csv_path(measured_at)
    file_exists = csv_path.exists()

    with csv_path.open(
        "a",
        newline="",
        encoding="utf-8",
    ) as csv_file:
        writer = csv.writer(csv_file)

        if not file_exists:
            writer.writerow(
                [
                    "measure_at",
                    "roi1_result",
                ]
            )

        writer.writerow(
            [
                measured_at.strftime("%Y-%m-%d %H:%M:%S"),
                roi1_result,
            ]
        )


def create_video_writer(
    measured_at,
    width,
    height,
):
    video_path = MOVIE_DIR / measured_at.strftime(
        "worker_detection_%Y%m%d_%H%M%S.mp4"
    )

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")

    writer = cv2.VideoWriter(
        str(video_path),
        fourcc,
        VIDEO_FPS,
        (width, height),
    )

    if not writer.isOpened():
        raise RuntimeError("Video file could not be opened.")

    return writer


model = YOLO(MODEL_PATH)

camera = cv2.VideoCapture(CAMERA_NO)

if not camera.isOpened():
    raise RuntimeError("Camera could not be opened.")

# カメラの画像サイズを取得
width = int(camera.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(camera.get(cv2.CAP_PROP_FRAME_HEIGHT))

# 動画保存開始
video_start_at = datetime.now()
video_date = video_start_at.date()

video_writer = create_video_writer(
    video_start_at,
    width,
    height,
)

# 最後にCSV・動画へ保存した時刻
last_record_time = 0.0


try:
    while True:
        success, frame = camera.read()

        if not success:
            break

        # YOLOによる人物検出
        # 毎フレーム実行する
        result = model.predict(
            source=frame,
            classes=[0],        # person を検出
            conf=CONFIDENCE,
            iou=IOU_THRESHOLD,
            verbose=False,
        )[0]

        roi1_detected = False

        for box in result.boxes:
            x1, y1, x2, y2 = box.xyxy[0].tolist()

            center_x = int((x1 + x2) / 2)
            center_y = int((y1 + y2) / 2)

            if (
                ROI1_X1 <= center_x <= ROI1_X2
                and ROI1_Y1 <= center_y <= ROI1_Y2
            ):
                roi1_detected = True

            # 人物のバウンディングボックス
            cv2.rectangle(
                frame,
                (int(x1), int(y1)),
                (int(x2), int(y2)),
                (0, 255, 0),
                2,
            )

            # 人物の中心点
            cv2.circle(
                frame,
                (center_x, center_y),
                5,
                (0, 0, 255),
                -1,
            )

        # 作業エリア ROI1を描画
        cv2.rectangle(
            frame,
            (ROI1_X1, ROI1_Y1),
            (ROI1_X2, ROI1_Y2),
            (255, 0, 0),
            3,
        )

        # 検出状態
        status = (
            "ROI1: DETECTED"
            if roi1_detected
            else "ROI1: NOT DETECTED"
        )

        cv2.putText(
            frame,
            status,
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.0,
            (0, 0, 255),
            2,
        )

        # ----------------------------------------
        # CSV・動画保存
        # ----------------------------------------
        # YOLO検出と画面表示は毎フレーム行うが、
        # CSVとMP4への記録は1秒に1回だけ行う
        now = time.monotonic()

        if now - last_record_time >= 1.0:
            measured_at = datetime.now()

            roi1_result = 1 if roi1_detected else 0

            write_csv(
                measured_at,
                roi1_result,
            )

            # 日付が変わったら動画ファイルを切り替える
            if measured_at.date() != video_date:
                video_writer.release()

                video_writer = create_video_writer(
                    measured_at,
                    width,
                    height,
                )

                video_date = measured_at.date()

            video_writer.write(frame)

            last_record_time = now

        # 画面表示は毎フレーム
        cv2.imshow("Person Detection", frame)

        key = cv2.waitKey(1)

        if key == 27:   # ESCキー押下時
            break

finally:
    # 動画ファイルを閉じる
    video_writer.release()

    # カメラを閉じる
    camera.release()

    cv2.destroyAllWindows()
