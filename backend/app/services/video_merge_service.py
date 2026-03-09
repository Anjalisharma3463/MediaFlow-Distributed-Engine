import subprocess
from pathlib import Path


def merge_video_audio(video_path: str, audio_path: str, output_path: str):
    """
    Replace original video audio with new dubbed audio
    """

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "ffmpeg",
        "-y",
        "-i", video_path,
        "-i", audio_path,
        "-c:v", "copy",
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-shortest",
        output_path
    ]

    subprocess.run(cmd, check=True)

    print(" Dubbed video created:", output_path)

    return output_path