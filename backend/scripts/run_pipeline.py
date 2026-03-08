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
from urllib import response 
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
 
 

# def clean_transcript(input_transcript_path: str):
#     """
#     Clean transcript segments while preserving timestamps.
#     Fix phonetic English technical terms and remove noise.
#     """
#     BATCH_SIZE = 15

#     with open(input_transcript_path, "r", encoding="utf-8") as f:
#         segments = json.load(f)

#         clean_segments  = []

#     for i in range(0, len(segments), BATCH_SIZE):

#         batch = segments[i:i+BATCH_SIZE]

#         payload = []

#         for idx, seg in enumerate(batch):
#             payload.append({
#                 "id": idx,
#                 "text": seg["text"]
#             })

#         payload_json = json.dumps(payload, ensure_ascii=False, indent=2)

        # prompt = f"""
        # You are cleaning speech-to-text transcripts.

        # Fix spelling errors and phonetic English words written in Hindi or other scripts.

        # Rules:
        # - Do NOT translate
        # - Do NOT explain
        # - Do NOT write code
        # - Return ONLY valid JSON

        # Input:
        # {payload_json}

        # Output JSON format:
        # [
        # {{"id": 0, "cleaned": "..."}}
        # ]
        # """

#         response = client.chat.completions.create(
#             model="llama-3.1-8b-instant",
#             messages=[
#                 {"role": "user", "content": prompt}
#             ],
#             temperature=0
#         )

#         result_text = response.choices[0].message.content.strip()

#         try:
#             cleaned_batch = json.loads(result_text)
#         except:
#             print("⚠️ Invalid JSON from model")
#             print(result_text)
#             continue

#         for item in cleaned_batch:

#             seg = batch[item["id"]]

#             clean_segments .append({
#                 "start": seg["start"],
#                 "end": seg["end"],
#                 "text": item["cleaned"]
#             })

#     return clean_segments 



#  translation service using Groq Translation API

def translate_text(input_transcript_path: str, target_language: str, output_transcript_path: str):
    """
    Translate transcript segments into target language.
    """
    # get the clean transcript
    # clean_segments  = clean_transcript(input_transcript_path)
    # load transcript file directly (since cleaning is disabled for now)
    with open(input_transcript_path, "r", encoding="utf-8") as f:
        clean_segments = json.load(f)
    # send this text and duration to model to get the translation in batch size for each call to model
    BATCH_SIZE = 10
    # this translated_segments will hold the final output of translated segments with start, end, original text and translated text
    translated_segments = []

    # process the transcript in batches and make one batch_payload of segments with duration
    for i in range(0, len(clean_segments), BATCH_SIZE):
        batch = clean_segments[i:i+BATCH_SIZE]    

        batch_payload = []
        for idx, segment in enumerate(batch):
            duration = segment["end"] - segment["start"]
            
            batch_payload.append({
                "id": idx,
                "text": segment["text"],
                "duration": duration
            })

        payload_json = json.dumps(batch_payload, ensure_ascii=False, indent=2)

        prompt = f"""
        You are a translation engine.

        Translate each sentence into {target_language}.

        Rules:
        - Keep meaning accurate
        - Keep translations concise to fit the duration
        - Do NOT explain anything
        - Do NOT write code
        - Do NOT include markdown
        - Return ONLY valid JSON

        Input:
        {payload_json}

        Output format (JSON only):
        [
        {{"id": 0, "translated": "..."}}
        ]
        """
        # send this batch_payload to model to get the translation
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0

        ) 
         
        result_text = response.choices[0].message.content.strip()

        # remove markdown if present
        result_text = result_text.replace("```json", "").replace("```", "").strip()
        print("\nMODEL RESPONSE:")
        print(result_text)
        try:
            batch_translations = json.loads(result_text)
        except json.JSONDecodeError:
            print("⚠️ JSON parsing failed")
            print(result_text)
            continue

        for item in batch_translations:

            seg = batch[item["id"]]

            translated_segments.append({
                "start": seg["start"],
                "end": seg["end"],
                "original": seg["text"],
                "translated": item["translated"]
            })
    # save the output in output format 
    with open(output_transcript_path, "w", encoding="utf-8") as f:
        json.dump(translated_segments, f, indent=4, ensure_ascii=False)

    print(f"✅ Translation saved to {output_transcript_path}")




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
    
    translate_text(output_transcript_path, "Hindi", str(Path("storage/translated_transcripts") / f"{video.stem}_translated.json"))
    print("Translation completed.")
    return audio_path


if __name__ == "__main__":

    video_file = "storage/input/test-video2.mp4"

    run_pipeline(video_file)