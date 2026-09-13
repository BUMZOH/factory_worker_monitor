from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PIL import Image
from scipy.ndimage import gaussian_filter


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

BINS_X = 100
BINS_Y = 60

SIGMA = 2.0
ALPHA = 0.6

# Hide areas below this ratio of the maximum density.
DISPLAY_THRESHOLD = 0.05


# ================================================
#   Load data
# ================================================
df = pd.read_csv(CSV_PATH)

camera_image = Image.open(IMAGE_PATH)

image_width = camera_image.width
image_height = camera_image.height

print(f"Data count: {len(df)}")
print(f"Image size: {image_width} x {image_height}")


# ================================================
#   Create 2D histogram
# ================================================
heatmap, x_edges, y_edges = np.histogram2d(
    df["center_x"],
    df["center_y"],
    bins=[
        BINS_X,
        BINS_Y,
    ],
    range=[
        [0, image_width],
        [0, image_height],
    ],
)


# ================================================
#   Smooth heatmap
# ================================================
heatmap = gaussian_filter(
    heatmap,
    sigma=SIGMA,
)


# ================================================
#   Remove low-density areas
# ================================================
threshold = heatmap.max() * DISPLAY_THRESHOLD

heatmap = np.ma.masked_where(
    heatmap < threshold,
    heatmap,
)

print(f"Maximum density: {heatmap.max():.3f}")
print(f"Display threshold: {threshold:.3f}")


# ================================================
#   Plot
# ================================================
plt.figure(figsize=(12, 7))

# Camera image
plt.imshow(camera_image)

# Heatmap
plt.imshow(
    heatmap.T,
    extent=[
        0,
        image_width,
        image_height,
        0,
    ],
    origin="upper",
    cmap="jet",
    alpha=ALPHA,
    interpolation="bilinear",
)

plt.title("Worker Position Heatmap")
plt.xlabel("X [px]")
plt.ylabel("Y [px]")

plt.xlim(0, image_width)
plt.ylim(image_height, 0)

plt.show()