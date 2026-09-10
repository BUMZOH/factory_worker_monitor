import cv2
from ultralytics import YOLO


MODEL_PATH = "yolov8n.pt"
VIDEO_PATH = "movie/movie.webm"

CONFIDENCE = 0.25   # 0.5 -> 0.25 へ変更

# 作業エリア
ROI_X1 = 300
ROI_Y1 = 200
ROI_X2 = 750
ROI_Y2 = 750


model = YOLO(MODEL_PATH)

video = cv2.VideoCapture(VIDEO_PATH)

if not video.isOpened():
    raise RuntimeError(f"動画を開けませんでした: {VIDEO_PATH}")

working = False
work_start_time = None
total_work_time = 0.0


while True:
    success, frame = video.read()

    if not success:
        break

    result = model.predict(
        source=frame,
        classes=[0],
        conf=CONFIDENCE,
        imgsz=1280,     # 追加
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

    # 動画内の現在時刻を秒単位で取得する
    now = video.get(cv2.CAP_PROP_POS_MSEC) / 1000.0

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
        f"Video Time: {now:.1f} sec",
        (20, 80),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (0, 0, 255),
        2,
    )

    cv2.putText(
        frame,
        f"Work Time: {current_work_time:.1f} sec",
        (20, 120),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (0, 0, 255),
        2,
    )

    cv2.imshow("Person Detection", frame)

    key = cv2.waitKey(1)

    if key == 27:
        break


# 動画終了時に作業中なら、最後の区間を累積する
if working:
    total_work_time += now - work_start_time

print(f"Total Work Time: {total_work_time:.1f} sec")

video.release()
cv2.destroyAllWindows()
