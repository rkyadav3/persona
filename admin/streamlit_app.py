import streamlit as st

st.set_page_config(page_title="Studio", layout="wide")
from lib.auth import require_login
require_login()
from lib import store
from lib.ui import fmt_size

st.title("Overview")
c = store.counts()
a, b, d, e = st.columns(4)
a.metric("Files", c["files"], fmt_size(c["bytes"]))
b.metric("Posts", c["posts"], f"{c['drafts']} drafts")
d.metric("Research topics", c["topics"])
e.metric("Indexed chunks", c["chunks"], f"{c['embedded']} embedded")

if c["chunks"] > c["embedded"]:
    st.warning(f"{c['chunks'] - c['embedded']} chunks are waiting to be embedded. Open Knowledge index and press Sync.")

st.subheader("Start something")
l1, l2, l3, l4 = st.columns(4)
l1.page_link("pages/2_Add_files.py", label="Add files")
l2.page_link("pages/4_Writing.py", label="Write a post")
l3.page_link("pages/3_Research_topics.py", label="Research topics")
l4.page_link("pages/6_Knowledge_index.py", label="Knowledge index")
st.caption("The chatbot only answers from published files and published posts. Drafts stay private.")
