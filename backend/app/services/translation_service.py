import json
from app.services.groq_client import client


#  translation service using Groq Translation API

def translate_text(input_transcript_path: str, target_language: str, output_transcript_path: str):
    """
    Translate transcript segments into target language.
    """
    # get the clean transcript
    # clean_segments  = clean_transcript(input_transcript_path)
    # load transcript file directly (since cleaning is disabled for now)
    with open(input_transcript_path, "r", encoding="utf-8") as f:
        clean_segments = json.load(f)
    # send this text and duration to model to get the translation in batch size for each call to model
    BATCH_SIZE = 10
    # this translated_segments will hold the final output of translated segments with start, end, original text and translated text
    translated_segments = []

    # process the transcript in batches and make one batch_payload of segments with duration
    for i in range(0, len(clean_segments), BATCH_SIZE):
        batch = clean_segments[i:i+BATCH_SIZE]    

        batch_payload = []
        for idx, segment in enumerate(batch):
            duration = segment["end"] - segment["start"]
            
            batch_payload.append({
                "id": idx,
                "text": segment["text"],
                "duration": duration
            })

        payload_json = json.dumps(batch_payload, ensure_ascii=False, indent=2)

        prompt = f"""
        You are a translation engine for creating natural, spoken-style translations.

        Translate each sentence into {target_language} in a way that a native speaker would **actually say it in everyday conversation**.

        Rules:
        - Keep the meaning accurate.
        - Use **natural, colloquial language**, like someone would speak in real life.
        - Keep translations concise to fit the original segment duration.
        - Avoid overly formal or literary words.
        - Do NOT explain anything.
        - Do NOT write code.
        - Do NOT include markdown.
        - Return ONLY valid JSON.

        Input:
        {payload_json}

        Output format (JSON only):
        [
        {{"id": 0, "translated": "..."}}
        ]
        """
        # send this batch_payload to model to get the translation
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0

        ) 
         
        result_text = response.choices[0].message.content.strip()

        # remove markdown if present
        result_text = result_text.replace("```json", "").replace("```", "").strip()
        print("\nMODEL RESPONSE:")
        print(result_text)
        try:
            batch_translations = json.loads(result_text)
        except json.JSONDecodeError:
            print("⚠️ JSON parsing failed")
            print(result_text)
            continue

        for item in batch_translations:

            seg = batch[item["id"]]

            translated_segments.append({
                "start": seg["start"],
                "end": seg["end"],
                "original": seg["text"],
                "translated": item["translated"]
            })
    # save the output in output format 
    with open(output_transcript_path, "w", encoding="utf-8") as f:
        json.dump(translated_segments, f, indent=4, ensure_ascii=False)

    print(f"✅ Translation saved to {output_transcript_path}")






# def clean_transcript(input_transcript_path: str):
#     """
#     Clean transcript segments while preserving timestamps.
#     Fix phonetic English technical terms and remove noise.
#     """
#     BATCH_SIZE = 15

#     with open(input_transcript_path, "r", encoding="utf-8") as f:
#         segments = json.load(f)

#         clean_segments  = []

#     for i in range(0, len(segments), BATCH_SIZE):

#         batch = segments[i:i+BATCH_SIZE]

#         payload = []

#         for idx, seg in enumerate(batch):
#             payload.append({
#                 "id": idx,
#                 "text": seg["text"]
#             })

#         payload_json = json.dumps(payload, ensure_ascii=False, indent=2)

        # prompt = f"""
        # You are cleaning speech-to-text transcripts.

        # Fix spelling errors and phonetic English words written in Hindi or other scripts.

        # Rules:
        # - Do NOT translate
        # - Do NOT explain
        # - Do NOT write code
        # - Return ONLY valid JSON

        # Input:
        # {payload_json}

        # Output JSON format:
        # [
        # {{"id": 0, "cleaned": "..."}}
        # ]
        # """

#         response = client.chat.completions.create(
#             model="llama-3.1-8b-instant",
#             messages=[
#                 {"role": "user", "content": prompt}
#             ],
#             temperature=0
#         )

#         result_text = response.choices[0].message.content.strip()

#         try:
#             cleaned_batch = json.loads(result_text)
#         except:
#             print("⚠️ Invalid JSON from model")
#             print(result_text)
#             continue

#         for item in cleaned_batch:

#             seg = batch[item["id"]]

#             clean_segments .append({
#                 "start": seg["start"],
#                 "end": seg["end"],
#                 "text": item["cleaned"]
#             })

#     return clean_segments 
