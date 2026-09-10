import time

import cv2
from ultralytics import YOLO


MODEL_PATH = "yolov8n.pt"
CAMERA_NO = 0

CONFIDENCE = 0.5

# 作業エリア
ROI_X1 = 150
ROI_Y1 = 150
ROI_X2 = 550
ROI_Y2 = 450

# 確認用動画
OUTPUT_PATH = "movie/detection_result.mp4"
OUTPUT_WIDTH = 960
OUTPUT_HEIGHT = 540
OUTPUT_FPS = 5.0


model = YOLO(MODEL_PATH)

camera = cv2.VideoCapture(CAMERA_NO)

if not camera.isOpened():
    raise RuntimeError("カメラを開けませんでした")

fourcc = cv2.VideoWriter_fourcc(*"mp4v")

writer = cv2.VideoWriter(
    OUTPUT_PATH,
    fourcc,
    OUTPUT_FPS,
    (OUTPUT_WIDTH, OUTPUT_HEIGHT),
)

if not writer.isOpened():
    raise RuntimeError("確認用動画を作成できませんでした")

working = False
work_start_time = None
total_work_time = 0.0

save_interval = 1.0 / OUTPUT_FPS
last_save_time = 0.0


while True:
    success, frame = camera.read()

    if not success:
        break

    result = model.predict(
        source=frame,
        classes=[0],
        conf=CONFIDENCE,
        verbose=False,
    )[0]

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

        cv2.rectangle(
            frame,
            (int(x1), int(y1)),
            (int(x2), int(y2)),
            (0, 255, 0),
            2,
        )

        cv2.circle(
            frame,
            (center_x, center_y),
            5,
            (0, 0, 255),
            -1,
        )

    now = time.monotonic()

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

    cv2.rectangle(
        frame,
        (ROI_X1, ROI_Y1),
        (ROI_X2, ROI_Y2),
        (255, 0, 0),
        3,
    )

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

    cv2.putText(
        frame,
        f"Work Time: {current_work_time:.1f} sec",
        (20, 80),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (0, 0, 255),
        2,
    )

    cv2.imshow("Person Detection", frame)

    # 確認用動画は低FPS・低解像度で保存
    if now - last_save_time >= save_interval:
        save_frame = cv2.resize(
            frame,
            (OUTPUT_WIDTH, OUTPUT_HEIGHT),
        )

        writer.write(save_frame)

        last_save_time = now

    key = cv2.waitKey(1)

    if key == 27:
        break


camera.release()
writer.release()
cv2.destroyAllWindows()

print(f"確認用動画を保存しました: {OUTPUT_PATH}")