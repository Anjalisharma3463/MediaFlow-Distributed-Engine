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
Groq TTS (natural speech) / elevenLabs → PyDub (align) → FFmpeg (merge)

here i have decide to use elevenLabs because groq tts does not provide multiple language support but elevenlavs does and elevenLabs generate High-Quality Text → Speech  than groq tts.
eleven labs provides:
    1. high quality audio generation
    2. Voice Cloning of provided voice sample audio and input text
    3. same emotion and same timing of sample audio
    4. speaker detection - ElevenLabs separates them and generates voices accordingly.
    5. ElevenLabs provides 10,000+ prebuilt voices.
    6.Emotion Control


did not used elevenlabs because it did not work with scripts but on gui it did work . so i used edge-tts for tts service..


future modification:--
1. i need to add gender specific voice.
2. i need to add lip sync model
3. voice clonning exactly like similar to user voice in input video.
4. i need to clean the transcript generated from audio. like mixed languages and convert into one language like phonetic meanings etc....
5. i will add emotions .like if audio in input video is sad then translated audio will also be in sad emotion.::
    maybe we can map emotions like this:
    Sad → slower, lower pitch
    Happy → faster, higher pitch
    Angry → slightly faster, louder, sharper pitch

6. To make generated audio segments more real... like insta translate reels audio in pure hindi likie (adhhbudh word) but in real life nobody use that word like no body use proper hindi.
7. context awareness using RAG on transcripts
8. emotional modeling :- I can't believe this! and sometime like hello? hello !

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
pip install -r requirements.txt

<!-- To run this pipeline -->
python -m scripts.run_pipeline


pip freeze > requirements.txt





<!-- 
1. lets's find out by input audio or tell me in which service betwen like while stt or translation or by input audio so we have to save input audio also we were not doing that coz we don't need of that . 
then we will extract find out that speaker based voice on bsias of gender.
2.  skip emotions for now . or lets discuss how we can implement thisl.
3.  will take all those edge tts langues voice and map then to language and gender in a file script and based on translated_language input we will find out voice.
4. then we will sned this finallised voice+emotions (if we will do this now) + gender + duration from transcript ) to  edge tts to generate audio segments  by adjusting pitch and speed with text segments.
5. at the end will merge all audio segments in final audio using pydub , also will use duration to adjust audio speed and update final audio by adding backgound music from input (original )audio .  -->