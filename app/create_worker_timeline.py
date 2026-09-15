import csv
import json
from datetime import datetime, timedelta
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


# ================================================
#   Settings
# ================================================
BASE_DIR = Path(__file__).resolve().parent

SETTINGS_PATH = BASE_DIR / "settings.json"

CSV_DIR = BASE_DIR / "csv"
IMAGE_DIR = BASE_DIR / "image"


# ================================================
#   Constants
# ================================================
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
def load_settings() -> dict:
    """Load application settings from JSON file."""
    with SETTINGS_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


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


def get_target_period(
    target_date: str,
) -> tuple[datetime, datetime]:
    """Return the target period from 04:00 to next-day 04:00."""
    start_at = datetime.strptime(
        f"{target_date} "
        f"{TIMELINE_START_HOUR:02d}:00:00",
        "%Y%m%d %H:%M:%S",
    )

    end_at = start_at + timedelta(days=1)

    return start_at, end_at


def get_grid_position(
    center_x: float,
    center_y: float,
    image_width: int,
    image_height: int,
    grid_rows: int,
    grid_cols: int,
) -> tuple[int, int]:
    """Convert center coordinates to a grid position."""
    cell_width = image_width / grid_cols
    cell_height = image_height / grid_rows

    col = int(center_x / cell_width)
    row = int(center_y / cell_height)

    if col >= grid_cols:
        col = grid_cols - 1

    if row >= grid_rows:
        row = grid_rows - 1

    return row, col


def get_roi_names(
    row: int,
    col: int,
    roi_settings: list[dict],
) -> list[str]:
    """Return ROI names assigned to the specified grid cell."""
    roi_names = []

    for roi in roi_settings:
        if not roi["enable"]:
            continue

        if [row, col] in roi["areas"]:
            roi_names.append(roi["name"])

    return roi_names


def get_status_color(
    active_roi_names: set[str],
    roi_settings: list[dict],
) -> str:
    """Convert active ROI names to a timeline color."""
    if len(active_roi_names) >= 2:
        return COLOR_MULTIPLE

    if not active_roi_names:
        return COLOR_STOP

    active_roi_name = next(iter(active_roi_names))

    for index, roi in enumerate(roi_settings):
        if roi["name"] == active_roi_name:
            if index < len(ROI_COLORS):
                return ROI_COLORS[index]

    return COLOR_STOP


def load_raw_data(
    csv_path: Path,
    target_date: str,
    image_width: int,
    image_height: int,
    grid_rows: int,
    grid_cols: int,
    roi_settings: list[dict],
) -> list[dict]:
    """Load raw detection data and add ROI information."""
    start_at, end_at = get_target_period(target_date)

    records = []

    with csv_path.open(
        "r",
        newline="",
        encoding="utf-8-sig",
    ) as csv_file:
        reader = csv.DictReader(csv_file)

        for csv_row in reader:
            measured_at = datetime.strptime(
                csv_row["measured_at"],
                "%Y-%m-%d %H:%M:%S",
            )

            if not start_at <= measured_at < end_at:
                continue

            center_x_text = csv_row["center_x"].strip()
            center_y_text = csv_row["center_y"].strip()

            roi_names = []

            if center_x_text and center_y_text:
                center_x = float(center_x_text)
                center_y = float(center_y_text)

                row, col = get_grid_position(
                    center_x,
                    center_y,
                    image_width,
                    image_height,
                    grid_rows,
                    grid_cols,
                )

                roi_names = get_roi_names(
                    row,
                    col,
                    roi_settings,
                )

            records.append(
                {
                    "measured_at": measured_at,
                    "roi_names": roi_names,
                }
            )

    return records


def create_timeline_data(
    records: list[dict],
    target_date: str,
    roi_settings: list[dict],
) -> list[str]:
    """Create timeline colors using seconds 00 through 09."""
    start_at, _ = get_target_period(target_date)

    timeline_data = []

    for minute_no in range(TIMELINE_MINUTES):
        minute_at = start_at + timedelta(
            minutes=minute_no,
        )

        window_end = minute_at + timedelta(
            seconds=10,
        )

        minute_records = [
            record
            for record in records
            if (
                minute_at
                <= record["measured_at"]
                < window_end
            )
        ]

        # No record means that data itself is unavailable.
        if not minute_records:
            timeline_data.append(COLOR_NONE)
            continue

        active_roi_names = set()

        for record in minute_records:
            active_roi_names.update(
                record["roi_names"]
            )

        color = get_status_color(
            active_roi_names,
            roi_settings,
        )

        timeline_data.append(color)

    return timeline_data


