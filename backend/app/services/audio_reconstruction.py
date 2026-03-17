# audio_reconstruction.py
#
# Adaptive timeline placement for dubbed audio segments.
#
# THE PROBLEM THIS SOLVES:
#
# After speed adjustment in tts_service.py, most segments fit their slot.
# But some (strategy="capped") are still longer than their original slot
# because we capped speed at 1.8x to preserve natural sound quality.
#
# Naive approach (your original code):
#   Place every segment at its exact original timestamp.
#   Result: long segments overlap with the next segment → chaotic audio.
#
# Adaptive approach (this file):
#   Track a "cursor" — the earliest timestamp the next segment can start.
#   For each segment:
#     - preferred_start = original timestamp (sync with video)
#     - actual_start    = max(preferred_start, cursor)
#     - cursor          = actual_start + segment_duration + MIN_GAP
#
# This means:
#   - Short segments that fit → placed at exact original timestamp (perfect sync)
#   - Segments that were capped → placed as close to original as possible,
#     but pushed forward only as much as needed to avoid overlap
#   - Complete audio preserved — nothing is cut
#   - Sound quality preserved — no additional speed changes here
#   - Sync drifts slightly on long problematic sections but recovers
#     naturally at the next segment that fits its slot
#
# This is the same strategy Rask.ai and HeyGen use.
# Perfect sync + perfect quality + complete audio is not possible simultaneously.
# This balances all three as well as it can be done.

import json
import subprocess
from pathlib import Path
from pydub import AudioSegment


# CONFIGURATION

MIN_GAP_MS = 80   # minimum silence gap between segments in milliseconds
                  # prevents segments from running right into each other
                  # 80ms is the perceptual threshold — below this humans
                  # cannot distinguish gap from no gap


# UTILITIES

def get_audio_duration_ms(audio_file: str) -> int:
    """Get audio duration in milliseconds using ffprobe."""
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        audio_file,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        audio = AudioSegment.from_file(audio_file)
        return len(audio)
    return int(float(result.stdout.strip()) * 1000)


def load_timing_metrics(metrics_path: str) -> dict:
    """
    Load timing metrics from tts_service output.
    Returns dict keyed by segment_index for fast lookup.
    Returns empty dict if file not found — reconstruction still works,
    just without adaptive capping info.
    """
    metrics_file = Path(metrics_path)
    if not metrics_file.exists():
        print("No timing metrics file found — using basic placement")
        return {}

    with open(metrics_file, "r", encoding="utf-8") as f:
        metrics_list = json.load(f)

    return {m["segment_index"]: m for m in metrics_list}


# ADAPTIVE PLACEMENT ENGINE

def compute_placement_positions(
    transcript: list,
    segments_folder: Path,
    timing_metrics: dict
) -> list:
    """
    Compute the actual placement position for each segment on the timeline.

    For each segment:
      preferred_start = original transcript timestamp (video sync)
      actual_start    = max(preferred_start, cursor)  ← never overlap previous
      cursor          = actual_start + segment_duration + MIN_GAP_MS

    Returns list of placement dicts:
    [
      {
        "segment_index": 0,
        "preferred_start_ms": 1000,
        "actual_start_ms": 1000,
        "segment_duration_ms": 850,
        "pushed_ms": 0,           ← how much it was pushed forward from preferred
        "strategy": "on_time"     ← "on_time" | "pushed"
      }
    ]
    """
    placements = []
    cursor_ms = 0  # earliest the next segment can start

    for i, segment in enumerate(transcript):

        preferred_start_ms = int(segment["start"] * 1000)

        segment_file = segments_folder / f"segment_{i}.mp3"

        if not segment_file.exists():
            print(f"Missing segment file: {segment_file} — skipping")
            continue

        segment_duration_ms = get_audio_duration_ms(str(segment_file))

        # adaptive placement decision
        actual_start_ms = max(preferred_start_ms, cursor_ms)
        pushed_ms = actual_start_ms - preferred_start_ms
        strategy = "on_time" if pushed_ms == 0 else "pushed"

        placements.append({
            "segment_index":       i,
            "segment_file":        str(segment_file),
            "preferred_start_ms":  preferred_start_ms,
            "actual_start_ms":     actual_start_ms,
            "segment_duration_ms": segment_duration_ms,
            "pushed_ms":           pushed_ms,
            "strategy":            strategy
        })

        # advance cursor past end of this segment + minimum gap
        cursor_ms = actual_start_ms + segment_duration_ms + MIN_GAP_MS

        # log segments that were pushed
        if pushed_ms > 0:
            print(
                f"   [seg {i:03d}] pushed +{pushed_ms}ms "
                f"(preferred={preferred_start_ms}ms → actual={actual_start_ms}ms)"
            )

    return placements
 
# MAIN ENTRY  POINT

