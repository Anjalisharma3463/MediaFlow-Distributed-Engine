import json
import re
from pathlib import Path
from app.services.groq_client import client


# HOW THIS WORKS — READ THIS FIRST  


# The problem: In any language, speakers say technical/brand words
# phonetically in their native script. Whisper transcribes what it hears.
# So "React" in Hindi becomes "रिएक्ट", in Japanese "リアクト", in Arabic "ريآكت"
# The translation LLM then guesses what that phonetic word means — and guesses wrong.
# "वाइब" → "Vue" is one example. This happens in every language.
#
# The wrong fix: hardcoded dictionaries per language (unmaintainable, always incomplete) 
#
# The right fix: Three layers 

# LAYER 1 — DETECTION (LLM-based, universal)
#   Ask a fast LLM to read the transcript and identify all words that are
#   phonetic transliterations of technical/brand/foreign terms.
#   Output: a term map specific to THIS video's content.
#   Works for any source language automatically — no configuration needed.
#
# LAYER 2 — PROTECTION (dynamic, per-video)
#   Use the detected term map to wrap those words in [KEEP]...[/KEEP]
#   before sending to translation. The translation LLM is instructed
#   to never touch content inside those markers.
#
# LAYER 3 — RESTORATION (simple regex strip)
#   After translation, strip the [KEEP][/KEEP] markers, leaving the
#   preserved English terms correctly placed in the translated sentence.
#
# This works for Hindi→English, Spanish→Japanese, Arabic→French,
# any language pair, zero configuration changes per language.


# LAYER 1 — UNIVERSAL TERM DETECTION

def detect_technical_terms(segments: list, source_language: str) -> dict:
    """
    Analyze the transcript to detect phonetically transliterated
    technical/brand/foreign words that must NOT be translated.

    Uses an LLM because:
    - It understands phonetics across scripts (regex cannot)
    - It knows what technical/brand terms look like across domains
    - It works for any source language with zero code changes
    - A dictionary would need thousands of entries per language and
      still miss new terms, product names, and slang

    Returns: { "native_script_word": "EnglishEquivalent" }

    Examples by language:
        Hindi:    { "वाइब": "vibe", "कोडिंग": "coding", "रिएक्ट": "React" }
        Japanese: { "リアクト": "React", "フロントエンド": "frontend" }
        Arabic:   { "كلاود": "cloud", "ريآكت": "React" }
        Russian:  { "фронтенд": "frontend", "бэкенд": "backend" }
        Korean:   { "도커": "Docker", "깃허브": "GitHub" }
    """

    # sample first 30 segments — enough to find all recurring terms
    # without blowing the token budget on a long video
    sample_segments = segments[:30]
    all_text = " ".join([s["text"] for s in sample_segments])

    system_prompt = """You are a linguistics expert who detects English technical terms
written phonetically in other languages.

Speakers in tech videos borrow English words and pronounce them in their native language.
Whisper transcribes those sounds into native script.
Your job: find those borrowed words and map them back to their English originals.

What to look for:
- Programming languages: Python, React, JavaScript, Node, Vue, etc.
- Tech concepts: API, backend, frontend, cloud, server, database, etc.
- Brand names: GitHub, Docker, AWS, Google, ChatGPT, etc.
- Tech slang: vibe coding, debugging, deploying, etc.
- Any other English word a tech content creator would say

Return a JSON object. If nothing found, return {}.
NEVER explain. NEVER add markdown. Return ONLY valid JSON."""

    user_prompt = f"""Source language: {source_language}

Transcript text:
{all_text}

Find all phonetically transliterated English technical/brand terms.
Return format (JSON object only):
{{
  "native_script_word": "EnglishEquivalent"
}}"""

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0
        )

        result_text = response.choices[0].message.content.strip()
        result_text = result_text.replace("```json", "").replace("```", "").strip()

        term_map = json.loads(result_text)

        if term_map:
            print(f"Detected {len(term_map)} technical terms to preserve:")
            for native, english in term_map.items():
                print(f"'{native}' → '{english}'")
        else:
            print("No transliterated terms detected in this video")

        return term_map

    except (json.JSONDecodeError, Exception) as e:
        print(f"Term detection failed: {e} — continuing without protection")
        return {}


# LAYER 2 — DYNAMIC TERM PROTECTION

def protect_terms(text: str, term_map: dict) -> str:
    """
    Wrap detected technical terms with [KEEP]...[/KEEP] markers
    so the translation LLM skips them entirely.

    Sorts by length descending to prevent partial replacements.
    Example: "जावास्क्रिप्ट" is replaced before "स्क्रिप्ट"
    so you don't get a double-replacement.

    "वाइब कोडिंग से" → "[KEEP]vibe[/KEEP] [KEEP]coding[/KEEP] से"
    """
    if not term_map:
        return text

    for native_word in sorted(term_map.keys(), key=len, reverse=True):
        english_word = term_map[native_word]
        if native_word in text:
            text = text.replace(native_word, f"[KEEP]{english_word}[/KEEP]")

    return text


