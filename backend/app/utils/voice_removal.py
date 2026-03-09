import subprocess
from pathlib import Path
import sys

def separate_audio_demucs(input_audio: str, output_dir: str):
    """
    Separate vocals and background using Demucs
    """


    cmd = [
        sys.executable,
        "-m",
        "demucs",
        "--two-stems=vocals",
        "--name",
        "htdemucs",
        input_audio,
        "-o",
        output_dir,
    ]

    subprocess.run(cmd, check=True)


    background_path = (
    Path(output_dir)
    / "htdemucs"
    / Path(input_audio).stem
    / "no_vocals.wav"
)
    
    if not background_path.exists():
        raise FileNotFoundError(f"Demucs output not found: {background_path}")

    return str(background_path) 