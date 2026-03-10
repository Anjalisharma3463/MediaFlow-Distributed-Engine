from pathlib import Path
import asyncio
from app.utils.validate import validate_video_file
from app.services.audio_service import extract_audio_from_video
from app.services.transcription_service import transcribe_audio
from app.services.translation_service import translate_text
from app.services.tts_service import text_to_speech_tts
from app.services.audio_combiner_service import build_final_audio
from app.services.video_merge_service import merge_video_audio

def run_pipeline(video_path: str, translated_language: str,use_background_music: bool = True):
    # user will give translated language as input in which user wants this video translate to..

    validate_video_file(video_path)

    video = Path(video_path)

    audio_path = f"storage/audio/extracted/{video.stem}.wav" 
    transcripts_folder = f"storage/transcripts/{video.stem}"
    if not Path(transcripts_folder).exists():
        Path(transcripts_folder).mkdir(parents=True, exist_ok=True)
    else:
        print(f"Warning: Transcripts folder {transcripts_folder} already exists. It will be overwritten.")
    original_transcript_path = f"{transcripts_folder}/original_transcript.json"
    translated_path = f"{transcripts_folder}/translated_transcript.json"
    timing_metrics_path = f"{transcripts_folder}/timing_metrics.json"
    new_audio_path = f"storage/final/{video.stem}_final.mp3"
    merged_video_path = f"storage/output/{video.stem}_final.mp4"
    
    print("Extracting audio...")
    extract_audio_from_video(video_path, audio_path)

    print("Transcribing audio...")
    transcribe_audio(audio_path, original_transcript_path)

    print("Translating transcript...")
    translate_text(original_transcript_path, translated_language, translated_path)

    print("Generating TTS audio segments...")
    output_audio_folder = f"storage/temp/tts_segments/{video.stem}"
    asyncio.run(text_to_speech_tts(translated_path, translated_language, output_audio_folder,timing_metrics_path))

    print("Combining audio segments...")
    build_final_audio(translated_path, output_audio_folder, audio_path, new_audio_path, use_background_music=use_background_music)

    print("merging video with new audio...")
    merge_video_audio(video_path, new_audio_path, merged_video_path)

    print("Pipeline completed")

    return translated_path

