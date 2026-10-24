"""Stage 2: turn text into meaning vectors with Google's gemini-embedding-001 (free tier)."""
import math
import time
import requests
from .config import secret

DIM = 768
MODEL = lambda: secret("EMBED_MODEL", "gemini-embedding-001")


def doc_text(c):
    """Prefix each chunk with its document title and section so the vector knows where it came from."""
    h = f" > {c['heading']}" if c.get("heading") else ""
    return f"{c['source_name']}{h}\n{c['content']}"


def _unit(v):
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / n for x in v]


def embed(texts, task="RETRIEVAL_DOCUMENT"):
    key = secret("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY is not set in secrets.")
    model = MODEL()
    body = {"requests": [{"model": f"models/{model}", "content": {"parts": [{"text": t}]},
                          "taskType": task, "outputDimensionality": DIM} for t in texts]}
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:batchEmbedContents"
    last = ""
    for attempt in range(6):
        r = requests.post(url, headers={"x-goog-api-key": key, "Content-Type": "application/json"}, json=body, timeout=90)
        if r.status_code == 429 or r.status_code >= 500:     # rate limit or hiccup: back off and retry
            last = f"{r.status_code}: {r.text[:200]}"
            time.sleep(min(60, 4 * 2 ** attempt))
            continue
        if not r.ok:
            raise RuntimeError(f"Embedding failed ({r.status_code}): {r.text[:300]}")
        return [_unit(e["values"]) for e in r.json()["embeddings"]]   # 768-d vectors are not pre-normalised by the API
    raise RuntimeError(f"Embedding still failing after retries ({last}). Free tier limit reached? Try again in a minute.")
