from pathlib import Path
import asyncio
from app.utils.validate import validate_video_file
from app.services.audio_service import extract_audio_from_video
from app.services.transcription_service import transcribe_audio
from app.services.translation_service import translate_text
from app.services.tts_service import text_to_speech_tts
from app.services.audio_reconstruction import build_final_audio
from app.services.video_merge_service import merge_video_audio


def run_pipeline(video_path: str, translated_language: str, use_background_music: bool = True):
    """
    Full dubbing pipeline.

    Flow:
        validate → extract audio → transcribe → translate → TTS → reconstruct audio → merge video 
    """

    validate_video_file(video_path)

    video = Path(video_path)

    # ── Path definitions 
    audio_path              = f"storage/audio/extracted/{video.stem}.wav"
    transcripts_folder      = f"storage/transcripts/{video.stem}"
    original_transcript_path= f"{transcripts_folder}/original_transcript.json"
    translated_path         = f"{transcripts_folder}/translated_transcript.json"
    timing_metrics_path     = f"{transcripts_folder}/timing_metrics.json"  # ← connects TTS → reconstruction
    tts_segments_folder     = f"storage/temp/tts_segments/{video.stem}"
    new_audio_path          = f"storage/final/{video.stem}_final.mp3"
    merged_video_path       = f"storage/output/{video.stem}_final.mp4"

    # create transcripts folder
    transcripts_folder_path = Path(transcripts_folder)
    if not transcripts_folder_path.exists():
        transcripts_folder_path.mkdir(parents=True, exist_ok=True)
    else:
        print(f"Warning: Transcripts folder already exists — will overwrite outputs")

    #   STEP 1: Extract audio 
    print("\n[1/6] Extracting audio...")
    extract_audio_from_video(video_path, audio_path)

    # STEP 2: Transcribe 
    # Returns (segments, detected_language)
    # detected_language is what Whisper identified — passed to translate_text
    # so cleaning and term detection prompts know what language they're working with
    print("\n[2/6] Transcribing audio...")
    _, detected_language = transcribe_audio(audio_path, original_transcript_path)
    print(f"      Detected source language: {detected_language}")

    # STEP 3: Translate 
    # source_language now flows in — fixes term detection and cleaning quality
    print("\n[3/6] Translating transcript...")
    translate_text(
        input_transcript_path=original_transcript_path,
        target_language=translated_language,
        output_transcript_path=translated_path,
        source_language=detected_language      
    )

    #  STEP 4: Generate TTS  
    # Saves timing_metrics.json at timing_metrics_path
    # Each segment tagged with strategy: "none" | "mild" | "capped"
    print("\n[4/6] Generating TTS audio segments...")
    asyncio.run(text_to_speech_tts(
        translated_path=translated_path,
        translated_language=translated_language,
        output_path_folder=tts_segments_folder,
        timing_metrics_output_path=timing_metrics_path  # ← saves metrics here
    ))

    # STEP 5: Reconstruct audio  
    # timing_metrics_path now passed in — reconstruction reads it
    # to know which segments were capped and need adaptive placement
    print("\n[5/6] Reconstructing audio...")
    build_final_audio(
        translated_transcript_path=translated_path,
        segments_folder=tts_segments_folder,
        original_audio_path=audio_path,
        output_audio_path=new_audio_path,
        timing_metrics_path=timing_metrics_path,         
        use_background_music=use_background_music
    )

    #  STEP 6: Merge video 
    print("\n[6/6] Merging video with new audio...")
    merge_video_audio(video_path, new_audio_path, merged_video_path)

    print(f"\n✅ Pipeline complete → {merged_video_path}")
    return merged_video_path