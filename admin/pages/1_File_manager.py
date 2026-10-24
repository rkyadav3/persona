import streamlit as st

st.set_page_config(page_title="File manager", layout="wide")
from lib.auth import require_login
require_login()
from lib import store, indexer
from lib.extract import is_text
from lib.ui import fmt_size, folder_select, topic_select

ss = st.session_state
ss.setdefault("folder", None)
ss.setdefault("open_file", None)


def editor(fid):
    f = store.get_file(fid)
    if not f:
        ss.open_file = None
        return
    with st.container(border=True):
        top, close = st.columns([6, 1])
        top.subheader(f["name"])
        if close.button("Close", key=f"x{fid}"):
            ss.open_file = None
            st.rerun()
        name = st.text_input("Name", f["name"], key=f"n{fid}")
        c1, c2 = st.columns(2)
        with c1:
            topic = topic_select("Research topic", f"t{fid}", f["topic_id"])
        with c2:
            status = st.radio("Status", ["published", "draft"], index=0 if f["status"] == "published" else 1,
                              horizontal=True, key=f"s{fid}", help="Drafts are never used by the chatbot.")
        editable = is_text(f["name"])
        text = None
        if editable:
            text = st.text_area("Content", f["text_content"], height=380, key=f"c{fid}")
        else:
            st.caption("This file type can't be edited here. Text extracted from PDF and Word files is searchable by the chatbot.")
        s1, s2 = st.columns([1, 1])
        if s1.button("Save", type="primary", key=f"sv{fid}"):
            store.save_file(fid, name, topic, status, text)
            waiting, err = indexer.refresh("file", fid)
            st.success("Saved.")
            if err:
                st.warning(f"Saved, but indexing needs attention: {err}")
            elif waiting > 0:
                st.info(f"{waiting} chunks are still waiting to be embedded. Press Sync in Knowledge index.")
        try:
            s2.link_button("Download", store.signed_url(f["storage_path"]))
        except Exception:
            s2.caption("Download link unavailable.")
        m1, m2 = st.columns([3, 1])
        with m1:
            dest = folder_select("Move to folder", f"m{fid}", f["folder_id"])
        if m2.button("Move", key=f"mv{fid}"):
            store.move_file(fid, dest)
            st.rerun()
        with st.popover("Delete this file"):
            st.warning("This removes the file and its searchable chunks.")
            if st.button("Yes, delete", key=f"del{fid}"):
                store.delete_file(fid)
                ss.open_file = None
                st.rerun()


head, btn = st.columns([4, 1])
head.title("File manager")
btn.page_link("pages/2_Add_files.py", label="Add files")

crumbs = store.breadcrumbs(ss.folder)
st.caption("All files" + "".join(f" / {c['name']}" for c in crumbs))
if ss.folder is not None and st.button("Up one level"):
    ss.folder = crumbs[-2]["id"] if len(crumbs) > 1 else None
    ss.open_file = None
    st.rerun()

if ss.open_file:
    editor(ss.open_file)

q = st.text_input("Search names and contents", key="q")
folders = [] if q else store.children(ss.folder)
files = store.search_files(q) if q else store.list_files(ss.folder)
topics = {t["id"]: t["name"] for t in store.topics()}

for f in folders:
    c1, c2, c3 = st.columns([6, 1, 1])
    if c1.button(f"Folder: {f['name']}", key=f"f{f['id']}", use_container_width=True):
        ss.folder, ss.open_file = f["id"], None
        st.rerun()
    with c2.popover("Rename"):
        nn = st.text_input("New name", f["name"], key=f"rn{f['id']}")
        if st.button("Save", key=f"rs{f['id']}"):
            store.rename_folder(f["id"], nn)
            st.rerun()
    with c3.popover("Delete"):
        st.warning("Deletes the folder and everything inside it.")
        if st.button("Delete folder", key=f"fd{f['id']}"):
            store.delete_folder(f["id"])
            st.rerun()

if files:
    h = st.columns([5, 2, 1, 1])
    for col, label in zip(h, ["Name", "Topic", "Status", "Size"]):
        col.caption(label)
for f in files[:200]:
    c1, c2, c3, c4 = st.columns([5, 2, 1, 1])
    if c1.button(f["name"], key=f"o{f['id']}"):
        ss.open_file = f["id"]
        st.rerun()
    c2.write(topics.get(f["topic_id"], ""))
    c3.write(f["status"])
    c4.write(fmt_size(f["size"]))
if not folders and not files:
    st.info("Nothing here. Use Add files to upload or create something.")
