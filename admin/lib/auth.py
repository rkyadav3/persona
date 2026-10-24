import hmac
import streamlit as st
from .config import secret


def require_login():
    """Call at the top of every page. Shows a password box until the admin signs in."""
    if st.session_state.get("ok"):
        with st.sidebar:
            if st.button("Sign out"):
                st.session_state.clear()
                st.rerun()
        return
    expected = secret("ADMIN_PASSWORD")
    st.title("Studio")
    if not expected:
        st.error("ADMIN_PASSWORD is not set in secrets.")
        st.stop()
    pw = st.text_input("Password", type="password")
    if st.button("Sign in", type="primary"):
        if hmac.compare_digest(pw.encode(), str(expected).encode()):
            st.session_state.ok = True
            st.rerun()
        st.error("Wrong password.")
    st.stop()
