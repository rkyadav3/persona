"""Keeps the knowledge index (chunks + vectors) in step with your content. Drafts are never indexed."""
import hashlib
import time

from .chunker import chunk, html_to_text
from .config import secret
from .db import sb, paged
from .embed import embed, doc_text, MODEL

CHUNK_VERSION = "v1"   # bump if you change chunking rules to force a rebuild
BATCH = 20


def _hash(name, text):
    return hashlib.sha1("\0".join([name, text, CHUNK_VERSION, str(MODEL())]).encode()).hexdigest()


def _batches(items, n=100):
    for i in range(0, len(items), n):
        yield items[i:i + n]


def delete_source(key):
    sb().table("chunks").delete().eq("source_key", key).execute()


def _insert(kind, sid, name, text):
    key, h = f"{kind}:{sid}", _hash(name, text)
    rows = [{"source_key": key, "source_type": kind, "source_id": sid, "source_name": name, "source_hash": h,
             "ord": i, "heading": c["heading"], "content": c["text"]} for i, c in enumerate(chunk(text))]
    for b in _batches(rows):
        sb().table("chunks").insert(b).execute()
    return len(rows)


def index_source(kind, sid):
    """Re-chunk one file/post if it changed. Removes it from the index if it is a draft or empty."""
    key = f"{kind}:{sid}"
    if kind == "file":
        r = (sb().table("files").select("name,text_content,status").eq("id", sid).limit(1).execute().data or [None])[0]
        src = (r["name"], r["text_content"], r["status"]) if r else None
    else:
        r = (sb().table("posts").select("title,html,status").eq("id", sid).limit(1).execute().data or [None])[0]
        src = (r["title"], html_to_text(r["html"]), r["status"]) if r else None
    if not src or src[2] != "published" or not src[1].strip():
        delete_source(key)
        return 0
    cur = sb().table("chunks").select("source_hash").eq("source_key", key).limit(1).execute().data
    if cur and cur[0]["source_hash"] == _hash(src[0], src[1]):
        return 0
    delete_source(key)
    return _insert(kind, sid, src[0], src[1])


def pending_count():
    return sb().table("chunks").select("id", count="exact").is_("embedding", "null").limit(1).execute().count or 0


def embed_pending(max_seconds=60, progress=None):
    """Embed chunks that have no vector yet, staying under the free-tier tokens-per-minute limit.
    Returns (embedded_now, still_waiting). Safe to call repeatedly; it resumes where it stopped."""
    t0, done, tpm = time.time(), 0, float(secret("EMBED_TPM", 24000))
    while time.time() - t0 < max_seconds:
        rows = (sb().table("chunks").select("id,source_name,heading,content").is_("embedding", "null")
                .order("id").limit(BATCH).execute().data)
        if not rows:
            break
        t1 = time.time()
        vecs = embed([doc_text(r) for r in rows])
        sb().rpc("set_embeddings", {"items": [{"id": r["id"], "embedding": v} for r, v in zip(rows, vecs)]}).execute()
        done += len(rows)
        if progress:
            progress(done)
        wait = sum(len(doc_text(r)) for r in rows) / 3.5 / (tpm / 60) - (time.time() - t1)
        if wait > 0:
            time.sleep(wait)
    return done, pending_count()


def refresh(kind, sid, seconds=45):
    """Used after an upload or save. Returns (chunks_still_waiting, error_text_or_None)."""
    try:
        index_source(kind, sid)
        return embed_pending(seconds)[1], None
    except Exception as e:  # keep the save successful even if embedding is unavailable
        try:
            return pending_count(), str(e)
        except Exception:
            return -1, str(e)


def sync_all(max_seconds=240, progress=None):
    """Full diff: add new/changed sources, drop deleted/unpublished ones, then embed what's pending."""
    wanted = {}
    for f in paged("files", "id,name,text_content", lambda q: q.eq("status", "published")):
        if f["text_content"].strip():
            wanted[f"file:{f['id']}"] = ("file", f["id"], f["name"], f["text_content"])
    for p in paged("posts", "id,title,html", lambda q: q.eq("status", "published")):
        t = html_to_text(p["html"])
        if t.strip():
            wanted[f"post:{p['id']}"] = ("post", p["id"], p["title"], t)
    have = {r["source_key"]: r["source_hash"] for r in sb().rpc("chunk_sources").execute().data}
    stale = [k for k, h in have.items() if k not in wanted or _hash(wanted[k][2], wanted[k][3]) != h]
    for k in stale:
        delete_source(k)
    added = 0
    for k, (kind, sid, name, text) in wanted.items():
        if have.get(k) != _hash(name, text):
            _insert(kind, sid, name, text)
            added += 1
    done, remaining = embed_pending(max_seconds, progress)
    return {"removed": len(stale), "added": added, "embedded": done, "remaining": remaining}


def rebuild_all():
    sb().table("chunks").delete().gt("id", 0).execute()
