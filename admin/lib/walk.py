"""Collect every file across the folder tree. The cache is keyed by user id: without it one tenant could be
served another tenant's cached list."""
import streamlit as st

from lib import store


@st.cache_data(ttl=20, show_spinner=False)
def all_files(uid):
    out, stack, seen = [], [None], set()
    while stack:
        fid = stack.pop()
        if fid in seen:
            continue
        seen.add(fid)
        out += store.list_files(fid)
        stack += [c["id"] for c in store.children(fid)]
    return out