def strip_keep_tags(text: str) -> str:
    """
    Remove [KEEP]...[/KEEP] markers after translation, keeping the content.

    "[KEEP]vibe[/KEEP] [KEEP]coding[/KEEP]" → "vibe coding"
    """
    return re.sub(r'\[KEEP\](.*?)\[/KEEP\]', r'\1', text)


# TRANSCRIPT CLEANING 

def clean_transcript_segments(segments: list, source_language: str) -> list:
    """
    Clean raw Whisper output before translation:
    - Fix STT mishearings and obvious errors
    - Add basic punctuation to run-on sentences
    - Remove filler words (um, uh, hmm and language equivalents)

    Deliberately NOT translating here.
    Mixing cleaning + translation in one prompt degrades both tasks.
    Uses 8b model — cleaning does not need 70b.
    """
    BATCH_SIZE = 15
    cleaned_segments = []

    for i in range(0, len(segments), BATCH_SIZE):
        batch = segments[i:i + BATCH_SIZE]
        payload = [{"id": idx, "text": seg["text"]} for idx, seg in enumerate(batch)]
        payload_json = json.dumps(payload, ensure_ascii=False, indent=2)

        system_prompt = f"""You clean speech-to-text transcript output in {source_language}.

Fix only:
1. Obvious STT errors and mishearings
2. Run-on text without punctuation — add minimal punctuation
3. Filler words: um, uh, hmm and their equivalents in {source_language}

Never translate. Never change meaning. Never explain.
Return ONLY valid JSON array."""

        user_prompt = f"""Clean these segments. Language: {source_language}

Input:
{payload_json}

Output (JSON array only):
[
  {{"id": 0, "cleaned": "..."}}
]"""

        try:
            response = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0
            )

            result_text = response.choices[0].message.content.strip()
            result_text = result_text.replace("```json", "").replace("```", "").strip()
            cleaned_batch = json.loads(result_text)

            for item in cleaned_batch:
                seg = batch[item["id"]]
                cleaned_segments.append({
                    "start": seg["start"],
                    "end": seg["end"],
                    "text": item["cleaned"]
                })

        except Exception as e:
            print(f"⚠️ Cleaning batch {i} failed: {e} — using original text")
            for seg in batch:
                cleaned_segments.append(seg)

    return cleaned_segments


# LANGUAGE STYLE GUIDES
# What "conversational" means varies significantly by language.
# These steer the model toward spoken register, not written/formal register.

LANGUAGE_STYLE_GUIDE = {
    "hindi": "Use Hinglish style — natural Hindi mixed with common English tech terms. Forcing pure Hindi for technical words sounds unnatural and nobody says it that way.",
    "english": "Natural conversational American English. Short sentences. Never formal or academic.",
    "spanish": "Latin American conversational Spanish. Avoid Castilian formal constructions.",
    "french": "Modern conversational French. Avoid overly formal register.",
    "german": "Natural spoken German. Avoid complex compound sentences where simpler works.",
    "japanese": "Casual spoken Japanese. Use casual form unless speaker sounds formal.",
    "portuguese": "Brazilian Portuguese conversational style.",
    "arabic": "Modern Standard Arabic with conversational phrasing, not formal literary Arabic.",
    "korean": "Casual spoken Korean. Match formality level of original speaker.",
    "russian": "Everyday spoken Russian. Avoid bureaucratic or overly formal constructions.",
    "italian": "Natural conversational Italian. Match the speaker's energy and pace.",
    "chinese": "Simplified Chinese with natural conversational flow. Avoid stiff written style.",
    "turkish": "Everyday conversational Turkish.",
    "dutch": "Natural conversational Dutch. Avoid overly formal register.",
    "polish": "Conversational Polish. Match the speaker's tone.",
    "swedish": "Natural conversational Swedish.",
    "indonesian": "Informal Indonesian (bahasa gaul where appropriate). Match speaker's tone.",
}


# MAIN ENTRY POINT

