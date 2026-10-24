import streamlit as st

st.set_page_config(page_title="Knowledge index", layout="wide")
from lib.auth import require_login
require_login()
from lib import store, indexer
from lib.config import secret
from lib.db import sb
from lib.embed import MODEL
from lib.search import search

st.title("Knowledge index")
st.caption("Published files and posts are split into chunks, turned into vectors, and stored in Supabase. The website searches this index. Drafts are never indexed.")

c = store.counts()
a, b, d = st.columns(3)
a.metric("Chunks", c["chunks"])
b.metric("Embedded", c["embedded"])
d.metric("Waiting for embedding", c["chunks"] - c["embedded"])

s1, s2 = st.columns([1, 1])
if s1.button("Sync now", type="primary", help="Adds new/changed content, drops removed content, and embeds what's pending."):
    bar = st.progress(0.0, text="Starting...")
    try:
        res = indexer.sync_all(max_seconds=240, progress=lambda n: bar.progress(min(1.0, n / max(1, c["chunks"] - c["embedded"] + n)), text=f"Embedded {n} chunks"))
        st.success(f"Added {res['added']} source(s), removed {res['removed']}, embedded {res['embedded']} chunk(s).")
        if res["remaining"]:
            st.info(f"{res['remaining']} chunks still waiting. The free tier limits embedding speed. Press Sync again to continue where it stopped.")
    except Exception as e:
        st.error(str(e))
with s2.popover("Rebuild everything"):
    st.warning("Deletes every chunk and vector, then you must Sync again (this re-embeds everything).")
    if st.button("Delete the index"):
        indexer.rebuild_all()
        st.rerun()

st.subheader("Settings in use")
st.write(f"Embedding model: **{MODEL()}** (768 dimensions)  ·  Similarity gate: **{secret('MIN_SIMILARITY', 0.6)}**  ·  Keyword gate: **{secret('MIN_KEYWORD_RANK', 0.2)}**")
st.caption("The website reads the same values from its own Vercel environment variables (MIN_SIMILARITY, MIN_KEYWORD_RANK).")

st.subheader("Test retrieval")
q = st.text_input("Ask a question and see which chunks come back")
if q:
    try:
        rows = search(q)
        if not rows:
            st.info("Nothing passed the relevance gate, so the chatbot would say it has no answer.")
        for i, r in enumerate(rows, 1):
            with st.container(border=True):
                st.markdown(f"**{i}. {r['source_name']}**" + (f" › {r['heading']}" if r["heading"] else ""))
                st.caption(f"similarity {r['similarity']:.3f}  ·  keyword rank {r['keyword_rank']:.2f}")
                st.write(r["content"][:600])
    except Exception as e:
        st.error(str(e))

st.subheader("Recent questions")
log = sb().table("chat_log").select("*").order("created_at", desc=True).limit(50).execute().data
if not log:
    st.caption("No questions yet.")
else:
    st.caption("Unanswered questions show what your research is missing, or where the relevance gate is too strict.")
    st.dataframe([{"asked": r["created_at"][:16].replace("T", " "), "question": r["question"],
                   "answered": "yes" if r["answered"] else "NO", "top similarity": r["top_similarity"]} for r in log],
                 use_container_width=True, hide_index=True)
