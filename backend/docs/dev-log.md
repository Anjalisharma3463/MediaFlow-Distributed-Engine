# MediaFlow Distributed Engine – Engineering Development Log

## Project Overview

**MediaFlow Distributed Engine** is an AI-powered video dubbing pipeline that transforms a video into a translated version with synthesized speech.

The system performs the following steps:

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

The goal of this project is to simulate a **real-world media processing pipeline**, focusing on modular backend architecture and scalable AI service integration.

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
FFmpeg → audio extraction & video processing
Groq Whisper → speech-to-text
Groq API → translation
Edge TTS → speech synthesis
PyDub → audio alignment
Demucs → background music separation
FFmpeg → final video merge
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

Separating logic into **services and pipeline layers** ensures the system is modular and maintainable.

---

# March 7, 2026 — Transcript Storage

### Work Done

Created folder structure for storing transcript files.

### Reason

Speech-to-text results must be persisted because they are:

* reused by the translation stage
* useful for debugging
* required to rerun later pipeline stages without reprocessing audio

---

# March 8, 2026 — Core Pipeline Development

## Input Validation & Audio Extraction

### Problem

Users may upload:

* unsupported formats
* corrupted video files
* invalid inputs

### Solution

Added **video validation step** before pipeline execution.

Implemented **audio extraction using FFmpeg**.

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

Implemented speech-to-text functionality using **Groq Whisper API**.

### Output

Timestamped transcript such as:

```
0.00 - 3.20  Hello everyone welcome back
3.20 - 7.10  Today we are going to discuss AI
```

Transcripts are stored in:

```
storage/transcripts/
```

---

## Transcript Translation

### Work Done

Implemented **batch-based transcript translation** using the Groq API.

### Reasoning

Instead of making many API calls:

```
segment → API call
segment → API call
segment → API call
```

The system sends batches:

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
* API errors
* file existence checks

### Goal

Pipeline failures should **fail early with clear errors**.

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

Each translated segment now generates a separate audio file:

```
segment_0.mp3
segment_1.mp3
segment_2.mp3
```

These segments are later combined into a final audio track.

---

# Improving Translation Realism

### Problem

Initial translations sounded **too formal** for natural speech.

Example:

Formal:

```
यह अत्यंत अद्भुत अनुभव था
```

Natural speech:

```
यह सच में बहुत अच्छा अनुभव था
```

### Solution

Updated translation prompt:

```
Translate using conversational language used in real speech.
Avoid overly formal words.
```

This significantly improved the **naturalness of generated speech**.

---

# March 10, 2026 — Audio Reconstruction

## Combining TTS Segments

To rebuild the final audio track:

1. Create silent audio track
2. Place each segment at its timestamp
3. Merge all segments

### Implementation

Used **PyDub** to overlay audio segments.

Each segment starts at:

```
segment["start"]
```

This preserves **speech synchronization with the original video**.

---

# Background Music Preservation

### Problem

Replacing full audio removed:

* background music
* ambient sounds

This made the video feel unnatural.

### Solution

Used **Demucs** to separate audio into:

```
vocals
background music
```

The pipeline keeps background music and overlays generated speech on top.

---

# Final Audio Mixing

Final audio consists of:

```
Generated TTS speech
+
Original background music
```

This produces a **more realistic dubbed audio track**.

---

# Final Video Merge

The final pipeline step merges:

```
Original video stream
+
New generated audio
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

Result: the same speaker sounded like **multiple people**.

---

### Root Cause

Voice selection occurred **inside the segment generation loop**.

---

### Fix

Voice is now selected **once per video**.

Example:

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

This makes the system flexible for different use cases.

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

The system still lacks:

1. speaker-aware voice selection
2. lip synchronization
3. voice cloning
4. emotion-aware speech
5. transcript cleaning
6. context-aware translation

---

# Future Improvements

Planned enhancements include:

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

Planning the pipeline prevented messy architecture.

---

### 2 — Modular services simplify debugging

Separating STT, translation, and TTS improved maintainability.

---

### 3 — Real AI systems require multiple layers

A practical system requires integration of:

```
audio processing
language understanding
speech synthesis
video synchronization
```

---

# Where This Should Be Published

### 1️⃣ Inside the GitHub repository

Create:

```
docs/dev-log.md
```

---

### 2️⃣ LinkedIn (short posts)

Example topics:

* Fixing inconsistent TTS voices
* Designing a modular AI media pipeline
* Lessons from building an AI dubbing engine

---

### 3️⃣ Long-form technical blog

Recommended platforms:

* Hashnode
* Dev.to
* Medium

Possible blog title:

```
Building an AI Video Translation Pipeline from Scratch
```

---

# Recommended Repository Structure

```
MediaFlow-Distributed-Engine
│
├─ backend
├─ docs
│   ├─ dev-log.md
│   ├─ architecture.md
│   └─ pipeline-design.md
├─ README.md
└─ requirements.txt
```

---

# Development Writing Habit

For every feature or bug, document:

```
Problem
Root Cause
Solution
Lesson
```

Example:

```
Problem:
Segments had different voices.

Root Cause:
Voice was randomly selected per segment.

Solution:
Select voice once per video.

Lesson:
Shared configuration should be initialized outside loops.
```

This practice builds **engineering thinking and a strong technical portfolio**.

---

 