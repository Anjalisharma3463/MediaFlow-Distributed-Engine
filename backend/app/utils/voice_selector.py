import json
import random
from pathlib import Path

VOICE_FILE = Path(__file__).parent / "edge_tts_voice_map.json"

with open(VOICE_FILE, "r") as f:
    voice_map = json.load(f)


def select_voice(language: str, gender: str | None = None) -> str:

    language = language.capitalize()

    if language not in voice_map:
        language = "English"

    voices_data = voice_map[language]["voices"]

    # If gender is provided
    if gender and gender in voices_data:
        voices = voices_data[gender]

    else:
        # combine all voices
        voices = []

        voices += voices_data.get("female", [])
        voices += voices_data.get("male", [])
        voices += voices_data.get("multilingual", [])

    return random.choice(voices)