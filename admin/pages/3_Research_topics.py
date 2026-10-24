import streamlit as st

st.set_page_config(page_title="Research topics", layout="wide")
from lib.auth import require_login
require_login()
from lib import store

st.title("Research topics")
left, right = st.columns([1, 2])
with left:
    with st.form("new_topic", clear_on_submit=True):
        st.subheader("New topic")
        n = st.text_input("Name")
        d = st.text_area("What is it about?", height=100)
        if st.form_submit_button("Create topic", type="primary") and n.strip():
            store.create_topic(n, d)
            st.rerun()
with right:
    topics = store.topics()
    if not topics:
        st.info("No topics yet. Create one, then attach files and posts to it.")
    for t in topics:
        with st.expander(f"{t['name']}  ·  {t['files']} files, {t['posts']} posts"):
            nn = st.text_input("Name", t["name"], key=f"tn{t['id']}")
            nd = st.text_area("Description", t["description"], key=f"td{t['id']}")
            a, b = st.columns(2)
            if a.button("Save", key=f"ts{t['id']}"):
                store.update_topic(t["id"], nn, nd)
                st.rerun()
            with b.popover("Delete topic"):
                st.caption("Files and posts are kept; they just lose this topic.")
                if st.button("Delete", key=f"tx{t['id']}"):
                    store.delete_topic(t["id"])
                    st.rerun()
