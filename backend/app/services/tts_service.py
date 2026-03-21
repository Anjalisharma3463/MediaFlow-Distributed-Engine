# tts_service.py
# Text-to-speech service using Edge TTS
#
# PROBLEM: TTS audio is often longer than the original speech slot.
# Hindi "वाइब कोडिंग" (0.8s) translates to "vibe coding is" (2.7s TTS).
# Placing that 2.7s audio at the original 0.8s timestamp causes overlap
# with the next segment, making the final audio sound chaotic.
#
# SOLUTION: Mild speed adjustment at TTS generation time.
# Strategy:
#   ratio <= 1.3  → no adjustment, audio is fine as-is
#   ratio 1.3–2.0 → speed up slightly using ffmpeg atempo (sounds natural)
#   ratio > 2.0   → speed up to 1.8x max + flag for audio_reconstruction
#                   to use adaptive placement (let it spill into silence gap)
#
# Why ffmpeg atempo and not PyDub speedup:
#   PyDub speedup changes pitch (sounds chipmunk/robotic).
#   ffmpeg atempo is a time-stretch filter — changes speed without pitch change.
#   This is what professional dubbing tools use.
#
# atempo range: 0.5 to 2.0
# For ratios > 2.0, chain two atempo filters: atempo=2.0,atempo=X

import json
import asyncio
import subprocess
from pathlib import Path
import edge_tts
from app.utils.voice_selector import select_voice
from pydub import AudioSegment

 
# SPEED ADJUSTMENT THRESHOLDS
# Tuned for natural sound quality 

RATIO_NO_ADJUST   = 1.3   # under this → leave audio alone
RATIO_MAX_STRETCH = 1.4  # professional standard


 
# FFMPEG TIME-STRETCH
# Uses atempo filter — changes speed without changing pitch
# This is the key difference from PyDub which sounds robotic 

def speed_adjust_audio(input_path: str, output_path: str, speed_factor: float) -> bool:
    """
    Speed-adjust audio using ffmpeg atempo filter.
    Preserves pitch — does NOT sound robotic.

    atempo accepts values 0.5 to 2.0 only.
    For speed > 2.0, chain two filters: atempo=2.0,atempo=remainder

    Returns True if successful, False if ffmpeg failed.
    """

    if speed_factor <= 1.0:
        # no adjustment needed, just copy
        import shutil
        shutil.copy(input_path, output_path)
        return True

    # clamp to safe maximum
    speed_factor = min(speed_factor, RATIO_MAX_STRETCH)

    # build atempo filter chain
    # atempo max is 2.0, so for anything above we chain filters
    if speed_factor <= 2.0:
        atempo_filter = f"atempo={speed_factor:.4f}"
    else:
        # should not reach here after clamping, but safety net
        atempo_filter = f"atempo=2.0,atempo={speed_factor / 2.0:.4f}"

    cmd = [
        "ffmpeg",
        "-y",                        # overwrite without asking
        "-i", input_path,
        "-filter:a", atempo_filter,
        "-vn",                       # no video
        output_path
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"ffmpeg atempo failed for {input_path}: {result.stderr[:200]}")
        return False

    return True


# def compute_target_speed(source_duration: float, tts_duration: float) -> tuple[float, str]:
#     """
#     Decide how much to speed up TTS audio.

#     Returns:
#         (speed_factor, strategy)

#     Strategies:
#         "none"     → audio fits, no adjustment
#         "mild"     → slight speedup, will sound natural
#         "capped"   → over 2.0x, cap at 1.8x, audio_reconstruction handles the rest
#     """

#     if source_duration <= 0:
#         return 1.0, "none"

#     ratio = tts_duration / source_duration

#     if ratio <= RATIO_NO_ADJUST:
#         return 1.0, "none"

#     elif ratio <= RATIO_MAX_STRETCH:
#         # speed up to fit exactly — sounds natural under 2.0x
#         speed_factor = ratio
#         return speed_factor, "mild"

