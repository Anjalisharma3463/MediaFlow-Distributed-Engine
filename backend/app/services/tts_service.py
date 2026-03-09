# tts_service.py
# text-to-speech service using Edge TTS

import json
import asyncio
from pathlib import Path
import edge_tts
from app.utils.voice_selector import select_voice

async def generate_segment(text: str ,VOICE: str, output_file: str):
    """
    Generate TTS for a single segment
    """

    # this VOICE is will be made of voice that is as input in generate segment and translated_language from the list that are given in edge tts
    communicate = edge_tts.Communicate(text, VOICE)
    await communicate.save(output_file)


async def text_to_speech_tts(translated_path: str, translated_language: str, output_path_folder: str):
    """
    Convert translated transcript segments to audio files
    """

    # Load transcript
    with open(translated_path, "r", encoding="utf-8") as f:
        transcript = json.load(f)

    # Create output folder
    # if output_path_folder does not exist, create it
    if not Path(output_path_folder).exists(): 
        output_folder = Path(output_path_folder)
        output_folder.mkdir(parents=True, exist_ok=True)
        output_path_folder = str(output_folder)
    else:
        output_folder = Path(output_path_folder)

    tasks = []
    gender = "male"
    VOICE = select_voice(translated_language, gender)  # Select voice based on translated language
    # Generate audio for each segment
    for i, segment in enumerate(transcript):
        text = segment["translated"]
        # voice = segment["gender"]  #male or female voice based on
        output_file = output_folder / f"segment_{i}.mp3"

        tasks.append(generate_segment(text, VOICE, str(output_file)))

    # Run all tasks
    await asyncio.gather(*tasks)

    return str(output_folder)