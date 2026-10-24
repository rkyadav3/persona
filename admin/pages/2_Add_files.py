import io
import os
import zipfile

import streamlit as st

st.set_page_config(page_title="Add files", layout="wide")
from lib.auth import require_login
require_login()
from lib import store, indexer
from lib.ui import folder_select, topic_select

st.title("Add files")
st.caption("Add new material here. To browse, edit, move or delete, use the File manager.")
up_tab, new_tab, folder_tab = st.tabs(["Upload", "Create a text file", "New folder"])


def finish(new_ids):
    """Chunk every new file, then embed as much as the free tier allows."""
    if not new_ids:
        return
    with st.spinner("Indexing for search..."):
        err = None
        for i in new_ids:
            try:
                indexer.index_source("file", i)
            except Exception as e:
                err = str(e)
        waiting, err2 = indexer.refresh("file", new_ids[-1], seconds=60)
    err = err or err2
    if err:
        st.warning(f"Files are saved, but embedding needs attention: {err}")
    elif waiting > 0:
        st.info(f"{waiting} chunks are still waiting to be embedded (free-tier rate limit). Open Knowledge index and press Sync to continue.")
    else:
        st.success("Indexed. The chatbot can use these files now.")


with up_tab:
    uploaded = st.file_uploader("Files or a zip (a folder? zip it first)", accept_multiple_files=True)
    unzip = st.checkbox("Unzip zip files into folders", value=True)
    c1, c2 = st.columns(2)
    with c1:
        dest = folder_select("Save into folder", "up_folder")
    with c2:
        topic = topic_select("Research topic", "up_topic")
    if st.button("Upload", type="primary", disabled=not uploaded):
        items = []
        for up in uploaded:
            data = up.getvalue()
            if unzip and up.name.lower().endswith(".zip"):
                base = os.path.splitext(up.name)[0]
                with zipfile.ZipFile(io.BytesIO(data)) as z:
                    infos = [i for i in z.infolist() if not i.is_dir()]
                    if len(infos) > 2000 or sum(i.file_size for i in infos) > 300 * 1048576:
                        st.error(f"{up.name} is too large to unzip here.")
                        continue
                    for i in infos:
                        parts = [p for p in i.filename.split("/") if p and p not in (".", "..")]
                        if not parts or parts[0] == "__MACOSX" or i.file_size > 50 * 1048576:
                            continue
                        items.append(("/".join([base] + parts), z.read(i)))   # never writes using the zip's own paths
            else:
                items.append((up.name, data))
        bar, new_ids = st.progress(0.0), []
        for n, (rel, data) in enumerate(items):
            parts = rel.split("/")
            name = parts.pop()
            try:
                fid = store.ensure_path(dest, parts) if parts else dest
                new_ids.append(store.add_file(fid, topic, name, data)["id"])
            except Exception as e:
                st.error(f"{rel}: {e}")
            bar.progress((n + 1) / max(1, len(items)))
        st.success(f"Uploaded {len(new_ids)} file(s).")
        finish(new_ids)

with new_tab:
    with st.form("create_text"):
        name = st.text_input("File name", placeholder="e.g. notes-on-method")
        kind = st.selectbox("Type", ["md", "txt", "html", "csv", "json"])
        c1, c2 = st.columns(2)
        with c1:
            nf = folder_select("Save into folder", "nt_folder")
        with c2:
            nt = topic_select("Research topic", "nt_topic")
        body = st.text_area("Content", height=240)
        b1, b2 = st.columns(2)
        as_draft = b1.form_submit_button("Save as draft")
        publish = b2.form_submit_button("Create and publish", type="primary")
    if (as_draft or publish) and name.strip():
        fname = name.strip().replace("/", "-")
        if not fname.lower().endswith("." + kind):
            fname += "." + kind
        row = store.add_file(nf, nt, fname, body.encode("utf-8"), "draft" if as_draft else "published", text=body)
        st.success(f"Created {fname}.")
        if publish:
            finish([row["id"]])
    elif (as_draft or publish):
        st.error("Give the file a name.")

with folder_tab:
    with st.form("new_folder"):
        fname = st.text_input("Folder name")
        parent = folder_select("Inside", "nf_parent")
        go = st.form_submit_button("Create folder")
    if go and fname.strip():
        try:
            store.create_folder(parent, fname)
            st.success("Folder created.")
        except Exception as e:
            st.error(f"Couldn't create it (does that name already exist there?): {e}")