def calculate_working_time(
    records: list[dict],
    roi_settings: list[dict],
) -> dict[str, float]:
    """Calculate ROI working times using all records."""
    active_seconds = {
        roi["name"]: set()
        for roi in roi_settings
        if roi["enable"]
    }

    for record in records:
        measured_at = record["measured_at"]

        for roi_name in record["roi_names"]:
            if roi_name in active_seconds:
                active_seconds[roi_name].add(
                    measured_at
                )

    working_minutes = {}

    for roi_name, seconds in active_seconds.items():
        working_minutes[roi_name] = (
            len(seconds) / 60.0
        )

    return working_minutes


def draw_legend(
    draw: ImageDraw.ImageDraw,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    roi_settings: list[dict],
) -> None:
    """Draw the timeline legend."""
    legend_items = []

    for index, roi in enumerate(roi_settings):
        if not roi["enable"]:
            continue

        if index >= len(ROI_COLORS):
            continue

        legend_items.append(
            (
                ROI_COLORS[index],
                roi["name"],
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
    working_minutes: dict[str, float],
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
) -> None:
    """Draw working time for enabled ROIs."""
    items = []

    for roi_name, minutes in working_minutes.items():
        items.append(
            f"{roi_name} = {minutes:.1f} min."
        )

    first_line = "Working time at "

    if items:
        first_line += "    ".join(items[:3])
    else:
        first_line += "No enabled ROI"

    draw.text(
        (BASE_X, 340),
        first_line,
        fill="black",
        font=font,
    )

    if len(items) > 3:
        second_line = "Working time at "
        second_line += "    ".join(items[3:])

        draw.text(
            (BASE_X, 375),
            second_line,
            fill="black",
            font=font,
        )


def create_timeline_image(
    timeline_data: list[str],
    title: str,
    working_minutes: dict[str, float],
    roi_settings: list[dict],
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
        roi_settings,
    )

    draw_working_time(
        draw,
        working_minutes,
        font_large,
    )

    return image


def save_timeline_image(target_date: str) -> Path:
    """Create and save the timeline image."""
    settings = load_settings()

    grid_settings = settings["grid"]
    grid_rows = grid_settings["rows"]
    grid_cols = grid_settings["cols"]

    roi_settings = settings["roi_settings"]

    csv_path = (
        CSV_DIR
        / f"detection_raw_data_{target_date}.csv"
    )

    if not csv_path.exists():
        raise FileNotFoundError(
            f"File is not found: {csv_path}"
        )

    camera_image_path = (
        IMAGE_DIR
        / "camera_image.png"
    )

    if not camera_image_path.exists():
        raise FileNotFoundError(
            f"File is not found: {camera_image_path}"
        )

    with Image.open(camera_image_path) as camera_image:
        image_width = camera_image.width
        image_height = camera_image.height

    records = load_raw_data(
        csv_path,
        target_date,
        image_width,
        image_height,
        grid_rows,
        grid_cols,
        roi_settings,
    )

    timeline_data = create_timeline_data(
        records,
        target_date,
        roi_settings,
    )

    working_minutes = calculate_working_time(
        records,
        roi_settings,
    )

    date_for_display = (
        f"{target_date[:4]}-"
        f"{target_date[4:6]}-"
        f"{target_date[6:]}"
    )

    title = (
        f"Worker Detection Timeline "
        f"{date_for_display} "
        f"04:00 - next day 03:59"
    )

    image = create_timeline_image(
        timeline_data,
        title,
        working_minutes,
        roi_settings,
    )

    image_path = (
        IMAGE_DIR
        / f"worker_timeline_{target_date}.png"
    )

    image.save(image_path)

    return image_path


# ================================================
#   Test code
# ================================================
if __name__ == "__main__":
    target_date = input(
        'Input target date like "YYYYMMDD" '
        '(YYYY optional): '
    )

    if len(target_date) == 4:
        current_year = datetime.now().year
        target_date = f"{current_year}{target_date}"

    # Validate input
    if len(target_date) != 8 or not target_date.isdigit():
        raise ValueError(
            "Date must be YYYYMMDD or MMDD."
        )

    datetime.strptime(
        target_date,
        "%Y%m%d",
    )

    image_path = save_timeline_image(
        target_date
    )

    print(f"Image saved: {image_path}")