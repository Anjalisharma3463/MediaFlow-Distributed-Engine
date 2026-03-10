# MediaFlow Distributed Engine – Engineering Development Log

## Project Overview

**MediaFlow Distributed Engine** is an AI-powered video dubbing pipeline that transforms a video into a translated version with synthesized speech.

The system performs the following processing stages:

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

The objective of this project is to simulate a **real-world media processing pipeline**, focusing on modular backend architecture and scalable AI service integration.

---

# Initial System Design

Before implementing the system, the pipeline was designed conceptually.

### Planned Pipeline

```
1. Validate input video
2. Extract audio from video
3. Normalize audio format
4. Transcribe audio with timestamps
5. Save transcript
6. Translate transcript
7. Save translated transcript
8. Generate speech from translated text
9. Rebuild audio timeline
10. Merge new audio with original video
11. Output translated video
```

### Tech Stack

```
FFmpeg – video and audio processing
Groq Whisper – speech-to-text
Groq API – translation
Edge TTS – speech synthesis
PyDub – audio timeline reconstruction
Demucs – background music separation
```

---

# March 4, 2026 — Project Initialization

### Work Done

* Initialized repository
* Created backend project structure
* Added `.gitignore` and `.gitkeep`
* Configured environment variables

### Initial Architecture

```
app/
  services/
  pipeline/
  utils/
scripts/
storage/
```

### Reasoning

Separating logic into **services and pipeline layers** ensures the system remains modular and maintainable.

---

# March 7, 2026 — Transcript Storage

### Work Done

Created folder structure for storing transcript files.

### Reason

Speech-to-text results must be persisted because they:

* are reused by the translation stage
* help with debugging
* allow later pipeline stages to be rerun without reprocessing audio

---

# March 8, 2026 — Core Pipeline Development

## Input Validation & Audio Extraction

### Problem

Users may upload:

* unsupported formats
* corrupted video files
* invalid inputs

### Solution

Added a **video validation step** before pipeline execution and implemented **audio extraction using FFmpeg**.

Pipeline stage:

```
Video
↓
Validate Input
↓
Extract Audio
```

---

## Speech-to-Text Integration

### Work Done

Implemented speech-to-text using **Groq Whisper API**.

STT produces **timestamped transcript segments**, which are stored in:

```
storage/transcripts/
```

These segments are used for translation and TTS generation.

---

## Transcript Translation

### Work Done

Implemented **batch-based transcript translation** using the Groq API.

### Reasoning

Instead of making one API request per segment:

```
segment → API call
segment → API call
segment → API call
```

The system sends multiple segments in a single request:

```
multiple segments → single API call
```

### Benefits

* lower latency
* reduced API usage
* improved translation consistency

---

## Error Handling

Added validation for:

* missing audio files
* unsupported formats
* API failures
* file existence checks

### Goal

Ensure pipeline failures **fail early with clear error messages**.

---

# Pipeline Refactoring

The system was refactored into **modular services and pipeline orchestration**.

Before:

```
single script handling everything
```

After:

```
services/
  stt_service.py
  translate_service.py
  tts_service.py

pipeline/
  video_pipeline.py
```

### Reason

Improves:

* maintainability
* scalability
* debugging
* code clarity

---

# March 9, 2026 — Text-to-Speech Integration

## Edge TTS Service

### Work Done

Implemented a **Text-to-Speech service using Edge TTS**.

Each translated segment generates a separate audio file:

```
segment_0.mp3
segment_1.mp3
segment_2.mp3
```

These segments are later combined into a final audio track.

---

# Improving Translation Realism

### Problem

Initial translations sounded overly formal and unnatural for spoken dialogue.

### Solution

Updated the translation prompt to produce **conversational language** suitable for natural speech.

---

# March 10, 2026 — Audio Reconstruction

## Combining TTS Segments

To rebuild the final audio track:

1. Create a silent audio track
2. Place each segment at its timestamp
3. Merge all segments

### Implementation

Used **PyDub** to overlay audio segments.

Each segment begins at:

```
segment["start"]
```

This preserves synchronization between generated speech and the original video.

---

# Background Music Preservation

### Problem

Replacing the full audio removed:

* background music
* ambient sound

This made the resulting video feel unnatural.

### Solution

Used **Demucs** to separate audio into:

```
vocals
background music
```

The pipeline retains background music and overlays the generated speech.

---

# Final Audio Mixing

Final audio consists of:

```
Generated TTS speech
+
Original background music
```

This produces a more natural dubbed audio track.

---

# Final Video Merge

The final pipeline step merges:

```
Original video stream
+
Generated audio track
```

Using **FFmpeg**, producing the final translated video.

---

# Bug Fix — Multiple Voices in a Single Video

### Problem

Each segment randomly selected a voice.

Example:

```
segment 1 → voice A
segment 2 → voice B
segment 3 → voice C
```

This caused the same speaker to sound like multiple people.

