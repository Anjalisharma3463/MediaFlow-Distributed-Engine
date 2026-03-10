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