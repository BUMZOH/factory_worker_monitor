import csv
from datetime import datetime, timedelta
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


# ================================================
#   Settings
# ================================================
BASE_DIR = Path(__file__).resolve().parent
CSV_DIR = BASE_DIR / "csv"

CSV_PATH = CSV_DIR / "worker_detection_20260912.csv"
TARGET_DATE = "2026-09-12"


# ================================================
#   Constants
# ================================================
ROI_NAMES = [
    "ROI1",
    "ROI2",
    "ROI3",
    "ROI4",
    "ROI5",
]

ROI_COLUMNS = [
    "roi1_result",
    "roi2_result",
    "roi3_result",
    "roi4_result",
    "roi5_result",
]

ROI_COLORS = [
    "limegreen",
    "blue",
    "orange",
    "purple",
    "deepskyblue",
]

COLOR_MULTIPLE = "red"
COLOR_STOP = "gray"
COLOR_NONE = "black"

TIMELINE_MINUTES = 1440
TIMELINE_START_HOUR = 4

IMAGE_WIDTH = 1600
IMAGE_HEIGHT = 430

BASE_X = 80

TIMELINE_Y1 = 100
TIMELINE_Y2 = 200


# ================================================
#   Functions
# ================================================
def get_font(
    size: int,
) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Return a font usable by Pillow."""
    try:
        return ImageFont.truetype(
            "msgothic.ttc",
            size=size,
        )
    except OSError:
        return ImageFont.load_default()


def get_roi_results(row: dict) -> list[int]:
    """Get all ROI results from one CSV row."""
    roi_results = []

    for column in ROI_COLUMNS:
        result = int(row.get(column, 0))
        roi_results.append(result)

    return roi_results


def get_status_color(
    roi_results: list[int],
) -> str:
    """Convert ROI results to a timeline color."""
    detected_count = sum(roi_results)

    # Two or more ROIs detected at the same time.
    if detected_count >= 2:
        return COLOR_MULTIPLE

    # No ROI detected.
    if detected_count == 0:
        return COLOR_STOP

    # Only one ROI detected.
    for index, result in enumerate(roi_results):
        if result == 1:
            return ROI_COLORS[index]

    return COLOR_STOP


def get_target_period(
    target_date: str,
) -> tuple[datetime, datetime]:
    """Return the target period from 04:00 to next-day 04:00."""
    start_at = datetime.strptime(
        f"{target_date} {TIMELINE_START_HOUR:02d}:00:00",
        "%Y-%m-%d %H:%M:%S",
    )

    end_at = start_at + timedelta(days=1)

    return start_at, end_at


def load_timeline_data(
    csv_path: Path,
    target_date: str,
) -> list[str]:
    """Load 1440 minutes from 04:00 to 03:59 of the next day."""
    start_at, end_at = get_target_period(target_date)

    minute_colors = {}

    with csv_path.open(
        "r",
        newline="",
        encoding="utf-8-sig",
    ) as csv_file:
        reader = csv.DictReader(csv_file)

        for row in reader:
            measured_at = datetime.strptime(
                row["measured_at"],
                "%Y-%m-%d %H:%M:%S",
            )

            # Use only data recorded exactly at second 0.
            if measured_at.second != 0:
                continue

            if not start_at <= measured_at < end_at:
                continue

            roi_results = get_roi_results(row)

            minute_colors[measured_at] = get_status_color(
                roi_results,
            )

    timeline_data = []

    for minute_no in range(TIMELINE_MINUTES):
        minute_at = start_at + timedelta(
            minutes=minute_no,
        )

        color = minute_colors.get(
            minute_at,
            COLOR_NONE,
        )

        timeline_data.append(color)

    return timeline_data


def calculate_working_time(
    csv_path: Path,
    target_date: str,
) -> list[float]:
    """Calculate ROI working times using all records."""
    start_at, end_at = get_target_period(target_date)

    working_counts = [
        0
        for _ in ROI_NAMES
    ]

    with csv_path.open(
        "r",
        newline="",
        encoding="utf-8-sig",
    ) as csv_file:
        reader = csv.DictReader(csv_file)

        for row in reader:
            measured_at = datetime.strptime(
                row["measured_at"],
                "%Y-%m-%d %H:%M:%S",
            )

            if not start_at <= measured_at < end_at:
                continue

            roi_results = get_roi_results(row)

            for index, result in enumerate(roi_results):
                if result == 1:
                    working_counts[index] += 1

    # One CSV record represents approximately one second.
    working_minutes = []

    for count in working_counts:
        minutes = count / 60.0
        working_minutes.append(minutes)

    return working_minutes


def draw_legend(
    draw: ImageDraw.ImageDraw,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
) -> None:
    """Draw the timeline legend."""
    legend_items = []

    for index, roi_name in enumerate(ROI_NAMES):
        legend_items.append(
            (
                ROI_COLORS[index],
                roi_name,
            )
        )

    legend_items.extend(
        [
            (COLOR_MULTIPLE, "Multiple ROIs"),
            (COLOR_STOP, "No detection"),
            (COLOR_NONE, "No data"),
        ]
    )

    items_per_row = 4
    item_width = 350
    row_height = 35

    start_y = 255

    for index, item in enumerate(legend_items):
        color, label = item

        column_no = index % items_per_row
        row_no = index // items_per_row

        x = BASE_X + column_no * item_width
        y = start_y + row_no * row_height

        draw.rectangle(
            [
                (x, y),
                (x + 20, y + 20),
            ],
            fill=color,
            outline="black",
        )

        draw.text(
            (x + 28, y + 1),
            label,
            fill="black",
            font=font,
        )


def draw_working_time(
    draw: ImageDraw.ImageDraw,
    working_minutes: list[float],
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
) -> None:
    """Draw working time for all ROIs."""
    first_line = (
        f"Working time at ROI1 = {working_minutes[0]:.1f} min.    "
        f"ROI2 = {working_minutes[1]:.1f} min.    "
        f"ROI3 = {working_minutes[2]:.1f} min."
    )

    second_line = (
        f"Working time at ROI4 = {working_minutes[3]:.1f} min.    "
        f"ROI5 = {working_minutes[4]:.1f} min."
    )

    draw.text(
        (BASE_X, 340),
        first_line,
        fill="black",
        font=font,
    )

    draw.text(
        (BASE_X, 375),
        second_line,
        fill="black",
        font=font,
    )


def create_timeline_image(
    timeline_data: list[str],
    title: str,
    working_minutes: list[float],
) -> Image.Image:
    """Create a 1440-minute timeline image."""
    if len(timeline_data) != TIMELINE_MINUTES:
        raise ValueError(
            "timeline_data must contain 1440 items."
        )

    font_large = get_font(22)
    font_medium = get_font(16)

    image = Image.new(
        "RGB",
        (
            IMAGE_WIDTH,
            IMAGE_HEIGHT,
        ),
        "white",
    )

    draw = ImageDraw.Draw(image)

    draw.text(
        (BASE_X - 50, 25),
        title,
        fill="black",
        font=font_large,
    )

    # Draw one pixel for each minute.
    for minute_no, color in enumerate(timeline_data):
        x = BASE_X + minute_no

        draw.line(
            [
                (x, TIMELINE_Y1),
                (x, TIMELINE_Y2),
            ],
            fill=color,
            width=1,
        )

    # Draw hourly tick marks from 04:00 to next-day 04:00.
    for hour_no in range(25):
        x = BASE_X + hour_no * 60

        display_hour = (
            TIMELINE_START_HOUR + hour_no
        ) % 24

        draw.line(
            [
                (x, TIMELINE_Y2),
                (x, TIMELINE_Y2 + 5),
            ],
            fill="black",
            width=1,
        )

        draw.text(
            (x - 7, TIMELINE_Y2 + 10),
            str(display_hour),
            fill="black",
            font=font_medium,
        )

    draw.text(
        (
            BASE_X - 50,
            TIMELINE_Y2 + 10,
        ),
        "Time",
        fill="black",
        font=font_medium,
    )

    draw_legend(
        draw,
        font_medium,
    )

    draw_working_time(
        draw,
        working_minutes,
        font_large,
    )

    return image


# ================================================
#   Test code
# ================================================
if __name__ == "__main__":

    target_date = input('Input target date like "YYYY-MM-DD": ')
    if target_date == "":
        target_date = "2026-09-12"

    csv_path = CSV_DIR / (
        f"worker_detection_{target_date.replace("-","")}.csv"
    )

    timeline_data = load_timeline_data(
        csv_path,
        target_date,
    )

    working_minutes = calculate_working_time(
        csv_path,
        target_date,
    )

    title = (
        f"Worker Detection Timeline  {target_date} "
        "04:00 - next day 03:59"
    )

    image = create_timeline_image(
        timeline_data,
        title,
        working_minutes,
    )

    # Display on screen instead of saving an image file.
    image.show()