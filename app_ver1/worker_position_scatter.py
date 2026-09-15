from pathlib import Path
from datetime import datetime


import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from PIL import Image


# ================================================
#   Settings
# ================================================
BASE_DIR = Path(__file__).resolve().parent

IMAGE_DIR = BASE_DIR / "image"
IMAGE_PATH = IMAGE_DIR / "camera_image.png"


POINT_SIZE = 30
POINT_ALPHA = 0.05
IMAGE_ALPHA = 0.4

GRID_COLS = 8
GRID_ROWS = 5

GRID_COLOR = "black"
GRID_LINE_WIDTH = 1

TEXT_COLOR = "black"
TEXT_SIZE = 12


def save_worker_position_scatter(target_date: str) -> Path:
    """Create and save the worker position scatter image."""

    csv_path = (
        BASE_DIR
        / "csv"
        / f"detection_raw_data_{target_date}.csv"
    )

    if not csv_path.exists():
        raise FileNotFoundError(
            f"File is not found: {csv_path}"
        )


    # ================================================
    #   Load data
    # ================================================
    df = pd.read_csv(csv_path)

    camera_image = Image.open(IMAGE_PATH)

    image_width = camera_image.width
    image_height = camera_image.height

    print(f"Data count: {len(df)}")
    print(f"Image size: {image_width} x {image_height}")


    # ================================================
    #   Calculate grid size
    # ================================================
    cell_width = image_width / GRID_COLS
    cell_height = image_height / GRID_ROWS


    # ================================================
    #   Count detections in each grid
    # ================================================
    grid_counts = [
        [0 for _ in range(GRID_COLS)]
        for _ in range(GRID_ROWS)
    ]

    for _, row_data in df.iterrows():
        center_x = row_data["center_x"]
        center_y = row_data["center_y"]

        col = int(center_x / cell_width)
        row = int(center_y / cell_height)

        if col >= GRID_COLS:
            col = GRID_COLS - 1

        if row >= GRID_ROWS:
            row = GRID_ROWS - 1

        grid_counts[row][col] += 1


    # ================================================
    #   Plot
    # ================================================
    plt.figure(figsize=(12, 7))

    plt.imshow(
        camera_image,
        alpha=IMAGE_ALPHA,
    )

    plt.scatter(
        df["center_x"],
        df["center_y"],
        s=POINT_SIZE,
        alpha=POINT_ALPHA,
        color="red",
    )


    # ================================================
    #   Draw grid
    # ================================================
    for col in range(1, GRID_COLS):
        x = cell_width * col

        plt.axvline(
            x=x,
            color=GRID_COLOR,
            linewidth=GRID_LINE_WIDTH,
            linestyle="--",
        )

    for row in range(1, GRID_ROWS):
        y = cell_height * row

        plt.axhline(
            y=y,
            color=GRID_COLOR,
            linewidth=GRID_LINE_WIDTH,
            linestyle="--",
        )


    # ================================================
    #   Draw working time
    # ================================================
    for row in range(GRID_ROWS):
        for col in range(GRID_COLS):
            count = grid_counts[row][col]

            # 1 record = 1 second
            working_time_min = count / 60

            text_x = (
                col * cell_width
                + cell_width / 2
            )

            text_y = (
                row * cell_height
                + cell_height / 2
            )

            plt.text(
                text_x,
                text_y,
                f"{working_time_min:.1f} min",
                ha="center",
                va="center",
                color=TEXT_COLOR,
                fontsize=TEXT_SIZE,
            )

    date_for_display = (
        f"{target_date[:4]}-{target_date[4:6]}-{target_date[6:]}"
    )

    plt.title(f"Worker Position on {date_for_display}")
    plt.xlabel("X [px]")
    plt.ylabel("Y [px]")

    plt.xlim(0, image_width)
    plt.ylim(image_height, 0)

    image_path = IMAGE_DIR / f"worker_position_scatter_{target_date}.png"

    plt.savefig(image_path, dpi=150, bbox_inches="tight")

    plt.close()

    return image_path


# ================================================
#   Test code
# ================================================
if __name__ == "__main__":
    target_date = input('Input target date like "YYYYMMDD" (YYYY optional)')

    if len(target_date) == 4:
        current_year = datetime.now().year
        target_date = f"{current_year}{target_date}"


    # Validate input
    if len(target_date) != 8 or not target_date.isdigit():
        raise ValueError("Date must be YYYYMMDD or MMDD.")

    datetime.strptime(target_date, "%Y%m%d")


    image_path = save_worker_position_scatter(target_date)

    print(f"Image saved: {image_path}")
