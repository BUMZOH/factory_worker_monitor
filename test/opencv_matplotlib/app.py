from pathlib import Path

import cv2
import matplotlib.pyplot as plt
import numpy as np


# ================================================
#   Settings
# ================================================
BASE_DIR = Path(__file__).resolve().parent

IMAGE_PATH = BASE_DIR / "sample.png"


# ================================================
#   Load image
# ================================================
image_data = np.fromfile(
    IMAGE_PATH,
    dtype=np.uint8,
)

image = cv2.imdecode(
    image_data,
    cv2.IMREAD_COLOR,
)

if image is None:
    raise ValueError(
        f"Image could not be loaded: {IMAGE_PATH}"
    )


# ================================================
#   OpenCV processing
# ================================================

# Rectangle
cv2.rectangle(
    image,
    (100, 100),
    (500, 400),
    (0, 0, 255),
    3,
)

# Circle
cv2.circle(
    image,
    (300, 250),
    30,
    (0, 255, 0),
    -1,
)

# Text
cv2.putText(
    image,
    "OpenCV Result",
    (100, 80),
    cv2.FONT_HERSHEY_SIMPLEX,
    1.0,
    (255, 0, 0),
    2,
)


# ================================================
#   BGR -> RGB
# ================================================
image_rgb = cv2.cvtColor(
    image,
    cv2.COLOR_BGR2RGB,
)


# ================================================
#   Show with Matplotlib
# ================================================
plt.figure(
    figsize=(10, 6)
)

plt.imshow(image_rgb)

plt.title("OpenCV Processing Result")
plt.xlabel("X [px]")
plt.ylabel("Y [px]")

plt.show()