from pathlib import Path

def validate_video_file(video_path: str):
    video = Path(video_path)

    # check if file exists
    if not video.exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")

    # check extension
    allowed_extensions = [".mp4", ".mov", ".mkv", ".avi"]

    if video.suffix.lower() not in allowed_extensions:
        raise ValueError("Unsupported video format")

    # check file size
    if video.stat().st_size == 0:
        raise ValueError("Video file is empty")

    return True