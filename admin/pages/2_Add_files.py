import io
import os
import zipfile

import streamlit as st

st.set_page_config(page_title="Add files", layout="wide")
from lib.auth import require_login
require_login()
from lib import store, indexer
from lib.theme import apply_theme
from lib.ui import folder_select, topic_select

apply_theme()
ss = st.session_state
cur = ss.get("folder")

head, go_btn = st.columns([5, 1])
head.title("Add files")
go_btn.page_link("pages/1_File_manager.py", label="Go to file manager", icon=":material/folder:")
st.markdown('<p class="muted">Add new material here. To browse, rename, move or delete files, use the file manager.</p>',
            unsafe_allow_html=True)


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


up_col, new_col, folder_col = st.columns([3, 3, 2])

# ---- card 1: upload
with up_col:
    with st.container(border=True):
        st.subheader("Upload files or a zip")
        uploaded = st.file_uploader("Drop files here (a folder? zip it first)", accept_multiple_files=True)
        unzip = st.checkbox("Unzip zip files into folders", value=True)
        dest = folder_select("Save into folder", "up_folder", cur)
        topic = topic_select("Research topic", "up_topic")
        n_sel = len(uploaded or [])
        st.markdown(f'<p class="muted">{n_sel} file(s) chosen.</p>' if n_sel else '<p class="muted">No files chosen.</p>',
                    unsafe_allow_html=True)
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

# ---- card 2: create text file
with new_col:
    with st.container(border=True):
        st.subheader("Create a new text file")
        with st.form("create_text", border=False):
            name = st.text_input("File name", placeholder="e.g. notes-on-method")
            kind = st.selectbox("Type", ["md", "txt", "html", "csv", "json"],
                                format_func=lambda k: {"md": "Markdown (.md)", "txt": "Plain text (.txt)", "html": "HTML (.html)",
                                                       "csv": "CSV (.csv)", "json": "JSON (.json)"}[k])
            nf = folder_select("Save into folder", "nt_folder", cur)
            nt = topic_select("Research topic", "nt_topic")
            body = st.text_area("Content", height=180)
            b1, b2 = st.columns(2)
            as_draft = b1.form_submit_button("Save as draft")
            publish = b2.form_submit_button("Create and publish", type="primary")
        st.markdown('<p class="muted">Drafts stay private. Only published files feed the persona.</p>', unsafe_allow_html=True)
        if (as_draft or publish) and name.strip():
            fname = name.strip().replace("/", "-")
            if not fname.lower().endswith("." + kind):
                fname += "." + kind
            row = store.add_file(nf, nt, fname, body.encode("utf-8"), "draft" if as_draft else "published", text=body)
            st.success(f"Created {fname}.")
            if publish:
                finish([row["id"]])
        elif as_draft or publish:
            st.error("Give the file a name.")

# ---- card 3: new folder
with folder_col:
    with st.container(border=True):
        st.subheader("New folder")
        with st.form("new_folder", border=False):
            fname = st.text_input("Name")
            parent = folder_select("Inside", "nf_parent", cur)
            go = st.form_submit_button("Create folder")
        if go and fname.strip():
            try:
                store.create_folder(parent, fname)
                st.success("Folder created.")
            except Exception as e:
                st.error(f"Couldn't create it (does that name already exist there?): {e}")
