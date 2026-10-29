import datetime as dt
import secrets

import streamlit as st

st.set_page_config(page_title="Invites", layout="wide")
from lib.auth import require_login, is_admin, norm_code
require_login()
from lib.config import secret
from lib.db import raw_sb          # global tables (users, invite_codes): admin only, guarded below
from lib.theme import apply_theme, pill

apply_theme()
if not is_admin():
    st.error("This page is for admins. Add your email to ADMIN_EMAILS in the app secrets.")
    st.stop()

db = raw_sb()
ss = st.session_state
ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"     # no 0/O/1/I


def fmt(code):
    return f"{code[:4]}-{code[4:]}"


def make_code():
    while True:
        c = "".join(secrets.choice(ALPHABET) for _ in range(8))
        if not db.table("invite_codes").select("id").eq("code", c).execute().data:
            return c


st.title("Invites and users")
st.markdown('<p class="muted">Registration mode is set by <code>REGISTRATION_MODE</code> in the app secrets: '
            '<b>open</b>, <b>invite</b> or <b>closed</b>. Codes only matter in invite mode.</p>', unsafe_allow_html=True)

with st.container(border=True):
    st.subheader("New invite code")
    with st.form("new_invite", border=False):
        c1, c2, c3 = st.columns([3, 1, 1])
        label = c1.text_input("Label", placeholder="e.g. Skyline Scholars team")
        uses = c2.number_input("Max uses", 1, 1000, 1)
        days = c3.number_input("Expires in (days, 0 = never)", 0, 365, 14)
        if st.form_submit_button("Create code", type="primary"):
            code = make_code()
            exp = (dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=int(days))).isoformat() if days else None
            db.table("invite_codes").insert({"code": code, "label": label.strip() or None, "max_uses": int(uses),
                                            "expires_at": exp, "created_by": ss["uid"]}).execute()
            ss["new_code"] = code
    if ss.get("new_code"):
        st.success("Code created. Copy it now or use the link.")
        st.code(fmt(ss["new_code"]))
        app = str(secret("APP_URL", "")).rstrip("/")
        if app:
            st.code(f"{app}/?invite={ss['new_code']}")

codes = db.table("invite_codes").select("*").order("created_at", desc=True).execute().data
with st.container(border=True):
    st.subheader("Codes")
    if not codes:
        st.markdown('<p class="muted">No codes yet.</p>', unsafe_allow_html=True)
    now = dt.datetime.now(dt.timezone.utc)
    for c in codes:
        exp = dt.datetime.fromisoformat(c["expires_at"].replace("Z", "+00:00")) if c.get("expires_at") else None
        status = "revoked" if c["revoked"] else "expired" if exp and exp < now else "used up" if c["uses"] >= c["max_uses"] else "active"
        a, b, d, e, f = st.columns([2, 3, 1.2, 1.2, 1])
        a.code(fmt(c["code"]))
        b.write(c.get("label") or "")
        d.write(f"{c['uses']} / {c['max_uses']} used")
        e.markdown(f'<span class="pill {"published" if status == "active" else "draft"}">{status}</span>', unsafe_allow_html=True)
        if status == "active" and f.button("Revoke", key=f"rv{c['id']}"):
            db.table("invite_codes").update({"revoked": True}).eq("id", c["id"]).execute()
            st.rerun()

with st.container(border=True):
    st.subheader("Users")
    users = db.table("users").select("email,name,slug,created_at,invite_code_id").order("created_at", desc=True).execute().data
    labels = {c["id"]: c.get("label") or fmt(c["code"]) for c in codes}
    st.dataframe([{"email": u["email"], "name": u.get("name") or "", "joined": (u["created_at"] or "")[:16].replace("T", " "),
                   "invite": labels.get(u.get("invite_code_id"), "")} for u in users], use_container_width=True, hide_index=True)
