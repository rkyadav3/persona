"""All database + storage operations for the admin. Pages call these; they never touch Supabase directly."""
import mimetypes
import os
import re
import uuid
from datetime import datetime, timezone

from .db import sb, paged, BUCKET
from .extract import extract_text, is_text


def now():
    return datetime.now(timezone.utc).isoformat()


def _first(q):
    rows = q.limit(1).execute().data
    return rows[0] if rows else None


def _batches(items, n=100):
    for i in range(0, len(items), n):
        yield items[i:i + n]


# ---------------- folders ----------------
def all_folders():
    return paged("folders", "*")


def folder_paths():
    fs = all_folders()
    by = {f["id"]: f for f in fs}

    def path(f):
        parts, cur = [], f
        while cur:
            parts.append(cur["name"])
            cur = by.get(cur["parent_id"])
        return " / ".join(reversed(parts))

    return sorted([(f["id"], path(f)) for f in fs], key=lambda x: x[1].lower())


def children(parent_id):
    q = sb().table("folders").select("*").order("name")
    q = q.is_("parent_id", "null") if parent_id is None else q.eq("parent_id", parent_id)
    return q.execute().data


def breadcrumbs(folder_id):
    by = {f["id"]: f for f in all_folders()}
    trail, cur = [], by.get(folder_id)
    while cur:
        trail.insert(0, cur)
        cur = by.get(cur["parent_id"])
    return trail


def create_folder(parent_id, name):
    return sb().table("folders").insert({"parent_id": parent_id, "name": name.strip()}).execute().data[0]


def ensure_path(parent_id, parts):
    """Create nested folders for an uploaded folder/zip path, reusing existing ones."""
    cur = parent_id
    for name in [p for p in parts if p]:
        q = sb().table("folders").select("id").eq("name", name)
        q = q.is_("parent_id", "null") if cur is None else q.eq("parent_id", cur)
        hit = _first(q)
        cur = hit["id"] if hit else create_folder(cur, name)["id"]
    return cur


def rename_folder(folder_id, name):
    sb().table("folders").update({"name": name.strip()}).eq("id", folder_id).execute()


def delete_folder(folder_id):
    fs = all_folders()
    ids, frontier = [folder_id], [folder_id]
    while frontier:
        frontier = [f["id"] for f in fs if f["parent_id"] in frontier]
        ids += frontier
    files = paged("files", "id,storage_path", lambda q: q.in_("folder_id", ids))
    for b in _batches([f["storage_path"] for f in files]):
        sb().storage.from_(BUCKET).remove(b)
    for b in _batches([f"file:{f['id']}" for f in files]):
        sb().table("chunks").delete().in_("source_key", b).execute()
    sb().table("folders").delete().eq("id", folder_id).execute()   # cascades to subfolders and file rows


# ---------------- files ----------------
FILE_COLS = "id,folder_id,topic_id,name,mime,size,status,updated_at,created_at"


def list_files(folder_id):
    q = sb().table("files").select(FILE_COLS).order("name")
    q = q.is_("folder_id", "null") if folder_id is None else q.eq("folder_id", folder_id)
    return q.execute().data


def search_files(text):
    t = re.sub(r"[,()%*]", "", text).strip()
    if not t:
        return []
    return sb().table("files").select(FILE_COLS).or_(f"name.ilike.%{t}%,text_content.ilike.%{t}%").limit(100).execute().data


def get_file(file_id):
    return _first(sb().table("files").select("*").eq("id", file_id))


def _upload(path, data, mime):
    sb().storage.from_(BUCKET).upload(path, data, {"content-type": mime, "upsert": "true"})


def add_file(folder_id, topic_id, name, data, status="published", text=None):
    stored = uuid.uuid4().hex + os.path.splitext(name)[1].lower()
    mime = mimetypes.guess_type(name)[0] or "application/octet-stream"
    _upload(stored, data, mime)
    if text is None:
        text = extract_text(name, data)
    return sb().table("files").insert({
        "folder_id": folder_id, "topic_id": topic_id, "name": name, "storage_path": stored, "mime": mime,
        "size": len(data), "text_content": text, "status": status}).execute().data[0]


