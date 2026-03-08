import subprocess
# extract audio form video using ffmpeg

def extract_audio_from_video(video_path: str, output_audio_path: str):
    """
    Extract audio from video using ffmpeg
    """

    command = [
        "ffmpeg",
        "-i", video_path,
        "-ac", "1",
        "-ar", "16000",
        output_audio_path
    ]

    subprocess.run(command, check=True)

    return output_audio_path