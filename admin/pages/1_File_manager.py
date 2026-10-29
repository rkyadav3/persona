import streamlit as st

st.set_page_config(page_title="File manager", layout="wide")
from lib.auth import require_login
require_login()
from lib import store, indexer
from lib.extract import is_text
from lib.theme import apply_theme, pill, table_header, esc
from lib.ui import fmt_size, folder_select, topic_select

apply_theme()
ss = st.session_state
ss.setdefault("folder", None)
ss.setdefault("open_file", None)


def editor(fid):
    f = store.get_file(fid)
    if not f:
        ss.open_file = None
        return
    editable = is_text(f["name"])
    with st.container(border=True):
        # breadcrumb: All files / folders / this file
        trail = store.breadcrumbs(f["folder_id"]) if f.get("folder_id") else []
        st.markdown('<div class="crumbs">All files' + "".join(f" / {esc(c['name'])}" for c in trail)
                    + f" / <b>{esc(f['name'])}</b></div>", unsafe_allow_html=True)
        # top bar: name | topic | download | save buttons | close
        n, t, d = st.columns([4, 2, 1])
        name = n.text_input("Name", f["name"], key=f"n{fid}")
        with t:
            topic = topic_select("Research topic", f"t{fid}", f["topic_id"])
        with d:
            st.write("")
            try:
                st.link_button("Download", store.signed_url(f["storage_path"]), use_container_width=True)
            except Exception:
                st.caption("Download unavailable.")
        text = None
        if editable:
            text = st.text_area("Content", f["text_content"], height=380, key=f"c{fid}")
        else:
            st.markdown('<p class="muted">This file type can\'t be edited here and isn\'t searchable by the persona yet. '
                        'Rename it, assign a topic, or download it. (Text extracted from PDF and Word files is searchable.)</p>',
                        unsafe_allow_html=True)

        def save(status):
            store.save_file(fid, name, topic, status, text)
            waiting, err = indexer.refresh("file", fid)
            st.success("Saved as draft." if status == "draft" else "Saved." if not editable else "Published.")
            if err:
                st.warning(f"Saved, but indexing needs attention: {err}")
            elif waiting > 0:
                st.info(f"{waiting} chunks are still waiting to be embedded. Press Sync in Knowledge index.")

        b = st.columns([1, 1, 1, 4])
        if editable:
            if b[0].button("Save as draft", key=f"sd{fid}"):
                save("draft")
            if b[1].button("Save and publish", type="primary", key=f"sp{fid}"):
                save("published")
        else:
            if b[0].button("Save details", type="primary", key=f"sv{fid}"):
                save(f["status"])
        if b[2].button("Close", key=f"x{fid}"):
            ss.open_file = None
            st.rerun()

        m1, m2 = st.columns([3, 1])
        with m1:
            dest = folder_select("Move to folder", f"m{fid}", f["folder_id"])
        m2.write("")
        if m2.button("Move", key=f"mv{fid}"):
            store.move_file(fid, dest)
            st.rerun()
        with st.popover("Delete this file"):
            st.warning("This removes the file and its searchable chunks.")
            if st.button("Yes, delete", key=f"del{fid}"):
                store.delete_file(fid)
                ss.open_file = None
                st.rerun()


# ---- header bar: title | search | Add files
head, srch, btn = st.columns([3, 3, 1])
head.title("File manager")
with srch:
    st.write("")
    q = st.text_input("Search", key="q", placeholder="Search names and contents", label_visibility="collapsed")
with btn:
    st.write("")
    st.page_link("pages/2_Add_files.py", label="Add files", icon=":material/add:")

# ---- clickable breadcrumb: All files / a / b
crumbs = store.breadcrumbs(ss.folder)
cc = st.columns([1] * (len(crumbs) + 1) + [max(1, 8 - len(crumbs))])
if cc[0].button("All files", key="cr_root"):
    ss.folder, ss.open_file = None, None
    st.rerun()
for i, c in enumerate(crumbs, 1):
    if cc[i].button(f"/ {c['name']}", key=f"cr{c['id']}"):
        ss.folder, ss.open_file = c["id"], None
        st.rerun()
if q:
    st.markdown(f'<div class="crumbs">search results for “{esc(q)}”</div>', unsafe_allow_html=True)

if ss.open_file:
    editor(ss.open_file)

folders = [] if q else store.children(ss.folder)
files = store.search_files(q) if q else store.list_files(ss.folder)
topics = {t["id"]: t["name"] for t in store.topics()}

# ---- table
W = [5, 2, 1.6, 1, 2]
table_header(["Name", "Topic", "Status", "Size", ""], W)

for f in folders:
    c1, c2, c3, c4, c5 = st.columns(W)
    if c1.button(f"📁 {f['name']}", key=f"f{f['id']}", use_container_width=True):
        ss.folder, ss.open_file = f["id"], None
        st.rerun()
    with c5:
        r, d = st.columns(2)
        with r.popover("Rename"):
            nn = st.text_input("New name", f["name"], key=f"rn{f['id']}")
            if st.button("Save", key=f"rs{f['id']}"):
                store.rename_folder(f["id"], nn)
                st.rerun()
        with d.popover("Delete"):
            st.warning("Deletes the folder and everything inside it.")
            if st.button("Delete folder", key=f"fd{f['id']}"):
                store.delete_folder(f["id"])
                st.rerun()

for f in files[:200]:
    c1, c2, c3, c4, c5 = st.columns(W)
    if c1.button(f["name"], key=f"o{f['id']}", use_container_width=True):
        ss.open_file = f["id"]
        st.rerun()
    c2.write(topics.get(f["topic_id"], ""))
    c3.markdown(pill(f["status"]), unsafe_allow_html=True)
    c4.write(fmt_size(f["size"]))
    with c5.popover("Delete"):
        st.warning("This removes the file and its searchable chunks.")
        if st.button("Yes, delete", key=f"rd{f['id']}"):
            store.delete_file(f["id"])
            if ss.open_file == f["id"]:
                ss.open_file = None
            st.rerun()

if not files:
    if q:
        st.info("No files match your search.")
    elif not folders:
        st.info("This folder is empty. Use Add files to upload or create something.")
