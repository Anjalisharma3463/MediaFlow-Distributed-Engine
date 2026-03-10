# MediaFlow Distributed Engine

MediaFlow is an AI-powered video dubbing pipeline that translates and regenerates speech in videos while preserving timing and background audio.

The system automatically:

- extracts audio from video
- transcribes speech
- translates transcripts
- generates speech in a new language
- reconstructs the audio timeline
- merges the new audio with the original video

---

# Pipeline Overview

```
Video Input
↓
Validate Input
↓
Extract Audio (FFmpeg)
↓
Speech-to-Text (Groq Whisper)
↓
Translate Transcript (Groq API)
↓
Generate Speech (Edge TTS)
↓
Combine Audio Segments (PyDub)
↓
Merge With Original Video (FFmpeg)
↓
Final Dubbed Video
```

---

# Tech Stack

| Component | Tool |
|----------|------|
| Video Processing | FFmpeg |
| Speech-to-Text | Groq Whisper |
| Translation | Groq API |
| Text-to-Speech | Edge TTS |
| Audio Processing | PyDub |
| Music Separation | Demucs |

---

# Setup

Create virtual environment

```
py -3.10 -m venv venv
source venv/Scripts/activate
```

Install dependencies

```
pip install -r requirements.txt
```

Run pipeline

```
python -m scripts.run_pipeline
```

---

# Documentation

Detailed technical documentation is available in:

```
docs/dev-log.md
docs/pipeline-design.md
```

The development log explains the engineering decisions, architecture evolution, and bugs fixed during the project.

---

# Future Improvements

Planned improvements:

- gender-based voice selection
- speaker detection
- voice cloning
- lip synchronization
- emotion-aware speech
- context-aware translation