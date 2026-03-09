# 1 read translated transcript
# 2 load generated segment audio files
# try to add background music of that original audio if possible (optional)
# 3 create silent audio track
# 4 place segment audio at correct start time
# 5 export final audio file

# import json
# import subprocess
# from pathlib import Path
# from pydub import AudioSegment
# from app.utils import voice_removal


# def get_audio_duration(audio_file: str) -> int:
#     """
#     Get audio duration in milliseconds using ffprobe
#     """
#     cmd = [
#         "ffprobe",
#         "-v",
#         "error",
#         "-show_entries",
#         "format=duration",
#         "-of",
#         "default=noprint_wrappers=1:nokey=1",
#         audio_file,
#     ]

#     result = subprocess.run(cmd, capture_output=True, text=True)
#     duration_seconds = float(result.stdout.strip())

#     return int(duration_seconds * 1000)


# def build_final_audio(
#     translated_transcript_path: str,
#     segments_folder: str,
#     original_audio_path: str,
#     output_audio_path: str,
#     use_background_music: bool = True
# ):
#     """
#     Build final dubbed audio
#     """

#     # ------------------------------------------------
#     # 1 Load transcript
#     # ------------------------------------------------
#     with open(translated_transcript_path, "r", encoding="utf-8") as f:
#         transcript = json.load(f)

#     # ------------------------------------------------
#     # 2 Remove vocals using Demucs
#     # ------------------------------------------------
#     if use_background_music:

#         background_music_path = voice_removal.separate_audio_demucs(
#             original_audio_path,
#             "storage/temp/demucs_output"
#         )

#         background_music = AudioSegment.from_file(background_music_path) - 26

#     else:
#         background_music = None

#     # ------------------------------------------------
#     # 3 Create silent track (same duration as original)
#     # ------------------------------------------------
#     duration_ms = get_audio_duration(original_audio_path)

#     tts_track = AudioSegment.silent(duration=duration_ms)

#     # Make sure background music length matches
#     if len(background_music) < duration_ms:
#         background_music += AudioSegment.silent(duration_ms - len(background_music))

#     # ------------------------------------------------
#     # 4 Insert TTS segments
#     # ------------------------------------------------
#     segments_folder = Path(segments_folder)

#     for i, segment in enumerate(transcript):

#         start_time = int(segment["start"] * 1000)

#         segment_file = segments_folder / f"segment_{i}.mp3"

#         if not segment_file.exists():
#             print(f"Missing segment: {segment_file}")
#             continue

#         segment_audio = AudioSegment.from_file(segment_file)

#         tts_track = tts_track.overlay(segment_audio, position=start_time)

#     # ------------------------------------------------
#     # 5 Merge background music + TTS
#     # ------------------------------------------------
#         if background_music:
#             final_audio = background_music.overlay(tts_track)
#         else:
#             final_audio = tts_track

#     # ------------------------------------------------
#     # 6 Export final audio
#     # ------------------------------------------------
#     output_path = Path(output_audio_path)
#     output_path.parent.mkdir(parents=True, exist_ok=True)

#     final_audio.export(output_path, format="mp3")

#     print("Final dubbed audio saved:", output_path)

#     return str(output_path)








import json
import subprocess
from pathlib import Path
from pydub import AudioSegment
from app.utils import voice_removal


def get_audio_duration(audio_file: str) -> int:
    """
    Get audio duration in milliseconds using ffprobe
    """
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        audio_file,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    duration_seconds = float(result.stdout.strip())

    return int(duration_seconds * 1000)


def build_final_audio(
    translated_transcript_path: str,
    segments_folder: str,
    original_audio_path: str,
    output_audio_path: str,
    use_background_music: bool = True
):
    """
    Build final dubbed audio
    """

    # ------------------------------------------------
    # 1 Load transcript
    # ------------------------------------------------
    with open(translated_transcript_path, "r", encoding="utf-8") as f:
        transcript = json.load(f)

    # ------------------------------------------------
    # 2 Optional: Remove vocals using Demucs
    # ------------------------------------------------
    background_music = None

    if use_background_music:

        background_music_path = voice_removal.separate_audio_demucs(
            original_audio_path,
            "storage/temp/demucs_output"
        )

        background_music = AudioSegment.from_file(background_music_path) - 26

    # ------------------------------------------------
    # 3 Create silent track
    # ------------------------------------------------
    duration_ms = get_audio_duration(original_audio_path)

    tts_track = AudioSegment.silent(duration=duration_ms)

    # Ensure background length matches
    if background_music and len(background_music) < duration_ms:
        background_music += AudioSegment.silent(duration_ms - len(background_music))

    # ------------------------------------------------
    # 4 Insert TTS segments
    # ------------------------------------------------
    segments_folder = Path(segments_folder)

    for i, segment in enumerate(transcript):

        start_time = int(segment["start"] * 1000)

        segment_file = segments_folder / f"segment_{i}.mp3"

        if not segment_file.exists():
            print(f"Missing segment: {segment_file}")
            continue

        segment_audio = AudioSegment.from_file(segment_file)

        tts_track = tts_track.overlay(segment_audio, position=start_time)

    # ------------------------------------------------
    # 5 Merge background + TTS
    # ------------------------------------------------
    if background_music:
        final_audio = background_music.overlay(tts_track)
    else:
        final_audio = tts_track

    # ------------------------------------------------
    # 6 Export final audio
    # ------------------------------------------------
    output_path = Path(output_audio_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    final_audio.export(output_path, format="mp3")

    print("Final dubbed audio saved:", output_path)

    return str(output_path)