# def process_pipeline(input_video_path, target_language):

#     # Step 1
#     audio_path = extract_audio(input_video_path)

#     # Step 2
#     transcript = transcribe_audio(audio_path)

#     # Step 3
#     translated_text = translate_text(transcript, target_language)

#     # Step 4
#     generated_audio = generate_tts(translated_text)

#     # Step 5
#     final_video = merge_video(input_video_path, generated_audio)

#     return final_video



import json
import subprocess
from pathlib import Path 
from app.services.groq_client import client
# validate the input video_file

def validate_video_file(video_path: str):
    video = Path(video_path)

    # check if file exists
    if not video.exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")

    # check extension
    allowed_extensions = [".mp4", ".mov", ".mkv", ".avi"]

    if video.suffix.lower() not in allowed_extensions:
        raise ValueError("Unsupported video format")

    # check file size
    if video.stat().st_size == 0:
        raise ValueError("Video file is empty")

    return True


# extract audio form video using ffmpeg

def extract_audio_from_video(video_path: str, output_audio_path: str):
    """
    Extract audio from video using ffmpeg
    """

    command = [
        "ffmpeg",
        "-i", video_path,
        "-ac", "1",
        "-ar", "16000",
        output_audio_path
    ]

    subprocess.run(command, check=True)

    return output_audio_path

# Transcribe audio using Groq STT API

def transcribe_audio(audio_path: str, output_transcript_path: str = None):
    """
    Transcribe audio using Groq STT API
    """
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
 


# main pipeline

def run_pipeline(video_path: str):
    """
    Pipeline controller
    """
    print("Validating input video...")

    validate_video_file(video_path)

    video = Path(video_path)

    audio_output = Path("storage/audio") / f"{video.stem}.wav"
    print(f"Processing video: {video.stem}")
    audio_output.parent.mkdir(parents=True, exist_ok=True)

    print("Extracting audio...")

    audio_path = extract_audio_from_video(str(video), str(audio_output))
    print("Audio extracted at:", audio_path)
    output_transcript_path = Path("storage/transcripts") / f"{video.stem}.json"
    transcribe_audio(audio_path , output_transcript_path)
    print("Transcription completed.")

    return audio_path


if __name__ == "__main__":

    video_file = "storage/input/test-video2.mp4"

    run_pipeline(video_file)