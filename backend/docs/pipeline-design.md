# MediaFlow Pipeline Design


## Initial Pipeline Plan

The pipeline was designed on paper before implementation.

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


## Tool Selection

| Task                    | Best FREE Tool | Why Best                                      | Lightweight   | Quality      |
| ----------------------- | -------------- | --------------------------------------------- | ------------- | ------------ |
| Extract Audio           | FFmpeg-python  | Industry standard for video/audio processing | Tiny          | Perfect      |
| Transcribe + Translate  | Whisper-small  | Direct translation with timestamps           | Medium        | Very Good    |
| Text to Speech          | Coqui TTS      | Neural voices, offline generation            | Medium        | Excellent    |
| Audio Alignment         | PyDub          | Easy silence padding and timing alignment    | Tiny          | Perfect sync |
| Merge Video             | FFmpeg-python  | Efficient video/audio muxing                 | Tiny          | Perfect      |


## Pipeline Variants

### Groq Pipeline (Fastest)

Video
↓
FFmpeg (extract audio)
↓
Groq Whisper (transcribe)
↓
Groq Translation
↓
Edge TTS
↓
PyDub (alignment)
↓
FFmpeg (merge video)

Used when speed and translation accuracy are required.


### Local Pipeline (Zero Cost)

Video
↓
FFmpeg (extract)
↓
Whisper-small (transcribe + translate)
↓
Coqui TTS
↓
PyDub (alignment)
↓
FFmpeg (merge)

Used when running everything locally without API usage.


## TTS Service Decision

Initially ElevenLabs was considered because it provides:

- high quality speech synthesis
- voice cloning
- speaker detection
- emotion control
- large voice library

However, the ElevenLabs API integration did not work reliably through scripts during testing. Because of this limitation, Edge TTS was selected as the primary TTS service.


## Making Generated Speech Sound Natural

To make the generated speech sound natural:

- use Whisper timestamps
- split translation into timestamp segments
- generate TTS per segment
- adjust speech speed slightly if needed
- insert silence padding
- merge segments sequentially
- finally merge audio with the video using FFmpeg


## Future Emotion Modeling
Emotion could be mapped to speech parameters:

Sad → slower speech, lower pitch  
Happy → faster speech, higher pitch  
Angry → louder voice, sharper pitch