---

### Root Cause

Voice selection occurred **inside the segment generation loop**.

---

### Fix

Voice selection is now performed **once per video**.

```
voice = select_voice(language)

for segment in segments:
    generate_tts(segment, voice)
```

### Result

The entire video now uses a **consistent voice**.

---

# Feature — Optional Background Music

Added configuration flag:

```
use_background_music: bool
```

Modes:

```
True  → preserve original background music
False → generate voice-only audio
```

This allows the pipeline to support multiple use cases.

---

# Current Working Pipeline

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

# Current Limitations

• Speaker-aware voice selection
• Lip synchronization
• Voice cloning
• Emotion-aware speech
• Transcript normalization
• Context-aware translation

---

# Future Improvements

### Speaker Detection

Automatically detect speaker identity and assign appropriate voices.

---

### Lip Sync

Integrate models such as:

```
Wav2Lip
```

to synchronize speech with mouth movement.

---

### Voice Cloning

Use models such as:

```
XTTS
```

to generate speech in the **original speaker’s voice**.

---

### Transcript Cleaning

Add LLM post-processing to:

* remove filler words
* fix punctuation
* normalize mixed-language speech

---

### Emotion Modeling

Map emotions to speech parameters.

Example:

```
Sad → slower speech
Happy → faster speech
Angry → higher pitch
```

---

# Key Engineering Lessons

### 1 — Design the pipeline before coding

Planning the system architecture helped prevent messy implementation.

---

### 2 — Modular services simplify debugging

Separating STT, translation, and TTS improved maintainability.

---

### 3 — Real AI systems require multiple layers

A practical AI media pipeline requires integrating:

```
audio processing
language understanding
speech synthesis
video synchronization
```

---
 

# Pipeline Testing Observations (March 10, 2026)

During pipeline testing on longer videos, several issues were observed that require further investigation and improvement.

---

## Issue 1 — Audio Timing and Speech Speed Inconsistency

### Test Scenario

The pipeline was tested using a **1 minute 15 second video** to evaluate behavior on longer inputs.

### Observation

All **individual TTS audio segments** generated by Edge TTS sounded clear and understandable (though slightly robotic).

However, issues appeared in the **final merged audio track**:

• Some segments started **before the previous segment finished**, causing slight overlaps.
• Speech speed sometimes sounded **too fast**, while other parts sounded more natural.
• The timing inconsistency affected the overall naturalness of the final dubbed video.

### Possible Causes

Several potential causes were identified:

1. **Audio overlay timing issues** during segment merging using PyDub.
2. **Speed modification during audio processing**, which may unintentionally alter playback rate.
3. Lack of **explicit control over voice pitch and rate** during TTS generation.

### Current Status

The issue has **not yet been fixed**.
It has been documented as a known limitation to address in future pipeline improvements.

---

## Issue 2 — Translation Hallucination with Mixed-Language Content

### Test Scenario

A Hindi video containing **mixed Hindi and English technical terms** was processed through the pipeline.

### STT Output

Speech-to-text correctly transcribed the spoken content:

```json
[
  {
    "start": 0,
    "end": 4.2,
    "text": "अगर तुम वाइब कोडिंग से आपस बना रहा हो तुम ये गलती पका कर रहा हो जो कि है बहुत ही सिंपल"
  }
]
```

The phrase **"वाइब कोडिंग"** is a Hindi transliteration of the English term **"vibe coding"**.

---

### Translation Output

```json
[
  {
    "start": 0,
    "end": 4.2,
    "original": "अगर तुम वाइब कोडिंग से आपस बना रहा हो तुम ये गलती पका कर रहा हो जो कि है बहुत ही सिंपल",
    "translated": "If you're building with Vue, you're probably making this super simple mistake"
  }
]
```

### Problem

The term **"वाइब" (vibe)** was incorrectly translated to **"Vue"**, which is unrelated to the original meaning.

This is an example of **LLM hallucination during translation**.

### Root Cause

This likely occurred because:

• The model attempted to **interpret a transliterated English term inside Hindi text**
• The model associated "वाइब" with a **more common technical word (Vue)**

This type of error often appears in **code-switched language**, where speakers mix languages within the same sentence.

### Impact

This leads to **semantic distortion in translated output**, which can produce misleading subtitles and incorrect audio dubbing.

### Possible Future Solutions

Potential solutions include:

• Adding a **technical term preservation layer** before translation
• Detecting **transliterated English words** inside Hindi text
• Maintaining a **dictionary of technical terms** that should not be translated
• Applying post-processing validation for translation output

---

These observations highlight real-world challenges when building **AI-driven media translation pipelines**, especially when handling **timing alignment and multilingual speech patterns**.

---

This addition is **very good for your repo**, because it shows:

✔ real testing
✔ debugging mindset
✔ understanding of AI limitations
✔ thinking about future fixes

Exactly what recruiters like to see.

---
 