def save_file(file_id, name, topic_id, status, text=None):
    f = get_file(file_id)
    patch = {"name": name.strip() or f["name"], "topic_id": topic_id, "status": status, "updated_at": now()}
    if text is not None and is_text(patch["name"]):
        data = text.encode("utf-8")
        _upload(f["storage_path"], data, f["mime"] or "text/plain")
        patch.update(text_content=text, size=len(data))
    sb().table("files").update(patch).eq("id", file_id).execute()


def move_file(file_id, folder_id):
    sb().table("files").update({"folder_id": folder_id}).eq("id", file_id).execute()


def delete_file(file_id):
    f = get_file(file_id)
    if f:
        sb().storage.from_(BUCKET).remove([f["storage_path"]])
    sb().table("chunks").delete().eq("source_key", f"file:{file_id}").execute()
    sb().table("files").delete().eq("id", file_id).execute()


def signed_url(storage_path, seconds=3600):
    r = sb().storage.from_(BUCKET).create_signed_url(storage_path, seconds)
    return r.get("signedURL") or r.get("signedUrl")


# ---------------- topics ----------------
def topics():
    ts = sb().table("topics").select("*").order("name").execute().data
    fc, pc = {}, {}
    for r in paged("files", "topic_id", lambda q: q.not_.is_("topic_id", "null")):
        fc[r["topic_id"]] = fc.get(r["topic_id"], 0) + 1
    for r in paged("posts", "topic_id", lambda q: q.not_.is_("topic_id", "null")):
        pc[r["topic_id"]] = pc.get(r["topic_id"], 0) + 1
    for t in ts:
        t["files"], t["posts"] = fc.get(t["id"], 0), pc.get(t["id"], 0)
    return ts


def create_topic(name, description=""):
    return sb().table("topics").insert({"name": name.strip(), "description": description}).execute().data[0]


def update_topic(topic_id, name, description):
    sb().table("topics").update({"name": name.strip(), "description": description}).eq("id", topic_id).execute()


def delete_topic(topic_id):
    sb().table("topics").delete().eq("id", topic_id).execute()


# ---------------- posts ----------------
def posts():
    return sb().table("posts").select("id,title,status,topic_id,updated_at").order("updated_at", desc=True).execute().data


def get_post(post_id):
    return _first(sb().table("posts").select("*").eq("id", post_id))


def create_post(html="<p></p>", topic_id=None, template_id=None):
    return sb().table("posts").insert({"title": "Untitled", "html": html, "status": "draft",
                                       "topic_id": topic_id, "template_id": template_id}).execute().data[0]


def save_post(post_id, title, html, topic_id, status):
    sb().table("posts").update({"title": title.strip() or "Untitled", "html": html, "topic_id": topic_id,
                                "status": status, "updated_at": now()}).eq("id", post_id).execute()


def delete_post(post_id):
    sb().table("chunks").delete().eq("source_key", f"post:{post_id}").execute()
    sb().table("posts").delete().eq("id", post_id).execute()


# ---------------- templates ----------------
def templates():
    return sb().table("templates").select("*").order("name").execute().data


def save_template(template_id, name, html):
    if template_id:
        sb().table("templates").update({"name": name, "html": html}).eq("id", template_id).execute()
    else:
        sb().table("templates").insert({"name": name or "Untitled template", "html": html}).execute()


def delete_template(template_id):
    sb().table("templates").delete().eq("id", template_id).execute()


# ---------------- counts ----------------
def _count(q):
    return q.limit(1).execute().count or 0


def counts():
    return {
        "files": _count(sb().table("files").select("id", count="exact")),
        "bytes": sum(r["size"] for r in paged("files", "size")),
        "posts": _count(sb().table("posts").select("id", count="exact")),
        "drafts": _count(sb().table("posts").select("id", count="exact").eq("status", "draft")),
        "topics": _count(sb().table("topics").select("id", count="exact")),
        "chunks": _count(sb().table("chunks").select("id", count="exact")),
        "embedded": _count(sb().table("chunks").select("id", count="exact").not_.is_("embedding", "null")),
    }
