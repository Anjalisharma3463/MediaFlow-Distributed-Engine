from pathlib import Path
from app.services.groq_client import client
import json


def transcribe_audio(audio_path: str, output_transcript_path: str = None):
    """
    Transcribe audio using Groq STT API.
    If transcript file already exists, reuse it instead of calling the API again.
    """

    audio_file_path = Path(audio_path)

    # ------------------------------------------------
    # Validate audio file
    # ------------------------------------------------
    if not audio_file_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    allowed_extensions = [".mp3", ".wav", ".m4a", ".ogg"]

    if audio_file_path.suffix.lower() not in allowed_extensions:
        raise ValueError("Unsupported audio format")

    if audio_file_path.stat().st_size == 0:
        raise ValueError("Audio file is empty")

    # ------------------------------------------------
    # If transcript file exists → reuse it
    # ------------------------------------------------
    if output_transcript_path is not None:
        transcript_file = Path(output_transcript_path)

        if transcript_file.exists():
            print(f"Transcript already exists. Reusing: {transcript_file}")

            with open(transcript_file, "r", encoding="utf-8") as f:
                return json.load(f)

    # ------------------------------------------------
    # Call STT API
    # ------------------------------------------------
    print("Calling Groq STT API...")

    with open(audio_path, "rb") as audio_file:

        transcription = client.audio.transcriptions.create(
            file=audio_file,
            model="whisper-large-v3-turbo",
            timestamp_granularities=["word", "segment"],
            response_format="verbose_json",
        )

    segments = []

    for segment in transcription.segments:
        segments.append({
            "start": segment["start"],
            "end": segment["end"],
            "text": segment["text"]
        })

    # ------------------------------------------------
    # Save transcript if path provided
    # ------------------------------------------------
    if output_transcript_path is not None:

        transcript_file = Path(output_transcript_path)

        # create folder if missing
        transcript_file.parent.mkdir(parents=True, exist_ok=True)

        with open(transcript_file, "w", encoding="utf-8") as f:
            json.dump(segments, f, ensure_ascii=False, indent=2)

        print(f"Transcript saved: {transcript_file}")

    return segments