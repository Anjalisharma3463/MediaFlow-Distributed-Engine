from pathlib import Path
import asyncio
from app.utils.validate import validate_video_file
from app.services.audio_service import extract_audio_from_video
from app.services.transcription_service import transcribe_audio
from app.services.translation_service import translate_text
from app.services.tts_service import text_to_speech_tts
from app.services.audio_combiner_service import build_final_audio

def run_pipeline(video_path: str, translated_language: str):
    # user will give translated language as input in which user wants this video translate to..

    validate_video_file(video_path)

    video = Path(video_path)

    audio_path = f"storage/audio/extracted/{video.stem}.wav"
    transcript_path = f"storage/transcripts/{video.stem}.json"
    translated_path = f"storage/translated_transcripts/{video.stem}_translated.json"
   
    print("Extracting audio...")
    extract_audio_from_video(video_path, audio_path)

    print("Transcribing audio...")
    transcribe_audio(audio_path, transcript_path)

    print("Translating transcript...")
    translate_text(transcript_path, translated_language, translated_path)

    print("Generating TTS audio segments...")
    output_audio_folder = f"storage/temp/tts_segments/{video.stem}"
    asyncio.run(text_to_speech_tts(translated_path, translated_language, output_audio_folder))

    print("Combining audio segments...")
    build_final_audio(translated_path, output_audio_folder, audio_path, f"storage/final/{video.stem}_final.mp3")
    print("Pipeline completed")

    return translated_path

