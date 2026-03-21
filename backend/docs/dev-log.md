# MediaFlow Distributed Engine — Dev Log

> AI-powered video dubbing pipeline. Put in a video, get back a fully translated and dubbed version. Everything from speech recognition to voice synthesis runs automatically.

---

## Table of Contents

- [Project Overview](#project-overview)
- [Initial System Design](#initial-system-design)
- [March 4 — Project Initialization](#march-4-2026--project-initialization)
- [March 7 — Transcript Storage](#march-7-2026--transcript-storage)
- [March 8 — Core Pipeline Development](#march-8-2026--core-pipeline-development)
- [March 9 — Text-to-Speech Integration](#march-9-2026--text-to-speech-integration)
- [March 10 — Audio Reconstruction](#march-10-2026--audio-reconstruction)
- [Bug Fix — Multiple Voices](#bug-fix--multiple-voices-in-a-single-video)
- [Feature — Optional Background Music](#feature--optional-background-music)
- [Current Working Pipeline](#current-working-pipeline)
- [Current Limitations](#current-limitations)
- [Future Improvements](#future-improvements)
- [Testing Observations](#pipeline-testing-observations-march-10-2026)
- [Engineering Lessons](#key-engineering-lessons)
- [March 17 — Hallucination Protection & Pipeline Wiring](#march-17-2026--hallucination-protection--pipeline-wiring)
- [March 18 — Segment Overlap Fix & Speed Adjustment](#march-18-2026--segment-overlap-fix--speed-adjustment)
- [March 21 — Translation Quality & Audio Sync Improvements](#March 21, 2026 — Translation Quality & Audio Sync Improvements)
- [March 22 — Audio Sync & Speed Consistency Fix](#March 22, 2026 — Audio Sync & Speed Consistency Fix)

---  


## Project Overview

The pipeline works in stages:

```
Video Input
    ↓
Audio Extraction
    ↓
Speech-to-Text
    ↓
Transcript Translation
    ↓
Text-to-Speech Generation
    ↓
Audio Timeline Reconstruction
    ↓
Optional Background Music Separation
    ↓
Final Audio Mix
    ↓
Merge With Original Video
    ↓
Final Dubbed Video
```

The main goal is to simulate a real-world media processing pipeline with a focus on modular backend architecture and scalable AI service integration.

---

## Initial System Design

Before writing any code, I planned out the full pipeline conceptually. This saved a lot of time later because I already knew what each stage needed to do and how they connected.

### Planned Pipeline

```
1.  Validate input video
2.  Extract audio from video
3.  Normalize audio format
4.  Transcribe audio with timestamps
5.  Save transcript
6.  Translate transcript
7.  Save translated transcript
8.  Generate speech from translated text
9.  Rebuild audio timeline
10. Merge new audio with original video
11. Output translated video
```

### Tech Stack

| Tool | Purpose |
|------|---------|
| FFmpeg | Video and audio processing |
| Groq Whisper | Speech-to-text |
| Groq API | Translation |
| Edge TTS | Speech synthesis |
| PyDub | Audio timeline reconstruction |
| Demucs | Background music separation |

---

## March 4, 2026 — Project Initialization

**What I did:**
- Initialized the repository
- Created the backend project structure
- Added `.gitignore` and `.gitkeep`
- Configured environment variables

**Initial folder structure:**

```
app/
  services/
  pipeline/
  utils/
scripts/
storage/
```

I separated the logic into services and pipeline layers from the start. Keeping these two concerns apart makes the system much easier to maintain and debug as it grows.

---

## March 7, 2026 — Transcript Storage

Created folder structure for storing transcript files.

**Why this matters:** STT results need to be saved to disk, not just kept in memory:

- They get reused by the translation stage later in the pipeline
- Useful when debugging — I can inspect exactly what the STT produced
- If something fails in a later stage, I can rerun it without redoing audio processing from scratch

---

## March 8, 2026 — Core Pipeline Development

### Input Validation & Audio Extraction

**Problem:** Users can upload pretty much anything — unsupported formats, corrupted files, invalid inputs. The system needs to handle this gracefully instead of crashing halfway through.

**Solution:** Added a validation step at the very beginning of the pipeline before anything else runs, plus audio extraction using FFmpeg.

```
Video
  ↓
Validate Input
  ↓
Extract Audio
```

---

### Speech-to-Text Integration

Integrated the **Groq Whisper API** for speech-to-text. It produces timestamped transcript segments saved to:

```
storage/transcripts/
```

These timestamps are important — they're used later for TTS generation and keeping audio in sync with the video.

---

### Transcript Translation

**Problem with the naive approach** — one API call per segment would be terrible for performance:

```
segment → API call
segment → API call
segment → API call
...
```

**What I did instead:** Implemented batch-based translation — multiple segments in a single API request:

```
multiple segments → single API call
```

Benefits:
- Lower latency overall
- Less API usage
- Better translation consistency (the model sees more context at once)

---

### Error Handling

Added validation checks throughout the pipeline for:

- Missing audio files
- Unsupported formats
- API failures
- File existence checks

The goal is to **fail early with a clear error message**, rather than silently breaking halfway through a long video.

---

### Pipeline Refactoring

After getting the initial version working, I refactored into proper modules.

**Before:** single script handling everything

**After:**

```
services/
  stt_service.py
  translate_service.py
  tts_service.py

pipeline/
  video_pipeline.py
```

This separation makes it easier to work on individual parts without touching everything else. Debugging is faster too — I can test each service in isolation.

---

## March 9, 2026 — Text-to-Speech Integration

### Edge TTS Service

Implemented TTS using **Edge TTS**. Each translated segment gets its own audio file:

```
segment_0.mp3
segment_1.mp3
segment_2.mp3
...
```

These get assembled into the final audio track later.

---

### Improving Translation Realism

**Problem:** Initial translations were too formal for spoken dialogue. Formal text synthesized into speech sounds unnatural — like a robot reading a legal document.

**Fix:** Updated the translation prompt to ask for conversational language. Translations now sound much more like how people actually speak.

---

## March 10, 2026 — Audio Reconstruction

### Combining TTS Segments

To rebuild the final audio track from all the individual segments:

1. Create a silent audio track as the base
2. Place each segment at its original timestamp
3. Merge everything together

Used **PyDub** to overlay the segments. Each segment is placed at `segment["start"]` — that's what keeps the speech in sync with the video.

---

### Background Music Preservation

**Problem:** Replacing the full audio track removed everything — not just the original voice, but also all background music and ambient sound. The resulting video felt weirdly sterile.

**Solution:** Used **Demucs** to separate the original audio into:

```
vocals
background music
```

The pipeline keeps the background music and overlays the generated speech on top of it.

---

### Final Audio Mixing

The final audio is a combination of:

```
Generated TTS speech
+
Original background music
```

This produces a much more natural-sounding dubbed track compared to voice-only output.

---

### Final Video Merge

The last step merges the original video stream with the new audio track using **FFmpeg**, producing the final translated video file.

---

## Bug Fix — Multiple Voices in a Single Video

**The problem:** Every segment was randomly picking a different voice. The same speaker sounded like three different people:

```
segment 1 → voice A
segment 2 → voice B
segment 3 → voice C
```

**Root cause:** Voice selection was happening inside the segment generation loop, picking a new random voice on every iteration.

**Fix:** Moved voice selection outside the loop so it runs once per video:

```python
voice = select_voice(language)

for segment in segments:
    generate_tts(segment, voice)
```

The entire video now uses a consistent voice throughout.

---

## Feature — Optional Background Music

Added a configuration flag:

```python
use_background_music: bool
```

| Value | Behavior |
|-------|----------|
| `True` | Run Demucs, preserve original background audio |
| `False` | Output voice-only audio |

This makes the pipeline useful for more use cases — not just full dubbing but also voice-only outputs.

---

## Current Working Pipeline

```
Video Upload
    ↓
Validate Video
    ↓
Extract Audio (FFmpeg)
    ↓
Speech To Text (Groq Whisper)
    ↓
Save Transcript
    ↓
Translate Transcript (Groq API)
    ↓
Generate Speech Segments (Edge TTS)
    ↓
Combine Segments (PyDub)
    ↓
Merge With Original Background Audio
    ↓
Merge With Video (FFmpeg)
    ↓
Output Translated Video
```

---

## Current Limitations

- No speaker-aware voice selection
- No lip synchronization
- No voice cloning
- No emotion-aware speech
- No transcript normalization
- No context-aware translation

---

## Future Improvements

### Speaker Detection
Automatically detect which speaker is talking and assign them a consistent voice. Right now everyone gets the same voice — fixing this would make dubbing feel much more realistic for multi-speaker videos.

### Lip Sync
Integrate a model like **Wav2Lip** to synchronize generated speech with original mouth movements. This is probably the biggest visual issue with current output.

### Voice Cloning
Use a model like **XTTS** to generate speech in the original speaker's actual voice instead of a generic TTS voice.

### Transcript Cleaning
Add an LLM post-processing step that cleans up STT output — removing filler words, fixing punctuation, and normalizing code-switched or mixed-language speech before translation.

### Emotion Modeling
Map detected emotions to speech parameters:

```
Sad    → slower speech
Happy  → faster speech
Angry  → higher pitch
```

---

## Pipeline Testing Observations (March 10, 2026)

While testing on longer videos, I ran into a couple of issues. Neither is fixed yet — just documenting what I observed and what I think is causing them.

---

### Issue 1 — Audio Timing and Speech Speed Inconsistency

**Test scenario:** 1 minute 15 second video.

**What I observed:**

All individual TTS segments sounded clear on their own (though still a bit robotic). But after merging into the final audio:

- Sometimes the next segment started before the previous one finished → small overlaps
- Some parts sounded too fast, other parts sounded normal
- The overall dubbed audio didn't feel natural

Interestingly, playing the individual segments separately sounded fine. The problem mostly showed up **after merging them into the timeline**.

**Possible causes:**
1. Timing misalignment while overlaying segments using PyDub
2. I experimented with changing segment speed during merging, which may have affected playback rate
3. I didn't explicitly control voice pitch or speaking rate during TTS generation

> **Status:** Not fixed yet. Known limitation — will investigate in future iterations.

---

#### Investigation — Timing Analysis

After noticing the overlaps, I wanted to understand whether the problem was in the merging step or somewhere earlier. So I added a timing measurement step inside the TTS service.

For every segment, I record:

```
source_duration  = original speech duration (from STT timestamps)
tts_duration     = duration of generated TTS audio
expansion_ratio  = tts_duration / source_duration
```

These get saved to `timing_metrics.json`. Each entry looks like:

```json
{
  "segment_index": 3,
  "original_text": "...",
  "translated_text": "...",
  "source_duration": 1.2,
  "tts_duration": 2.1,
  "expansion_ratio": 1.75
}
```

**Results from testing (Hindi → English, 1m 15s video):**

- Average expansion ratio: **~1.7x**
- Some segments expanded **3–4x** longer than original speech
- Worst cases were very short Hindi phrases under 1 second

Example I actually saw:

```
Original Hindi speech duration:  0.8s
Generated English TTS duration:  2.7s
Expansion ratio:                 ~3.4
```

**What this tells me:**

The problem isn't just the merging step. The real issue is that **translated English sentences are often much longer than the original Hindi speech**. Short Hindi phrases expand into longer English sentences. Since TTS generates audio based on the translated text, the audio becomes longer than the original time slot allows.

When these longer segments get placed back on the original timeline, they extend past their allocated window — which explains the overlaps and pacing issues.

> **Status:** Timing metrics now recorded automatically per segment. Fix not implemented yet, but root cause confirmed — **duration expansion between languages is the main contributor.**

---

### Issue 2 — Translation Hallucination with Mixed-Language Content

**Test scenario:** Hindi video where the speaker mixes Hindi and English technical terms (very common in tech content).

**STT output** (worked correctly):

```json
[
  {
    "start": 0,
    "end": 4.2,
    "text": "अगर तुम वाइब कोडिंग से आपस बना रहा हो तुम ये गलती पका कर रहा हो जो कि है बहुत ही सिंपल"
  }
]
```

The phrase **"वाइब कोडिंग"** is just the Hindi pronunciation of **"vibe coding"**.

**Translation output:**

```json
[
  {
    "start": 0,
    "end": 4.2,
    "original": "अगर तुम वाइब कोडिंग से आपस बना रहा हो...",
    "translated": "If you're building with Vue, you're probably making this super simple mistake"
  }
]
```

**The problem:** The word **"वाइब" (vibe)** was translated as **"Vue"** — the frontend framework. The speaker was talking about vibe coding, but the output makes it sound like they're talking about Vue.js. This is a **translation hallucination**.

**Why I think this is happening:**

The model is trying to interpret a transliterated English word inside a Hindi sentence. Since the Devanagari spelling of "vibe" sounds somewhat similar to "Vue", the model probably guessed the more common technical term it's seen in training data.

This is a known problem with **code-switched language** — when a speaker switches between two languages mid-sentence. The model doesn't always handle transliterated technical terms well.

**Ideas for fixing this later:**
- Detect transliterated English technical words before sending to translation
- Preserve those words as-is instead of translating them
- Maintain a dictionary of technical terms that should never be modified
- Add a post-translation validation step to catch obvious hallucinations

---

## Key Engineering Lessons

### 1. Design the pipeline before coding
Planning the architecture first — even just on paper — prevented a lot of messy implementation. I knew exactly what each stage needed as input and what it had to produce as output before writing a single line.

### 2. Modular services simplify debugging
Separating STT, translation, and TTS into their own services made the whole system much easier to work with. When something breaks, I can test each service in isolation and know exactly where the problem is.

### 3. Real AI systems require multiple layers
A working AI media pipeline isn't just one model — it's a combination of audio processing, language understanding, speech synthesis, and video synchronization. Getting all of these to work together reliably is where most of the engineering challenge actually lives.

---

*Last updated: March 10, 2026*





---

## March 17, 2026 — Hallucination Protection & Pipeline Wiring

### Fix — Hallucination Protection for Mixed-Language Content

**Context:** March 10 testing showed transliterated English technical terms like "वाइब कोडिंग" were being mistranslated (e.g. → "Vue").

**What was implemented:**

**Step 1 — Term detection with `[KEEP]` markers:**

Before sending to the translation API, detected transliterated technical terms get wrapped:
```
Input:  "अगर तुम वाइब कोडिंग से आपस बना रहा हो"
Marked: "अगर तुम [KEEP]वाइब कोडिंग[/KEEP] से आपस बना रहा हो"
```

The translation prompt explicitly instructs the model to pass anything inside `[KEEP]` tags through verbatim — no guessing.

**Step 2 — Transcript cleaning pass:**

A separate LLM pass runs before translation to clean up STT noise — fixing punctuation, removing filler artifacts, normalizing code-switched phrases — so the translation model gets cleaner input.

> **Status:** Fixed. "वाइब → Vue" hallucination no longer occurs.

---

### Refactor — Pipeline Wiring

Two values that were previously not being passed between stages are now wired through:

- Whisper's **detected language** is passed into `translate_text` so term detection and cleaning prompts know what source language they're working with
- **`timing_metrics_path`** is passed into `build_final_audio` so the reconstruction stage can read the per-segment stretch strategy

Without this, both stages were operating without context they needed.

---

## March 18, 2026 — Segment Overlap Fix & Speed Adjustment

### Fix (Partial) — Timing-Aware Speed Adjustment per Segment

**Context:** Timing metrics from March 10 confirmed TTS audio was often much longer than the original source slot, causing overlaps.

**What was implemented:**

After generating raw TTS, the pipeline now measures the expansion ratio and applies `ffmpeg atempo` to compress it back into the original slot:
```
expansion_ratio ≤ mild threshold  → speed up exactly to fit
expansion_ratio > 2.0x            → cap at 1.8x to preserve quality
```

The 1.8x cap is intentional — `atempo` beyond ~2x causes audible distortion. The strategy used per segment (`exact_fit` or `capped`) gets saved into `timing_metrics.json` for the reconstruction stage to use.

 
> **Status:** Partially fixed. Segments no longer skip or break. However, the final audio still sounds uneven — some segments play at normal speed while others feel noticeably fast. Heavily expanded segments that hit the 1.8x cap are the likely cause. Under investigation.

---

### Fix — Adaptive Timeline Placement to Prevent Segment Overlap

**Context:** Even after speed adjustment, segments placed at fixed timestamps were still overlapping when a previous segment overflowed its slot.

**What was implemented:**

Replaced the fixed timestamp placement system with a **cursor-based system**:

- Each segment is placed at its original timestamp **if possible**
- If the previous segment overflowed, the cursor is pushed forward to after it finishes
- Sync recovers automatically at the next natural silence gap
```
Before:  every segment placed at original timestamp regardless of overflow
After:   cursor advances when overflow detected, snaps back at silence gaps
```

> **Status:** Fixed. Segments no longer overlap in the final audio track. 




---

## March 21, 2026 — Translation Quality & Audio Sync Improvements

Four issues identified and fixed this session, all directly impacting
how well the final dubbed audio syncs with the original video.

---

### Fix 1 — Isometric Translation (Speed Inconsistency Root Cause)

**Problem:**
The translation LLM was producing English text without any awareness
of how long it had to be spoken. A 1.58 second Hindi segment was being
translated into English text that took 4+ seconds to speak. After
atempo compression, it still overflowed — causing the fast/slow
inconsistency in final audio.

**Root cause:**
`duration_seconds` was already being sent to the LLM in the batch
payload but the system prompt never told the model to use it.
The model ignored it completely.

**Fix:**
Added isometric translation rule to system prompt:
```
ISOMETRIC TRANSLATION — each segment has a duration_seconds field.
Your translation must be speakable in approximately that many seconds.
Do NOT cut meaning. Instead use:
- Contractions: "do not" → "don't"
- Natural short forms: "in order to" → "to"
- Active voice: "is going to be built" → "will build"
```

**Why this helps audio sync:**
When translated text is closer in spoken length to the original,
the TTS expansion ratio drops. Less atempo compression needed.
Less compression = more natural sounding speech = better sync.

---

### Fix 2 — Short Segment Merging (Fragment Translations)

**Problem:**
Whisper splits audio into segments based on silence gaps. Very short
segments (under 1.5 seconds) were often mid-sentence fragments:
```
Segment: "and now the latest things"       (1.94s)
Segment: "is building with islands"        (1.70s)
```

These translated as disconnected fragments — sounded weird in the
final audio with unnatural gaps mid-sentence.

**Fix:**
Added `merge_short_segments()` before the cleaning pass:
```python
def merge_short_segments(segments, min_duration=2.0):
    # merges segments shorter than min_duration with the next segment
```
```
Before: "and now the latest things" + "is building with islands"
After:  "and now the latest thing is building with islands"
```

**Why this helps audio sync:**
Merged segments generate one continuous TTS audio clip instead of
two short ones with a gap between them. The gap that existed between
the two original segments is now available as speaking room for the
merged translation — reducing the need for speed compression.

---

### Fix 3 — Cleaning Pass Preserving Mixed Language

**Problem:**
The STT cleaning pass was converting Hinglish/mixed language words
into pure Hindi equivalents:
```
Original spoken: "और अब जो सबसे latest चीजें है"
After cleaning:  "और अब जो सबसे नवीनतम चीजें हैं।"
                                ↑ "latest" replaced with pure Hindi
```

This is wrong — the speaker said "latest" in English deliberately.
Replacing it changes the register and tone of the translation.

**Fix:**
Added explicit rule to cleaning prompt:
```
NEVER translate words to pure {source_language} —
preserve English/mixed words exactly as spoken.
```

**Why this helps translation quality:**
The translation LLM now receives the text closer to what was actually
spoken. Term detection and [KEEP] markers work correctly because the
mixed-language words are still present in their original form.

---

### Fix 4 — Context Window Increased

**Problem:**
With `CONTEXT_WINDOW = 3`, the translation model sometimes lost
consistency across batches — using different phrasing for the same
concept earlier vs later in the video.

**Fix:**
Increased to `CONTEXT_WINDOW = 5` — model now sees 5 previous
translated segments before each new batch.

**Why this helps:**
Consistent terminology throughout the video means TTS generates
audio with consistent rhythm and pacing — fewer jarring transitions
between segments in the final dubbed track.

---

### Combined Impact on Audio Pipeline

These four fixes work together in the pipeline:
```
Merge short fragments          → fewer gaps, more speaking room per segment
Isometric translation          → translated text fits original time slot better  
Preserve mixed language        → cleaner input to translation LLM
Larger context window          → consistent terminology = consistent TTS rhythm
                                                    ↓
                              Lower expansion ratios in TTS
                                                    ↓
                              Less atempo compression needed
                                                    ↓
                              More natural sounding final audio
```

> **Status:** Translation stage significantly improved. Expansion ratios
> are lower. Fragment segments eliminated. Speed inconsistency reduced
> but not fully resolved — timeline reconstruction fix still pending.

*Last updated: March 21, 2026*



---

## March 22, 2026 — Audio Sync & Speed Consistency Fix

This session focused on fixing the core audio timing issue — final dubbed
audio was 1:22 for a 1:15 original video. After fixes, it's now 1:17.

---

### The Core Problem — Speed Was Being Calculated Wrong

**What was happening:**
```
source_duration  = time original Hindi was spoken    (e.g. 2.26s)
tts_duration     = time English TTS audio takes      (e.g. 4.08s)
ratio            = 4.08 / 2.26 = 1.8x
speed applied    = 1.8x atempo → sounds very fast
```

The pipeline was squeezing TTS audio into `source_duration` only —
ignoring the silence gap that exists before the next segment starts.
That gap is available speaking room that was being wasted.

**Root cause confirmed from timing_metrics.json:**
```
Segment 13: source=1.64s  ratio=1.97x  → very fast
Segment 14: source=1.68s  ratio=2.01x  → capped, overflow into next
Segment 6:  source=2.26s  ratio=1.80x  → fast
```

All fast segments had short source slots. Long source slots were fine.
The silence gap between segments was never being used.

---

### Fix 1 — Available Window (tts_service.py)

Instead of fitting TTS into `source_duration`, the pipeline now calculates
the full available window to the next segment start:
```python
# OLD — only used source slot
speed_factor = tts_duration / source_duration

# NEW — uses full available window including silence gap
if i + 1 < len(transcript):
    next_start = transcript[i + 1]["start"]
    available_window = next_start - source_start  # includes silence gap
else:
    available_window = source_duration

speed_factor = tts_duration / available_window
```

**Applied to segment 13:**
```
OLD: fit 3.24s into 1.64s slot → ratio 1.97x → very fast
NEW: fit 3.24s into 3.32s window (includes gap) → ratio 0.97x → no speed needed
```

---

### Fix 2 — Speed Cap Reduced from 1.8x to 1.4x

Research confirms humans perceive speed change above 1.4x.
Previous cap of 1.8x was causing noticeably fast segments.
```python
# OLD
RATIO_MAX_STRETCH = 2.0
return 1.8, "capped"

# NEW  
RATIO_MAX_STRETCH = 1.4
return 1.4, "capped"
```

---

### Fix 3 — Adaptive Placement Tracks Overflow Separately

`audio_reconstruction.py` now distinguishes three placement strategies:
```
"on_time"  → placed at exact original timestamp, fits perfectly
"pushed"   → cursor advanced past original timestamp to avoid overlap
"overflow" → fits in original slot but audio spills into silence gap
```

This makes it easier to debug sync issues — know exactly which segments
are causing drift and by how much.

---

### Fix 4 — Short Segment Merge Threshold Increased

Increased `min_duration` from 1.5s to 2.0s in `translate_service.py`.
More fragment segments now get merged before translation:
```
Before: segments 16, 17 still fragments at 1.94s and 1.70s
After:  both merged into one complete sentence
```

---

### Fix 5 — Cleaning Pass Preserves Mixed Language

Added rule to STT cleaning prompt:
```
NEVER translate words to pure {source_language} —
preserve English/mixed words exactly as spoken.
```

Prevents the cleaning LLM from converting Hinglish words like
"latest" into pure Hindi equivalents before translation.

---

### Results

| Metric | Before | After |
|--------|--------|-------|
| Final audio duration | 1:22 | 1:17 |
| Original video duration | 1:15 | 1:15 |
| Segments at ratio > 1.6x | Several | Zero |
| Capped segments (>2.0x) | Present | Zero |
| Speed cap | 1.8x | 1.4x |

**Expansion ratio distribution after fix:**
```
ratio < 1.1   (perfect):    7 segments  
ratio 1.1-1.4 (good):       9 segments  
ratio 1.4-1.6 (acceptable): 5 segments  
ratio > 1.6   (problem):    0 segments  
```

> **Status:** Significantly improved. Audio timing is much closer to
> original. Remaining gap (1:17 vs 1:15) is from segments where even
> the full available window isn't enough — translation text still
> slightly too long. Multilingual testing pending.

---

### Open Questions

- Does available window fix work equally well for non-Hindi languages?
- Does isometric translation rule produce consistently shorter text
  across French, Spanish, Japanese?
- Voice quality (Edge TTS robotic) — next improvement after sync stable.



*Last updated: March 22, 2026*