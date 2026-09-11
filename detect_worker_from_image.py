from pathlib import Path
import tkinter as tk
from tkinter import filedialog

import cv2
from ultralytics import YOLO

#================================================
#   設定
#================================================
MODEL_PATH = "yolov8n.pt"
CONFIDENCE = 0.25           # default は 0.25
IMGSZ = 1280                # default は 640

BASE_DIRECTORY = Path(__file__).resolve().parent
IMAGE_DIRECTORY = BASE_DIRECTORY / "image"

# 作業エリア
ROI_X1 = 150
ROI_Y1 = 150
ROI_X2 = 550
ROI_Y2 = 450


# --- 対象画像ファイル選択 ---
root = tk.Tk(); root.withdraw()
image_path = filedialog.askopenfilename(
    title="画像ファイルを選択してください",
    initialdir=IMAGE_DIRECTORY,
    filetypes=[
        ("Image files", "*.jpg *.jpeg *.png *.bmp"),
        ("All files", "*.*"),
    ],
)
root.destroy()

if not image_path:
    raise SystemExit

frame = cv2.imread(image_path)

if frame is None:
    raise ValueError(f"画像を読み込めませんでした: {image_path}")


# --- YOLO モデル格納 & 推論実行 ---
model = YOLO(MODEL_PATH)

result = model.predict(
    source=frame,
    classes=[0],
    conf=CONFIDENCE,
    imgsz=IMGSZ,
    verbose=True,
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

cv2.imshow("Person Detection", frame)
cv2.waitKey(0)
cv2.destroyAllWindows()




















