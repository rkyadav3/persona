import streamlit as st

st.set_page_config(page_title="Writing", layout="wide")
from lib.auth import require_login
require_login()
from lib import store, indexer
from lib.theme import apply_theme, pill, table_header
from lib.ui import topic_select

try:
    from streamlit_quill import st_quill
    HAVE_QUILL = True
except Exception:
    HAVE_QUILL = False

apply_theme()

TOOLBAR = [
    [{"header": [1, 2, 3, False]}, {"font": []}, {"size": ["small", False, "large", "huge"]}],
    ["bold", "italic", "underline", "strike"], [{"color": []}, {"background": []}],
    [{"list": "ordered"}, {"list": "bullet"}, {"align": []}],
    ["blockquote", "code-block", "link", "image"], ["clean"],
]
ss = st.session_state
ss.setdefault("post_id", None)


def list_view():
    h, b = st.columns([5, 1])
    h.title("Writing")
    tpls = store.templates()
    with st.container(border=True):
        c1, c2, c3 = st.columns([2, 2, 1])
        tid = c1.selectbox("Start from template", [t["id"] for t in tpls],
                           format_func=lambda i: next(t["name"] for t in tpls if t["id"] == i)) if tpls else None
        with c2:
            topic = topic_select("Topic", "np_topic")
        c3.write("")
        c3.write("")
        if c3.button("New post", type="primary"):
            html = next((t["html"] for t in tpls if t["id"] == tid), "")
            ss.post_id = store.create_post(html, topic, tid)["id"]
            st.rerun()
    posts = store.posts()
    topics = {t["id"]: t["name"] for t in store.topics()}
    W = [5, 2, 1.6, 2, 1.2]
    table_header(["Title", "Topic", "Status", "Updated", ""], W)
    if not posts:
        st.info("No posts yet. Write your first one.")
    for p in posts:
        c1, c2, c3, c4, c5 = st.columns(W)
        if c1.button(p["title"], key=f"lk_p{p['id']}", use_container_width=True):
            ss.post_id = p["id"]
            st.rerun()
        c2.write(topics.get(p["topic_id"], ""))
        c3.markdown(pill(p["status"]), unsafe_allow_html=True)
        c4.caption(p["updated_at"][:16].replace("T", " "))
        with c5.popover("Delete"):
            st.warning("Delete this post?")
            if st.button("Yes, delete", key=f"ld{p['id']}"):
                store.delete_post(p["id"])
                st.rerun()


def editor_view(pid):
    post = store.get_post(pid)
    if not post:
        ss.post_id = None
        st.rerun()
    key = f"html_{pid}"
    ss.setdefault(key, post["html"])

    # ---- top bar: title / topic / editor mode / Save as draft / Publish / state
    title = st.text_input("Title", post["title"], key=f"title_{pid}", placeholder="Title", label_visibility="collapsed")
    c_topic, c_mode, c_draft, c_pub, c_state, c_back = st.columns([3, 3, 1.2, 1, 1.2, 1.2])
    with c_topic:
        topic = topic_select("Topic", f"topic_{pid}", post["topic_id"])
    mode = c_mode.radio("Editor", ["Visual", "HTML source"] if HAVE_QUILL else ["HTML source"], horizontal=True, key=f"mode_{pid}")
    c_draft.write("")
    c_pub.write("")
    want_draft = c_draft.button("Save as draft", key=f"draft_{pid}")
    want_pub = c_pub.button("Publish", type="primary", key=f"publish_{pid}")
    c_state.write("")
    state = c_state.empty()
    state.markdown(f'<span class="muted">{"Published" if post["status"] == "published" else "Draft"}</span>', unsafe_allow_html=True)
    c_back.write("")
    if c_back.button("Back to list", key=f"back_{pid}"):
        ss.post_id = None
        st.rerun()

    # ---- editor
    if mode == "Visual":
        out = st_quill(value=ss[key], html=True, toolbar=TOOLBAR, placeholder="Write here...", key=f"quill_{pid}")
        if out is not None:
            ss[key] = out
    else:
        ss[key] = st.text_area("HTML", ss[key], height=420, key=f"src_{pid}")
    if not HAVE_QUILL:
        st.caption("Visual editor package not installed; add streamlit-quill to requirements.txt.")

    # ---- save (after the editor so the latest content is captured)
    for wanted, status in ((want_draft, "draft"), (want_pub, "published")):
        if wanted:
            store.save_post(pid, title, ss[key], topic, status)
            waiting, err = indexer.refresh("post", pid)
            state.markdown(f'<span class="muted">{"Draft saved" if status == "draft" else "Published"}</span>', unsafe_allow_html=True)
            if err:
                st.warning(f"Saved, but indexing needs attention: {err}")
            elif waiting > 0:
                st.info(f"{waiting} chunks are waiting to be embedded. Press Sync in Knowledge index.")

    with st.popover("Delete post"):
        if st.button("Yes, delete", key=f"del_{pid}"):
            store.delete_post(pid)
            ss.post_id = None
            st.rerun()


editor_view(ss.post_id) if ss.post_id else list_view()
