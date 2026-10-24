import streamlit as st

st.set_page_config(page_title="Templates", layout="wide")
from lib.auth import require_login
require_login()
from lib import store

st.title("Templates")
st.caption("Starting layouts for new posts. Write HTML.")
left, right = st.columns([1, 2])
with left:
    with st.form("new_tpl", clear_on_submit=True):
        st.subheader("New template")
        n = st.text_input("Name")
        h = st.text_area("HTML", height=200)
        if st.form_submit_button("Save template", type="primary") and n.strip():
            store.save_template(None, n, h)
            st.rerun()
with right:
    for t in store.templates():
        with st.expander(t["name"]):
            nn = st.text_input("Name", t["name"], key=f"tn{t['id']}")
            nh = st.text_area("HTML", t["html"], height=160, key=f"th{t['id']}")
            a, b = st.columns(2)
            if a.button("Update", key=f"tu{t['id']}"):
                store.save_template(t["id"], nn, nh)
                st.rerun()
            if b.button("Delete", key=f"tx{t['id']}"):
                store.delete_template(t["id"])
                st.rerun()
