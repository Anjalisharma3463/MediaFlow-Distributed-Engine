from pathlib import Path
from app.services.groq_client import client
import json


def transcribe_audio(audio_path: str, output_transcript_path: str = None):
    """
    Transcribe audio using Groq STT API.
    If transcript file already exists, reuse it instead of calling the API again.
    """

    audio_file_path = Path(audio_path)

    # Validate audio file
    if not audio_file_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    allowed_extensions = [".mp3", ".wav", ".m4a", ".ogg"]

    if audio_file_path.suffix.lower() not in allowed_extensions:
        raise ValueError("Unsupported audio format")

    if audio_file_path.stat().st_size == 0:
        raise ValueError("Audio file is empty")

    # If transcript file exists → reuse it
    # Detected language is unknown when reusing cache,
    # so return "auto" — translate_text handles this gracefully
    if output_transcript_path is not None:
        transcript_file = Path(output_transcript_path)

        if transcript_file.exists():
            print(f"Transcript already exists. Reusing: {transcript_file}")

            with open(transcript_file, "r", encoding="utf-8") as f:
                return json.load(f), "auto"

    # Call STT API
    print("Calling Groq STT API...")

    with open(audio_path, "rb") as audio_file:

        transcription = client.audio.transcriptions.create(
            file=audio_file,
            model="whisper-large-v3-turbo",
            timestamp_granularities=["word", "segment"],
            response_format="verbose_json",
        )

    # Extract detected language
    # Whisper returns language code like "hi", "en", "es"
    # We normalize to full name for use in prompts
    detected_language_code = getattr(transcription, "language", "auto")
    detected_language = normalize_language(detected_language_code)

    print(f"Detected language: {detected_language} (raw code: {detected_language_code})")

    # Extract segments
    segments = []

    for segment in transcription.segments:
        segments.append({
            "start": segment["start"],
            "end": segment["end"],
            "text": segment["text"]
        })

    # Save transcript if path provided
    if output_transcript_path is not None:

        transcript_file = Path(output_transcript_path)
        transcript_file.parent.mkdir(parents=True, exist_ok=True)

        with open(transcript_file, "w", encoding="utf-8") as f:
            json.dump(segments, f, ensure_ascii=False, indent=2)

        print(f"Transcript saved: {transcript_file}")

    return segments, detected_language


# LANGUAGE CODE NORMALIZATION
# Whisper returns ISO 639-1 codes ("hi", "en", "ja")
# Our prompts work better with full names ("hindi", "english")

LANGUAGE_CODE_MAP = {
    "hi": "hindi",
    "en": "english",
    "es": "spanish",
    "fr": "french",
    "de": "german",
    "ja": "japanese",
    "pt": "portuguese",
    "ar": "arabic",
    "ko": "korean",
    "ru": "russian",
    "it": "italian",
    "zh": "chinese",
    "tr": "turkish",
    "nl": "dutch",
    "pl": "polish",
    "sv": "swedish",
    "id": "indonesian",
    "vi": "vietnamese",
    "th": "thai",
    "uk": "ukrainian",
    "fa": "persian",
    "ur": "urdu",
    "bn": "bengali",
    "ta": "tamil",
    "te": "telugu",
    "mr": "marathi",
    "gu": "gujarati",
}


def normalize_language(code: str) -> str:
    """
    Convert Whisper language code to full language name.
    Falls back to the raw code if not in map.

    "hi" → "hindi"
    "en" → "english"
    "xyz" → "xyz"  (unknown, passed as-is)
    """
    if not code:
        return "auto"
    return LANGUAGE_CODE_MAP.get(code.lower().strip(), code.lower().strip())