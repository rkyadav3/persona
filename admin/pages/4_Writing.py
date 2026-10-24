import streamlit as st

st.set_page_config(page_title="Writing", layout="wide")
from lib.auth import require_login
require_login()
from lib import store, indexer
from lib.ui import topic_select

try:
    from streamlit_quill import st_quill
    HAVE_QUILL = True
except Exception:
    HAVE_QUILL = False

TOOLBAR = [
    [{"header": [1, 2, 3, False]}, {"font": []}, {"size": ["small", False, "large", "huge"]}],
    ["bold", "italic", "underline", "strike"], [{"color": []}, {"background": []}],
    [{"list": "ordered"}, {"list": "bullet"}, {"align": []}],
    ["blockquote", "code-block", "link", "image"], ["clean"],
]
ss = st.session_state
ss.setdefault("post_id", None)


def list_view():
    h, b = st.columns([4, 1])
    h.title("Writing")
    tpls = store.templates()
    with st.container(border=True):
        c1, c2, c3 = st.columns([2, 2, 1])
        tid = c1.selectbox("Start from template", [t["id"] for t in tpls], format_func=lambda i: next(t["name"] for t in tpls if t["id"] == i))
        with c2:
            topic = topic_select("Topic", "np_topic")
        c3.write("")
        if c3.button("New post", type="primary"):
            html = next(t["html"] for t in tpls if t["id"] == tid)
            ss.post_id = store.create_post(html, topic, tid)["id"]
            st.rerun()
    posts = store.posts()
    topics = {t["id"]: t["name"] for t in store.topics()}
    if not posts:
        st.info("No posts yet. Create your first one above.")
    for p in posts:
        c1, c2, c3, c4 = st.columns([5, 2, 1, 2])
        if c1.button(p["title"], key=f"p{p['id']}"):
            ss.post_id = p["id"]
            st.rerun()
        c2.write(topics.get(p["topic_id"], ""))
        c3.write(p["status"])
        c4.caption(p["updated_at"][:16].replace("T", " "))


def editor_view(pid):
    post = store.get_post(pid)
    if not post:
        ss.post_id = None
        st.rerun()
    key = f"html_{pid}"
    ss.setdefault(key, post["html"])
    top, back = st.columns([6, 1])
    top.title("Edit post")
    if back.button("Back to list"):
        ss.post_id = None
        st.rerun()
    title = st.text_input("Title", post["title"], key=f"title_{pid}")
    c1, c2 = st.columns(2)
    with c1:
        topic = topic_select("Topic", f"topic_{pid}", post["topic_id"])
    with c2:
        mode = st.radio("Editor", ["Visual", "HTML source"] if HAVE_QUILL else ["HTML source"], horizontal=True, key=f"mode_{pid}")
    if mode == "Visual":
        out = st_quill(value=ss[key], html=True, toolbar=TOOLBAR, placeholder="Write here...", key=f"quill_{pid}")
        if out is not None:
            ss[key] = out
    else:
        ss[key] = st.text_area("HTML", ss[key], height=420, key=f"src_{pid}")
    if not HAVE_QUILL:
        st.caption("Visual editor package not installed; add streamlit-quill to requirements.txt.")
    s1, s2, s3 = st.columns([1, 1, 4])
    for label, status, kind in (("Save as draft", "draft", "secondary"), ("Publish", "published", "primary")):
        col = s1 if status == "draft" else s2
        if col.button(label, type=kind, key=f"{status}_{pid}"):
            store.save_post(pid, title, ss[key], topic, status)
            waiting, err = indexer.refresh("post", pid)
            st.success("Saved as draft." if status == "draft" else "Published.")
            if err:
                st.warning(f"Saved, but indexing needs attention: {err}")
            elif waiting > 0:
                st.info(f"{waiting} chunks are waiting to be embedded. Press Sync in Knowledge index.")
    with s3.popover("Delete post"):
        if st.button("Yes, delete", key=f"del_{pid}"):
            store.delete_post(pid)
            ss.post_id = None
            st.rerun()


editor_view(ss.post_id) if ss.post_id else list_view()
