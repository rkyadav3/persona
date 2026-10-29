"""Collect every file across the folder tree (used by the dashboard and topic pages)."""
import streamlit as st

from lib import store


@st.cache_data(ttl=20, show_spinner=False)
def all_files():
    out, stack, seen = [], [None], set()
    while stack:
        fid = stack.pop()
        if fid in seen:
            continue
        seen.add(fid)
        out += store.list_files(fid)
        stack += [c["id"] for c in store.children(fid)]
    return out
