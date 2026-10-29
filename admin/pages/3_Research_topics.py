import streamlit as st

st.set_page_config(page_title="Research topics", layout="wide")
from lib.auth import require_login
require_login()
from lib import store
from lib.theme import apply_theme, esc, pill
from lib.auth import current_user_id
from lib.walk import all_files

apply_theme()
ss = st.session_state
ss.setdefault("topic_open", None)


def detail(tid):
    t = next((x for x in store.topics() if x["id"] == tid), None)
    if not t:
        ss.topic_open = None
        st.rerun()
    top, back = st.columns([6, 1])
    top.markdown(f'<div class="crumbs">Research topics / <b>{esc(t["name"])}</b></div>', unsafe_allow_html=True)
    if back.button("All topics"):
        ss.topic_open = None
        st.rerun()

    left, right = st.columns([1, 2])
    with left:
        with st.container(border=True):
            st.subheader("Details")
            nn = st.text_input("Name", t["name"], key=f"dn{tid}")
            nd = st.text_area("Description", t["description"], height=110, key=f"dd{tid}")
            if st.button("Save", type="primary", key=f"ds{tid}") and nn.strip():
                store.update_topic(tid, nn, nd)
                st.rerun()
    with right:
        with st.container(border=True):
            files = [f for f in all_files(current_user_id()) if f.get("topic_id") == tid]
            posts = [p for p in store.posts() if p.get("topic_id") == tid]
            st.subheader("Files")
            if not files:
                st.markdown('<p class="muted">No files yet. Assign this topic when uploading, or from a file\'s page.</p>',
                            unsafe_allow_html=True)
            for f in files:
                if st.button(f["name"], key=f"tf{f['id']}"):
                    ss.open_file, ss.folder = f["id"], f.get("folder_id")
                    st.switch_page("pages/1_File_manager.py")
            st.subheader("Writing")
            for p in posts:
                c1, c2 = st.columns([5, 1])
                if c1.button(p["title"], key=f"tp{p['id']}"):
                    ss.post_id = p["id"]
                    st.switch_page("pages/4_Writing.py")
                c2.markdown(pill(p["status"]), unsafe_allow_html=True)
            a, b = st.columns([2, 1])
            if a.button("New post in this topic", key=f"np{tid}"):
                tpls = store.templates()
                html = tpls[0]["html"] if tpls else ""
                ss.post_id = store.create_post(html, tid, tpls[0]["id"] if tpls else None)["id"]
                st.switch_page("pages/4_Writing.py")
            with b.popover("Delete topic"):
                st.caption("Files and posts are kept; they just lose this topic.")
                if st.button("Delete", key=f"tx{tid}"):
                    store.delete_topic(tid)
                    ss.topic_open = None
                    st.rerun()


if ss.topic_open:
    detail(ss.topic_open)
else:
    st.title("Research topics")
    left, right = st.columns([1, 2])
    with left:
        with st.container(border=True):
            with st.form("new_topic", clear_on_submit=True, border=False):
                st.subheader("New topic")
                n = st.text_input("Name")
                d = st.text_area("What is it about?", height=100)
                if st.form_submit_button("Create topic", type="primary") and n.strip():
                    store.create_topic(n, d)
                    st.rerun()
    with right:
        with st.container(border=True):
            st.subheader("All topics")
            topics = store.topics()
            if not topics:
                st.markdown('<p class="muted">No topics yet. Create one, then attach files and posts to it.</p>',
                            unsafe_allow_html=True)
            for t in topics:
                c1, c2 = st.columns([3, 2])
                if c1.button(t["name"], key=f"lk_to{t['id']}", use_container_width=True):
                    ss.topic_open = t["id"]
                    st.rerun()
                c2.markdown(f'<span class="muted">{t["files"]} files, {t["posts"]} posts</span>', unsafe_allow_html=True)
