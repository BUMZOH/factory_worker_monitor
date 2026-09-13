from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from PIL import Image


# ================================================
#   Settings
# ================================================
BASE_DIR = Path(__file__).resolve().parent

CSV_PATH = (
    BASE_DIR
    / "csv"
    / "detection_raw_data_20260913.csv"
)

IMAGE_PATH = (
    BASE_DIR
    / "image"
    / "camera_image.png"
)

POINT_SIZE = 30
ALPHA = 0.3


# ================================================
#   Load data
# ================================================
df = pd.read_csv(CSV_PATH)

camera_image = Image.open(IMAGE_PATH)

print(f"Data count: {len(df)}")
print(f"Image size: {camera_image.size}")


# ================================================
#   Plot
# ================================================
plt.figure(figsize=(12, 7))

plt.imshow(camera_image)

plt.scatter(
    df["center_x"],
    df["center_y"],
    s=POINT_SIZE,
    alpha=ALPHA,
    color="red",
)

plt.title("Worker Position")
plt.xlabel("X [px]")
plt.ylabel("Y [px]")

plt.xlim(0, camera_image.width)
plt.ylim(camera_image.height, 0)

plt.show()