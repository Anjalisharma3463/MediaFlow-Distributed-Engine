# MediaFlow-Distributed-Engine  

The Pipeline Flow (On Paper First)
Write this clearly in README.md:
1. Validate input file
2. Extract audio from video
3. Normalize audio format
4. Transcribe audio with timestamps
5. Save transcript
6. Translate transcript
7. Save translated transcript
8. Generate new audio from translated text
9. Merge new audio with original video
10. Save final output
This must exist before implementation.


⚡ USER WANTS SPEED → Groq Pipeline
💰 UNLIMITED VIDEOS → Local Pipeline  
🤖 BEST QUALITY → Groq (large-v3)
🆓 ZERO COST → Local Pipeline

<!-- Mixed local+groq -->
<!-- Video → FFmpeg → [Groq Free Tier OR Local Fallback] → PyDub → FFmpeg -->
STT: Local primary → Groq optional high-accuracy
Translation: Groq primary → Local fallback
TTS: Local primary only

<!-- LOCAL -->

Video → FFmpeg (extract) → Whisper-small (transcribe+translate) → 
Coqui TTS (natural speech w/ timestamps) → FFmpeg (merge w/ alignment)


| Task                    | Best FREE Tool | Why Best                                      | Lightweight   | Quality      |
| ----------------------- | -------------- | --------------------------------------------- | ------------- | ------------ |
| 1. Extract Audio        | FFmpeg-python  | ✅ Final choice                                | Tiny          | Perfect      |
| 2. Transcribe+Translate | Whisper-small  | Direct English→Hindi translation + timestamps | Medium (~2GB) | Very Good    |
| 3. TTS (Natural)        | Coqui TTS      | Neural voices, offline, human-like            | Medium        | Excellent    |
| 4. Audio Alignment      | PyDub          | Perfect silence padding + timing              | Tiny          | Perfect sync |
| 5. Merge Video          | FFmpeg-python  | ✅ Final choice                                | Tiny          | Perfect      |



FFmpeg: ~100MB (negligible)
Whisper-small: ~2GB peak during transcription
Coqui TTS: ~1GB during speech generation
PyDub: ~50MB
TOTAL: ~3-4GB max at any time

<!-- OR -->

 <!-- Groq API -->

Video → FFmpeg (extract) → Groq Whisper (transcribe+translate) →
Groq TTS (natural speech) → PyDub (align) → FFmpeg (merge)




💡 How You Make It Sound Human

Very important:

Use Whisper timestamps

Split translation by timestamp segments

Generate TTS per segment

Adjust speed slightly if needed

Insert silence padding

Merge sequentially

Then final FFmpeg merge






py -3.10 -m venv venv
source venv/Scripts/activate 