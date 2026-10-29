import streamlit as st

st.set_page_config(page_title="Templates", layout="wide")
from lib.auth import require_login
require_login()
from lib import store
from lib.theme import apply_theme

apply_theme()
ss = st.session_state

st.title("Templates")
st.markdown('<p class="muted">Templates are starting layouts for new posts. Write HTML, then start a post from it.</p>',
            unsafe_allow_html=True)
left, right = st.columns([1, 2])
with left:
    with st.container(border=True):
        with st.form("new_tpl", clear_on_submit=True, border=False):
            st.subheader("New template")
            n = st.text_input("Name")
            h = st.text_area("HTML", height=200)
            if st.form_submit_button("Save template", type="primary") and n.strip():
                store.save_template(None, n, h)
                st.rerun()
with right:
    with st.container(border=True):
        st.subheader("Your templates")
        for t in store.templates():
            with st.expander(t["name"]):
                nn = st.text_input("Name", t["name"], key=f"tn{t['id']}")
                nh = st.text_area("HTML", t["html"], height=160, key=f"th{t['id']}")
                a, b, c = st.columns(3)
                if a.button("Update", key=f"tu{t['id']}"):
                    store.save_template(t["id"], nn, nh)
                    st.rerun()
                if b.button("Start a post", key=f"ts{t['id']}"):
                    ss.post_id = store.create_post(t["html"], None, t["id"])["id"]
                    st.switch_page("pages/4_Writing.py")
                if c.button("Delete", key=f"tx{t['id']}"):
                    store.delete_template(t["id"])
                    st.rerun()
