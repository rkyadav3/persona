import streamlit as st
from supabase import create_client
from .config import secret

BUCKET = "files"


@st.cache_resource
def sb():
    url, key = secret("SUPABASE_URL"), secret("SUPABASE_SERVICE_KEY")
    if not url or not key:
        st.error("Missing SUPABASE_URL or SUPABASE_SERVICE_KEY in secrets.")
        st.stop()
    return create_client(url, key)


def paged(table, select="*", apply=None, page=1000):
    """Fetch every row (PostgREST returns at most 1000 per request)."""
    out, start = [], 0
    while True:
        q = sb().table(table).select(select)
        if apply:
            q = apply(q)
        rows = q.range(start, start + page - 1).execute().data
        out += rows
        if len(rows) < page:
            return out
        start += page
