import streamlit as st
from . import store


def fmt_size(n):
    n = n or 0
    return f"{n / 1048576:.1f} MB" if n > 1048576 else f"{max(1, round(n / 1024))} KB"


def folder_select(label, key, default=None):
    opts = [(None, "Top level")] + store.folder_paths()
    ids = [o[0] for o in opts]
    idx = ids.index(default) if default in ids else 0
    return st.selectbox(label, ids, index=idx, format_func=lambda i: dict(opts)[i], key=key)


def topic_select(label, key, default=None):
    ts = store.topics()
    ids = [None] + [t["id"] for t in ts]
    names = {None: "No topic", **{t["id"]: t["name"] for t in ts}}
    idx = ids.index(default) if default in ids else 0
    return st.selectbox(label, ids, index=idx, format_func=lambda i: names[i], key=key)