def build_final_audio(
    translated_transcript_path: str,
    segments_folder: str,
    original_audio_path: str,
    output_audio_path: str,
    timing_metrics_path: str = None,
    use_background_music: bool = True
) -> str:
    """
    Build final dubbed audio from TTS segments using adaptive placement.

    Pipeline:
    1. Load transcript and timing metrics
    2. Compute adaptive placement positions (no overlaps)
    3. Optionally extract background music
    4. Create silent timeline matching original video duration
    5. Place each segment at its computed position
    6. Overlay background music (if requested)
    7. Export final audio

    Args:
        translated_transcript_path: path to translated transcript JSON
        segments_folder:            folder containing segment_0.mp3, segment_1.mp3 etc
        original_audio_path:        original video audio (for duration + background)
        output_audio_path:          where to save final dubbed audio
        timing_metrics_path:        path to timing_metrics.json from tts_service
        use_background_music:       whether to extract and preserve background music
    """

    print(f"\n{'='*60}")
    print(f"AUDIO RECONSTRUCTION")
    print(f"{'='*60}")

    # ── 1. Load transcript  
    with open(translated_transcript_path, "r", encoding="utf-8") as f:
        transcript = json.load(f)

    print(f"   Segments  : {len(transcript)}")

    segments_folder_path = Path(segments_folder)

    # ── 2. Load timing metrics 
    timing_metrics = {}
    if timing_metrics_path:
        timing_metrics = load_timing_metrics(timing_metrics_path)

    # ── 3. Compute adaptive placement positions 
    print(f"\n   Computing adaptive placement...")
    placements = compute_placement_positions(transcript, segments_folder_path, timing_metrics)

    on_time_count = sum(1 for p in placements if p["strategy"] == "on_time")
    pushed_count  = sum(1 for p in placements if p["strategy"] == "pushed")
    print(f"   On-time: {on_time_count} | Pushed: {pushed_count}")

    # ── 4. Optional background music extraction 
    background_music = None

    if use_background_music:
        print(f"\n   Extracting background music...")
        try:
            from app.utils import voice_removal
            background_music_path = voice_removal.separate_audio_demucs(
                original_audio_path,
                "storage/temp/demucs_output"
            )
            background_music = AudioSegment.from_file(background_music_path)
            background_music = background_music - 26  # reduce volume
            print(f"Background music extracted")
        except Exception as e:
            print(f"Background music extraction failed: {e}")
            print(f"Continuing without background music")
            background_music = None

    # ── 5. Create timeline 
    print(f"\n   Building timeline...")
    original_duration_ms = get_audio_duration_ms(original_audio_path)

    # timeline must be long enough for all segments including pushed ones
    # find the furthest point any segment will reach
    if placements:
        last_placement = placements[-1]
        furthest_ms = last_placement["actual_start_ms"] + last_placement["segment_duration_ms"]
    else:
        furthest_ms = 0

    # use whichever is longer: original video duration or furthest segment end
    # this prevents audio cutoff if segments were pushed beyond video length
    timeline_duration_ms = max(original_duration_ms, furthest_ms + 500)

    tts_track = AudioSegment.silent(duration=timeline_duration_ms)

    # pad background music if needed
    if background_music is not None:
        if len(background_music) < timeline_duration_ms:
            background_music += AudioSegment.silent(
                duration=timeline_duration_ms - len(background_music)
            )

    print(f"   Original duration : {original_duration_ms / 1000:.2f}s")
    print(f"   Timeline duration : {timeline_duration_ms / 1000:.2f}s")

    # ── 6. Place segments onto timeline 
    print(f"\n   Placing segments...")

    placed_count  = 0
    skipped_count = 0

    for placement in placements:

        segment_file = Path(placement["segment_file"])

        if not segment_file.exists():
            skipped_count += 1
            continue

        segment_audio = AudioSegment.from_file(str(segment_file))
        actual_start  = placement["actual_start_ms"]

        tts_track = tts_track.overlay(segment_audio, position=actual_start)
        placed_count += 1

    print(f"   Placed: {placed_count} | Skipped (missing file): {skipped_count}")

    # ── 7. Merge with background music 
    if background_music is not None:
        print(f"\n   Mixing with background music...")
        final_audio = background_music.overlay(tts_track)
    else:
        final_audio = tts_track

    # ── 8. Export 
    output_path = Path(output_audio_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    final_audio.export(output_path, format="mp3")

    # ── 9. Placement report 
    print(f"\n{'='*60}")
    print(f"✅ AUDIO RECONSTRUCTION COMPLETE")
    print(f"   Output      : {output_path}")
    print(f"   Duration    : {len(final_audio) / 1000:.2f}s")
    print(f"   On-time     : {on_time_count}/{len(placements)} segments at original timestamp")
    print(f"   Pushed      : {pushed_count}/{len(placements)} segments shifted forward")
    if pushed_count > 0:
        avg_push = sum(p["pushed_ms"] for p in placements if p["pushed_ms"] > 0) / pushed_count
        print(f"   Avg push    : {avg_push:.0f}ms")
    print(f"{'='*60}\n")

    return str(output_path)