# tts_service.py
# text-to-speech service using Edge TTS

import json
import asyncio
from pathlib import Path
import edge_tts
from app.utils.voice_selector import select_voice
from pydub import AudioSegment


def measure_segment(
    segment_index,
    original_text,
    translated_text,
    source_start,
    source_end,
    tts_audio_path,
):
    source_duration = source_end - source_start
    
    tts_audio = AudioSegment.from_file(tts_audio_path)
    tts_duration = len(tts_audio) / 1000.0
    
    expansion_ratio = tts_duration / source_duration if source_duration > 0 else 0
    
    return {
        "segment_index": segment_index,
        "original_text": original_text,
        "translated_text": translated_text,
        "source_duration": round(source_duration, 3),
        "tts_duration": round(tts_duration, 3),
        "expansion_ratio": round(expansion_ratio, 3)
    }


def save_timing_metrics(metrics_list, output_path):
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(metrics_list, f, ensure_ascii=False, indent=2)
    print(f"Timing metrics saved to {output_path}")


async def generate_segment(text: str, VOICE: str, output_file: str):
    communicate = edge_tts.Communicate(text, VOICE)
    await communicate.save(output_file)


async def text_to_speech_tts(translated_path: str, translated_language: str, output_path_folder: str):
    # Load transcript
    with open(translated_path, "r", encoding="utf-8") as f:
        transcript = json.load(f)

    # Create output folder
    if not Path(output_path_folder).exists():
        output_folder = Path(output_path_folder)
        output_folder.mkdir(parents=True, exist_ok=True)
    else:
        output_folder = Path(output_path_folder)

    gender = "male"
    VOICE = select_voice(translated_language, gender)

    # Build tasks with their output paths
    tasks = []
    segment_output_files = []

    for i, segment in enumerate(transcript):
        text = segment["translated"]
        output_file = output_folder / f"segment_{i}.mp3"
        segment_output_files.append(output_file)
        tasks.append(generate_segment(text, VOICE, str(output_file)))

    # Generate ALL audio files first
    await asyncio.gather(*tasks)

    # NOW measure — audio files exist on disk at this point
    timing_metrics = []

    for i, segment in enumerate(transcript):
        tts_audio_path = segment_output_files[i]

        metric = measure_segment(
            segment_index=i,
            original_text=segment["original"],
            translated_text=segment["translated"],
            source_start=segment["start"],
            source_end=segment["end"],
            tts_audio_path=str(tts_audio_path)
        )

        timing_metrics.append(metric)

        print(f"Segment {i}: source={metric['source_duration']}s | "
              f"tts={metric['tts_duration']}s | "
              f"ratio={metric['expansion_ratio']}")

    # Save once after all segments measured
    save_timing_metrics(
        timing_metrics,
        "storage/transcripts/timing_metrics.json"
    )

    return str(output_folder)