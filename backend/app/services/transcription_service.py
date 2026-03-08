from pathlib import Path
from app.services.groq_client import client
import json
# Transcribe audio using Groq STT API

def transcribe_audio(audio_path: str, output_transcript_path: str = None):
    """
    Transcribe audio using Groq STT API
    """
        # check if file exists
    if not Path(audio_path).exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")
    
    # check extension
    allowed_extensions = [".mp3", ".wav", ".m4a", ".ogg"]

    if Path(audio_path).suffix.lower() not in allowed_extensions:
        raise ValueError("Unsupported audio format")
    
    if Path(audio_path).stat().st_size == 0:
        raise ValueError("Audio file is empty")

    with open(audio_path , "rb") as audio_file:
        transcription = client.audio.transcriptions.create(
            file=audio_file,
            model="whisper-large-v3-turbo",
            timestamp_granularities = ["word", "segment"],
            response_format="verbose_json",
        )
        segments = []

        for segment in transcription.segments:
            segments.append({
                "start": segment["start"],
                "end": segment["end"],
                "text": segment["text"]
            })
        if output_transcript_path:
            with open(output_transcript_path, "w", encoding="utf-8") as f:
                json.dump(segments, f, indent=4, ensure_ascii=False)
        return segments