#     else:
#         # over 2.0x would sound unnatural
#         # cap at 1.8x (slightly under max for quality headroom)
#         # audio_reconstruction will use adaptive placement for the remainder
#         return 1.8, "capped"


def compute_target_speed(
    source_duration: float,
    tts_duration: float,
    available_window: float  # ← new parameter: time to next segment start
) -> tuple[float, str]:
    """
    Decide speed using available_window (gap to next segment),
    not just source_duration.
    
    available_window = next_segment_start - this_segment_start
    This includes the silence gap — extra room to speak naturally.
    """

    if source_duration <= 0:
        return 1.0, "none"

    # use available window — not just source slot
    # this is the key difference from naive approach
    fit_duration = max(available_window, source_duration)
    ratio = tts_duration / fit_duration

    if ratio <= 1.1:
        return 1.0, "none"          # fits perfectly — no touch

    elif ratio <= 1.4:
        return ratio, "mild"         # slight speedup, sounds natural

    elif ratio <= 2.0:
        return 1.4, "mild"           # cap at 1.4x — sounds ok
                                     # (you had 1.8x — too aggressive)
    else:
       return 1.4, "capped"   # still cap at 1.4x, flag adaptive
 
# CORE TTS GENERATION 

async def generate_segment_raw(text: str, voice: str, output_file: str):
    """Generate raw TTS audio. No speed adjustment here — done in post."""
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_file)


def get_audio_duration_ms(audio_path: str) -> float:
    """Get audio duration in seconds using ffprobe."""
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        audio_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        # fallback to pydub
        audio = AudioSegment.from_file(audio_path)
        return len(audio) / 1000.0
    return float(result.stdout.strip())

 
# TIMING METRICS 

def build_timing_metric(
    segment_index: int,
    original_text: str,
    translated_text: str,
    source_start: float,
    source_end: float,
    raw_tts_duration: float,
    final_tts_duration: float,
    speed_factor: float,
    strategy: str
) -> dict:
    """
    Build a timing metric entry for one segment.
    Tracks both raw TTS duration and final adjusted duration.
    Used to understand where sync breaks down.
    """
    source_duration = source_end - source_start

    return {
        "segment_index":      segment_index,
        "original_text":      original_text,
        "translated_text":    translated_text,
        "source_duration":    round(source_duration, 3),
        "raw_tts_duration":   round(raw_tts_duration, 3),
        "final_tts_duration": round(final_tts_duration, 3),
        "raw_expansion_ratio":round(raw_tts_duration / source_duration, 3) if source_duration > 0 else 0,
        "speed_factor":       round(speed_factor, 3),
        "strategy":           strategy,   # "none" | "mild" | "capped"
        "needs_adaptive":     strategy == "capped"  # flag for audio_reconstruction
    }


def save_timing_metrics(metrics_list: list, output_path: str):
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(metrics_list, f, ensure_ascii=False, indent=2)
    print(f"  Timing metrics saved: {output_file}")

 
# MAIN ENTRY POINT 

