"""Run the same hybrid search the website uses (for the Test retrieval box)."""
import re
from .db import sb
from .embed import embed
from .config import secret

STOP = set("a an and are as at be by for from has have in is it its of on or that the this to was were will with i my me you your do does what how why who which when".split())


def keyword_query(q):
    ws = [w for w in re.findall(r"[a-z0-9]+", q.lower()) if len(w) > 1 and w not in STOP]
    return " | ".join(dict.fromkeys(ws))


def search(q, k=6):
    vec = embed([q], "RETRIEVAL_QUERY")[0]
    return sb().rpc("hybrid_search", {
        "query_embedding": vec, "keyword_query": keyword_query(q), "match_count": k,
        "min_similarity": float(secret("MIN_SIMILARITY", 0.6)), "min_keyword_rank": float(secret("MIN_KEYWORD_RANK", 0.2)),
    }).execute().data
