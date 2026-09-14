from pathlib import Path
import re

import cv2


# ================================================
#   Settings
# ================================================
BASE_DIR = Path(__file__).resolve().parent
MOVIE_DIR = BASE_DIR / "movie"

BLACK_SCREEN_SECONDS = 3.0

VIDEO_CODEC = "mp4v"


# ================================================
#   Find video groups
# ================================================
def get_video_groups() -> dict[str, list[Path]]:
    """Find and group hourly MP4 files."""
    pattern = re.compile(
        r"^(\d{8}_\d{4})(?:_(\d+))?\.mp4$"
    )

    groups = {}

    for video_path in MOVIE_DIR.glob("*.mp4"):
        match = pattern.match(video_path.name)

        if match is None:
            continue

        group_name = match.group(1)
        file_number = match.group(2)

        if file_number is None:
            order = 1
        else:
            order = int(file_number)

        if group_name not in groups:
            groups[group_name] = []

        groups[group_name].append(
            (order, video_path)
        )

    result = {}

    for group_name, videos in groups.items():
        videos.sort(key=lambda item: item[0])

        result[group_name] = [
            video_path
            for _, video_path in videos
        ]

    return result


# ================================================
#   Video information
# ================================================
def get_video_info(
    video_path: Path,
) -> tuple[int, int, float] | None:
    """Get width, height, and FPS from a video."""
    capture = cv2.VideoCapture(str(video_path))

    if not capture.isOpened():
        print(f"Failed to open: {video_path.name}")
        return None

    width = int(
        capture.get(cv2.CAP_PROP_FRAME_WIDTH)
    )
    height = int(
        capture.get(cv2.CAP_PROP_FRAME_HEIGHT)
    )
    fps = capture.get(cv2.CAP_PROP_FPS)

    capture.release()

    return width, height, fps


def check_video_compatibility(
    video_paths: list[Path],
) -> tuple[int, int, float] | None:
    """Check whether all videos have the same format."""
    base_info = get_video_info(video_paths[0])

    if base_info is None:
        return None

    base_width, base_height, base_fps = base_info

    for video_path in video_paths[1:]:
        info = get_video_info(video_path)

        if info is None:
            return None

        width, height, fps = info

        same_size = (
            width == base_width
            and height == base_height
        )

        same_fps = abs(fps - base_fps) < 0.01

        if not same_size or not same_fps:
            print()
            print("Video format mismatch:")
            print(f"  File: {video_path.name}")
            print(
                f"  Expected: "
                f"{base_width}x{base_height}, "
                f"{base_fps:.3f} fps"
            )
            print(
                f"  Actual:   "
                f"{width}x{height}, "
                f"{fps:.3f} fps"
            )

            return None

    return base_width, base_height, base_fps


# ================================================
#   Write video
# ================================================
def write_video(
    writer: cv2.VideoWriter,
    video_path: Path,
) -> bool:
    """Write all frames from one video."""
    capture = cv2.VideoCapture(str(video_path))

    if not capture.isOpened():
        print(f"Failed to open: {video_path.name}")
        return False

    print(f"  Adding: {video_path.name}")

    while True:
        success, frame = capture.read()

        if not success:
            break

        writer.write(frame)

    capture.release()

    return True


def write_black_screen(
    writer: cv2.VideoWriter,
    width: int,
    height: int,
    fps: float,
) -> None:
    """Insert a black screen between videos."""
    import numpy as np

    black_frame = np.zeros(
        (height, width, 3),
        dtype=np.uint8,
    )

    frame_count = round(
        fps * BLACK_SCREEN_SECONDS
    )

    for _ in range(frame_count):
        writer.write(black_frame)


# ================================================
#   Merge
# ================================================
def merge_video_group(
    group_name: str,
    video_paths: list[Path],
) -> Path | None:
    """Merge one hourly video group."""
    print()
    print("=" * 60)
    print(f"Group: {group_name}")
    print(f"Files: {len(video_paths)}")
    print("=" * 60)

    video_info = check_video_compatibility(
        video_paths
    )

    if video_info is None:
        print("Merge skipped.")
        return None

    width, height, fps = video_info

    output_path = (
        MOVIE_DIR
        / f"{group_name}_merged.mp4"
    )

    fourcc = cv2.VideoWriter_fourcc(
        *VIDEO_CODEC
    )

    writer = cv2.VideoWriter(
        str(output_path),
        fourcc,
        fps,
        (width, height),
    )

    if not writer.isOpened():
        print(
            f"Failed to create: "
            f"{output_path.name}"
        )
        return None

    success = True

    for index, video_path in enumerate(
        video_paths
    ):
        if index > 0:
            print(
                f"  Adding black screen "
                f"({BLACK_SCREEN_SECONDS:.1f} sec)"
            )

            write_black_screen(
                writer,
                width,
                height,
                fps,
            )

        if not write_video(
            writer,
            video_path,
        ):
            success = False
            break

    writer.release()

    if not success:
        if output_path.exists():
            output_path.unlink()

        print("Merge failed.")
        return None

    print()
    print(
        f"Created: {output_path.name}"
    )

    return output_path


# ================================================
#   Delete original videos
# ================================================
def ask_delete_originals() -> bool:
    """Ask whether original videos should be deleted."""
    while True:
        answer = input(
            "\nDelete the original video files? "
            "(y/n): "
        ).strip().lower()

        if answer == "y":
            return True

        if answer == "n":
            return False

        print("Please enter 'y' or 'n'.")


def delete_original_videos(
    video_paths: list[Path],
) -> None:
    """Delete original MP4 files."""
    for video_path in video_paths:
        try:
            video_path.unlink()
            print(f"Deleted: {video_path.name}")

        except OSError as error:
            print(
                f"Failed to delete "
                f"{video_path.name}: {error}"
            )


# ================================================
#   Main
# ================================================
def main() -> None:
    """Merge hourly video files."""
    if not MOVIE_DIR.exists():
        print(
            f"Movie directory is not found: "
            f"{MOVIE_DIR}"
        )
        return

    groups = get_video_groups()

    merge_targets = {
        group_name: video_paths
        for group_name, video_paths
        in groups.items()
        if len(video_paths) >= 2
    }

    if not merge_targets:
        print("No video files to merge.")
        return

    merged_groups = []

    for group_name in sorted(
        merge_targets
    ):
        video_paths = merge_targets[
            group_name
        ]

        output_path = merge_video_group(
            group_name,
            video_paths,
        )

        if output_path is not None:
            merged_groups.append(
                video_paths
            )

    if not merged_groups:
        print()
        print("No videos were merged.")
        return

    print()
    print("=" * 60)
    print("Merge completed successfully.")
    print("=" * 60)

    if ask_delete_originals():
        print()

        for video_paths in merged_groups:
            delete_original_videos(
                video_paths
            )

        print()
        print("Original video files deleted.")

    else:
        print()
        print("Original video files were kept.")


if __name__ == "__main__":
    main()