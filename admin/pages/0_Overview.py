import streamlit as st

st.set_page_config(page_title="Overview", layout="wide")
from lib.auth import require_login
require_login()
from lib import store
from lib.theme import apply_theme, esc, stats
from lib.walk import all_files

apply_theme()
ss = st.session_state

files = all_files()
posts = store.posts()
topics = store.topics()
total_bytes = sum((f.get("size") or 0) for f in files)
drafts = sum(1 for p in posts if p["status"] == "draft")

st.title("Overview")
stats([
    (len(files), "files", f"{total_bytes / 1048576:.1f} MB stored"),
    (len(posts), "posts", f"{drafts} drafts"),
    (len(topics), "research topics", None),
])

left, right = st.columns(2)
with left:
    with st.container(border=True):
        st.subheader("Start something")
        a, b = st.columns(2)
        a.page_link("pages/4_Writing.py", label="Write a post", icon=":material/edit:")
        b.page_link("pages/2_Add_files.py", label="Add files", icon=":material/upload:")
        a.page_link("pages/1_File_manager.py", label="File manager", icon=":material/folder:")
        b.page_link("pages/3_Research_topics.py", label="New topic", icon=":material/topic:")
        st.markdown('<p class="muted">The persona only answers from published files and published posts. Drafts stay private.</p>',
                    unsafe_allow_html=True)
with right:
    with st.container(border=True):
        st.subheader("Recently changed files")
        recent = sorted(files, key=lambda f: f.get("updated_at") or f.get("created_at") or "", reverse=True)[:8]
        if not recent:
            st.markdown('<p class="muted">Nothing uploaded yet. Add your first research file.</p>', unsafe_allow_html=True)
        for f in recent:
            if st.button(f["name"], key=f"lk_rc{f['id']}", use_container_width=True):
                ss.open_file, ss.folder = f["id"], f.get("folder_id")
                st.switch_page("pages/1_File_manager.py")
