import os
import time
from datetime import datetime
from pathlib import Path

# Speed up camera initialization on some USB cameras
os.environ["OPENCV_VIDEOIO_MSMF_ENABLE_HW_TRANSFORMS"] = "0"

import cv2
from ultralytics import YOLO


#================================================
#   設定
#================================================
BASE_DIR = Path(__file__).resolve().parent

MODEL_PATH = BASE_DIR / "yolov8n.pt"
CAMERA_NO = 0

CONFIDENCE = 0.5        # default=0.25
IOU_THRESHOLD = 0.3     # default=0.7

# 動画保存
MOVIE_DIR = BASE_DIR / "movie"
MOVIE_DIR.mkdir(exist_ok=True)
VIDEO_PATH = MOVIE_DIR / datetime.now().strftime(
    "worker_detection_%Y%m%d_%H%M%S.mp4"
)

VIDEO_FPS = 1.0

# 作業エリア
ROI_X1 = 150
ROI_Y1 = 150
ROI_X2 = 550
ROI_Y2 = 450


model = YOLO(MODEL_PATH)

camera = cv2.VideoCapture(CAMERA_NO)

if not camera.isOpened():
    raise RuntimeError("Camera could not be opened.")

# カメラの画像サイズを取得
width = int(camera.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(camera.get(cv2.CAP_PROP_FRAME_HEIGHT))

# MP4動画の保存設定
fourcc = cv2.VideoWriter_fourcc(*"mp4v")

video_writer = cv2.VideoWriter(
    str(VIDEO_PATH),
    fourcc,
    VIDEO_FPS,
    (width, height),
)

if not video_writer.isOpened():
    raise RuntimeError("Video file could not be opened.")

working = False
work_start_time = None
total_work_time = 0.0

# 最後に動画へ保存した時刻
last_record_time = 0.0


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
        verbose=False,      # コンソールへのログ出力を無効
    )[0]                    # source が画像1つの場合は [0]

    person_in_area = False

    for box in result.boxes:
        x1, y1, x2, y2 = box.xyxy[0].tolist()

        center_x = int((x1 + x2) / 2)
        center_y = int((y1 + y2) / 2)

        if (
            ROI_X1 <= center_x <= ROI_X2
            and ROI_Y1 <= center_y <= ROI_Y2
        ):
            person_in_area = True

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

    # 現在時刻を取得
    now = time.monotonic()

    # 作業時間の計測
    if person_in_area:
        if not working:
            working = True
            work_start_time = now

    else:
        if working:
            total_work_time += now - work_start_time
            working = False
            work_start_time = None

    current_work_time = total_work_time

    if working:
        current_work_time += now - work_start_time

    # 作業エリアを描画
    cv2.rectangle(
        frame,
        (ROI_X1, ROI_Y1),
        (ROI_X2, ROI_Y2),
        (255, 0, 0),
        3,
    )

    # 作業状態
    status = "WORKING" if person_in_area else "NO PERSON"

    cv2.putText(
        frame,
        status,
        (20, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.0,
        (0, 0, 255),
        2,
    )

    # 作業時間
    cv2.putText(
        frame,
        f"Work Time: {current_work_time:.1f} sec",
        (20, 80),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (0, 0, 255),
        2,
    )

    # ----------------------------------------
    # 動画保存
    # ----------------------------------------
    # YOLO検出と画面表示は毎フレーム行うが、
    # MP4への保存は1秒に1回だけ行う
    if now - last_record_time >= 1.0:
        video_writer.write(frame)
        last_record_time = now

    # 画面表示は毎フレーム
    cv2.imshow("Person Detection", frame)

    key = cv2.waitKey(1)

    if key == 27:   # ESCキー押下時
        break


# 動画ファイルを閉じる
video_writer.release()

# カメラを閉じる
camera.release()

cv2.destroyAllWindows()