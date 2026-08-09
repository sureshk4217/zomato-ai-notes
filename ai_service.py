import json
import os
import re
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

AUTO_TAG_PROMPT = """Instructions:
Read the note content and classify it into useful short tags and write a concise summary.

Context:
This is an internal engineering knowledge-base note.

Input:
The user message contains the note content.

Constraints:
Return only a JSON object.
No text may surround the JSON object.
The object must contain exactly two keys: "tags" and "summary".
"tags" must be a list of 1-3 short lowercase keyword strings.
"summary" must be one sentence of at most 20 words.

Output Format:
{"tags":["keyword1","keyword2"],"summary":"One concise sentence."}
"""

STOP_WORDS = {
    "the","and","for","with","this","that","from","into","have","has","are","was",
    "were","your","you","our","about","after","before","will","must","been","they",
    "then","than","their","there","here","note","notes","very","just","today"
}

def _mock_response(content: str) -> str:
    words = re.findall(r"[A-Za-z0-9]+", content.lower())
    significant = []
    for word in words:
        if word not in STOP_WORDS and len(word) > 2 and word not in significant:
            significant.append(word)
        if len(significant) == 3:
            break
    if not significant:
        significant = ["general"]
    first_sentence = re.split(r"[.!?]", content.strip())[0].strip()
    summary_words = first_sentence.split()[:20]
    summary = " ".join(summary_words)
    if summary and not summary.endswith("."):
        summary += "."
    return json.dumps({"tags": significant[:3], "summary": summary or "General note."})

def get_ai_response(user_message: str, system_prompt: str) -> str:
    if os.getenv("MOCK_AI", "1") == "1":
        return _mock_response(user_message)

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is required when MOCK_AI=0")

    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"),
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "temperature": 0,
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]