def translate_text(
    input_transcript_path: str,
    target_language: str,
    output_transcript_path: str,
    source_language: str = "auto"
):
    """
    Full translation pipeline:
      1. Load transcript
      2. Detect technical terms for this specific video (universal, any language)
      3. Clean STT output (separate pass, better quality)
      4. Translate with term protection + context window
      5. Strip protection markers from output
      6. Save translated transcript

    Args:
        input_transcript_path:  path to raw Whisper transcript JSON
        target_language:        language to translate into (e.g. "english", "hindi")
        output_transcript_path: where to save translated transcript JSON
        source_language:        source language, pass Whisper's detected language if available
    """

    input_file = Path(input_transcript_path)

    if not input_file.exists():
        raise FileNotFoundError(f"Transcript not found: {input_transcript_path}")
    if input_file.stat().st_size == 0:
        raise ValueError("Transcript file is empty")

    with open(input_file, "r", encoding="utf-8") as f:
        raw_segments = json.load(f)

    print(f"\n{'='*60}")
    print(f"TRANSLATION PIPELINE")
    print(f"{'='*60}")
    print(f"Segments : {len(raw_segments)}")
    print(f"Source   : {source_language}")
    print(f"Target   : {target_language}")

    # ── STAGE 1: Detect video-specific technical terms ──────────────────
    print(f"\n[1/3] Detecting technical terms...")
    term_map = detect_technical_terms(raw_segments, source_language)

    # ── STAGE 2: Clean raw STT noise ────────────────────────────────────
    print(f"\n[2/3] Cleaning transcript...")
    cleaned_segments = clean_transcript_segments(raw_segments, source_language)
    print(f"Done — {len(cleaned_segments)} segments cleaned")

    # ── STAGE 3: Translate with protection + context window ─────────────
    print(f"\n[3/3] Translating...")

    BATCH_SIZE = 10
    CONTEXT_WINDOW = 3  # previous translated segments shown to each new batch
                        # gives the model memory of what was already said
                        # prevents terminology drift between batches

    translated_segments = []
    style_guide = LANGUAGE_STYLE_GUIDE.get(
        target_language.lower(),
        "Natural conversational language that sounds like real spoken speech, not written text."
    )
    total_batches = (len(cleaned_segments) + BATCH_SIZE - 1) // BATCH_SIZE

    system_prompt = f"""You are a professional dubbing translator for video content.

Source language: {source_language}
Target language: {target_language}
Style requirement: {style_guide}

Rules:
1. Translate for SPOKEN delivery — short sentences, natural rhythm
2. Match the speaker's energy: casual stays casual, excited stays excited
3. [KEEP]...[/KEEP] markers are UNTOUCHABLE — preserve them character-for-character
4. Keep translations CONCISE — voice must fit original timing
5. Consistent terminology — use the same translation for the same term throughout
6. No explanations, no notes, no markdown
7. Return ONLY valid JSON"""

    for i in range(0, len(cleaned_segments), BATCH_SIZE):

        batch = cleaned_segments[i:i + BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1
        print(f"      Batch {batch_num}/{total_batches}...", end=" ")

        # context: show last N translated segments so model maintains consistency
        context_str = ""
        if translated_segments:
            recent = translated_segments[-CONTEXT_WINDOW:]
            context_lines = [
                f"  [{s['original'][:45]}] → [{s['translated']}]"
                for s in recent
            ]
            context_str = (
                "Maintain consistency with these recent translations:\n"
                + "\n".join(context_lines)
                + "\n\n"
            )

        # apply term protection before sending to translation LLM
        batch_payload = []
        for idx, segment in enumerate(batch):
            protected_text = protect_terms(segment["text"], term_map)
            duration = round(segment["end"] - segment["start"], 2)
            batch_payload.append({
                "id": idx,
                "text": protected_text,
                "duration_seconds": duration
            })

        payload_json = json.dumps(batch_payload, ensure_ascii=False, indent=2)

        user_prompt = (
            f"{context_str}"
            f"Translate to {target_language}. "
            f"Preserve all [KEEP]...[/KEEP] markers exactly as they appear.\n\n"
            f"Input:\n{payload_json}\n\n"
            f"Output (JSON array only):\n"
            f"[\n  {{\"id\": 0, \"translated\": \"...\"}}\n]"
        )

        try:
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0
            )

            result_text = response.choices[0].message.content.strip()
            result_text = result_text.replace("```json", "").replace("```", "").strip()
            batch_translations = json.loads(result_text)

            for item in batch_translations:
                seg = batch[item["id"]]
                clean_translation = strip_keep_tags(item["translated"])
                translated_segments.append({
                    "start": seg["start"],
                    "end": seg["end"],
                    "original": seg["text"],
                    "translated": clean_translation
                })

            print(f"{len(batch_translations)} segments")

        except json.JSONDecodeError as e:
            print(f"JSON parse failed: {e} — using fallback")
            for seg in batch:
                translated_segments.append({
                    "start": seg["start"],
                    "end": seg["end"],
                    "original": seg["text"],
                    "translated": seg["text"]  # untranslated fallback, pipeline continues
                })

        except Exception as e:
            print(f"Failed: {e} — using fallback")
            for seg in batch:
                translated_segments.append({
                    "start": seg["start"],
                    "end": seg["end"],
                    "original": seg["text"],
                    "translated": seg["text"]
                })

    # ── Save translated segments
    output_file = Path(output_transcript_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(translated_segments, f, indent=4, ensure_ascii=False)

    print(f"\n{'='*60}")
    print(f"TRANSLATION COMPLETE")
    print(f"Segments  : {len(translated_segments)}")
    print(f"Saved to  : {output_file}")
    print(f"{'='*60}\n")

    return translated_segments