async def text_to_speech_tts(
    translated_path: str,
    translated_language: str,
    output_path_folder: str,
    timing_metrics_output_path: str
) -> str:
    """
    Generate TTS audio for all translated segments.

    Process per segment:
    1. Generate raw TTS audio (Edge TTS)
    2. Measure raw duration vs source duration
    3. If expansion ratio > 1.3, apply ffmpeg atempo speed adjustment
    4. Save final adjusted audio as segment_{i}.mp3
    5. Record timing metrics with strategy used

    Returns path to folder containing all segment files.
    """

    translated_file = Path(translated_path)

    if not translated_file.exists():
        raise FileNotFoundError(f"Translated transcript not found: {translated_path}")
    if translated_file.stat().st_size == 0:
        raise ValueError("Translated transcript file is empty")

    with open(translated_file, "r", encoding="utf-8") as f:
        transcript = json.load(f)

    output_folder = Path(output_path_folder)
    output_folder.mkdir(parents=True, exist_ok=True)

    # temp folder for raw (unadjusted) TTS files
    raw_folder = output_folder / "raw"
    raw_folder.mkdir(parents=True, exist_ok=True)

    # select one voice for the entire video
    # voice selected once outside the loop — consistency across all segments
    gender = "male"
    voice = select_voice(translated_language, gender)
    print(f"\n{'='*60}")
    print(f"TTS GENERATION")
    print(f"{'='*60}")
    print(f"   Segments : {len(transcript)}")
    print(f"   Language : {translated_language}")
    print(f"   Voice    : {voice}")

    # ── STEP 1: Generate all raw TTS in parallel  
    print(f"\n   Generating raw TTS for {len(transcript)} segments...")

    raw_tasks = []
    raw_files = []

    for i, segment in enumerate(transcript):
        raw_file = raw_folder / f"segment_{i}_raw.mp3"
        raw_files.append(raw_file)
        raw_tasks.append(generate_segment_raw(segment["translated"], voice, str(raw_file)))

    await asyncio.gather(*raw_tasks)
    print(f"Raw TTS generated")

    # ── STEP 2: Measure durations + apply speed adjustment  
    print(f"\n   Adjusting timing...")

    timing_metrics = []
    none_count  = 0
    mild_count  = 0 
    capped_count = 0

    for i, segment in enumerate(transcript):

        source_start    = segment["start"]
        source_end      = segment["end"]

        raw_file        = raw_files[i]
        final_file      = output_folder / f"segment_{i}.mp3"

        source_duration = source_end - source_start

        # calculate available window to next segment
        if i + 1 < len(transcript):
            next_start = transcript[i + 1]["start"]
            available_window = next_start - source_start  # includes silence gap
        else:
            available_window = source_duration  # last segment — use source only

        raw_tts_duration = get_audio_duration_ms(str(raw_file))
        speed_factor, strategy = compute_target_speed(
            source_duration, raw_tts_duration, available_window
        )

        # apply speed adjustment
        if strategy == "none":
            # no change — just move raw file to final location
            import shutil
            shutil.copy(str(raw_file), str(final_file))
            final_duration = raw_tts_duration
            none_count += 1

        else:
            # apply ffmpeg atempo
            success = speed_adjust_audio(str(raw_file), str(final_file), speed_factor)

            if success:
                final_duration = get_audio_duration_ms(str(final_file))
            else:
                # ffmpeg failed — fall back to raw file
                import shutil
                shutil.copy(str(raw_file), str(final_file))
                final_duration = raw_tts_duration
                strategy = "none"

            if strategy == "mild":
                mild_count += 1
            elif strategy == "capped":
                capped_count += 1

        # record metrics
        metric = build_timing_metric(
            segment_index=i,
            original_text=segment.get("original", ""),
            translated_text=segment["translated"],
            source_start=source_start,
            source_end=source_end,
            raw_tts_duration=raw_tts_duration,
            final_tts_duration=final_duration,
            speed_factor=speed_factor,
            strategy=strategy
        )
        timing_metrics.append(metric)

        ratio_display = f"{raw_tts_duration / source_duration:.2f}x" if source_duration > 0 else "N/A"
        print(
            f"   [{i:03d}] source={source_duration:.2f}s | "
            f"raw={raw_tts_duration:.2f}s | "
            f"ratio={ratio_display} | "
            f"strategy={strategy} | "
            f"final={final_duration:.2f}s"
        )

    # ── STEP 3: Save metrics 
    save_timing_metrics(timing_metrics, timing_metrics_output_path)

    print(f"\n   Adjustment summary:")
    print(f"   no_change={none_count} | mild_speedup={mild_count} | capped={capped_count}")
    print(f"   (capped segments will use adaptive placement in audio reconstruction)")
    print(f"{'='*60}\n")

    return str(output_folder)