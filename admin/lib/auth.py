"""Self-service accounts: register, sign in, sign out. Replaces the old single-password require_login().
Passwords are hashed with bcrypt; 5 wrong passwords lock the account for 10 minutes (stored in the DB,
so it holds across browsers)."""
import datetime as dt
import re
import secrets

import bcrypt
import streamlit as st

from lib.config import secret
from lib.db import raw_sb          # the UNscoped client: only auth code may touch the users table
from lib.theme import apply_theme

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MAX_FAILS, LOCK_MIN = 5, 10
ss = st.session_state
_DUMMY = bcrypt.hashpw(b"dummy-password", bcrypt.gensalt(12))   # equalises timing for unknown emails


def _now():
    return dt.datetime.now(dt.timezone.utc)


def _parse(ts):
    return dt.datetime.fromisoformat(ts.replace("Z", "+00:00")) if ts else None


def _mode():
    """open = anyone, invite = needs a code, closed = no sign-ups. Set REGISTRATION_MODE in secrets (default open)."""
    if str(secret("ALLOW_REGISTRATION", True)).strip().lower() in ("0", "false", "no", "off"):
        return "closed"
    m = str(secret("REGISTRATION_MODE", "open")).strip().lower()
    return m if m in ("open", "invite", "closed") else "open"


def _registration_open():
    return _mode() != "closed"


def is_admin():
    admins = {e.strip().lower() for e in str(secret("ADMIN_EMAILS", "")).split(",") if e.strip()}
    return bool(ss.get("uid")) and (ss.get("user_email") or "").lower() in admins


def norm_code(code):
    return re.sub(r"[^A-Z0-9]", "", (code or "").upper())


def _check_invite(code):
    """Returns (row, error). Valid = exists, not revoked, not expired, uses left."""
    code = norm_code(code)
    if not code:
        return None, "Enter your invite code."
    rows = raw_sb().table("invite_codes").select("*").eq("code", code).execute().data
    bad = "That invite code isn't valid."
    if not rows:
        return None, bad
    r = rows[0]
    exp = _parse(r.get("expires_at"))
    if r.get("revoked") or (exp and exp < _now()) or (r.get("uses") or 0) >= (r.get("max_uses") or 1):
        return None, bad
    return r, None


def _consume_invite(r):
    """Atomic enough: only succeeds if `uses` is still what we read, so two people can't both take the last use."""
    res = raw_sb().table("invite_codes").update({"uses": (r.get("uses") or 0) + 1}) \
        .eq("id", r["id"]).eq("uses", r.get("uses") or 0).execute()
    return bool(res.data)


def _slug(email):
    base = re.sub(r"[^a-z0-9]+", "-", email.split("@")[0].lower()).strip("-")[:24] or "user"
    return f"{base}-{secrets.token_hex(2)}"


def register(name, email, password, confirm, invite=None):
    email = (email or "").strip().lower()
    if not _registration_open():
        return "Registration is closed."
    if not EMAIL_RE.match(email):
        return "Enter a valid email address."
    if len(password) < 8:
        return "Use at least 8 characters for your password."
    if len(password.encode()) > 72:
        return "Your password is too long (72 characters max)."
    if password != confirm:
        return "The passwords don't match."
    db = raw_sb()
    inv = None
    if _mode() == "invite":
        inv, err = _check_invite(invite)
        if err:
            return err
    if db.table("users").select("id").eq("email", email).execute().data:
        return "An account with that email already exists. Sign in instead."
    pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt(12)).decode()
    try:
        row = db.table("users").insert({"email": email, "name": (name or "").strip() or None,
                                        "slug": _slug(email), "password_hash": pw_hash}).execute().data[0]
    except Exception:
        return "Couldn't create the account. Try again."
    if inv:
        if not _consume_invite(inv):                      # someone used the last slot a moment ago
            db.table("users").delete().eq("id", row["id"]).execute()
            return "That invite code was just used up. Ask for a new one."
        db.table("users").update({"invite_code_id": inv["id"]}).eq("id", row["id"]).execute()
    _start_session(row)
    return None


def login(email, password):
    email = (email or "").strip().lower()
    db = raw_sb()
    rows = db.table("users").select("*").eq("email", email).execute().data
    if not rows:
        bcrypt.checkpw(password.encode()[:72], _DUMMY)
        return "Wrong email or password."
    u = rows[0]
    locked = _parse(u.get("locked_until"))
    if locked and locked > _now():
        return f"Too many attempts. Try again in {int((locked - _now()).total_seconds() // 60) + 1} minutes."
    if not bcrypt.checkpw(password.encode()[:72], u["password_hash"].encode()):
        fails = (u.get("failed_attempts") or 0) + 1
        upd = {"failed_attempts": fails}
        if fails >= MAX_FAILS:
            upd = {"failed_attempts": 0, "locked_until": (_now() + dt.timedelta(minutes=LOCK_MIN)).isoformat()}
        db.table("users").update(upd).eq("id", u["id"]).execute()
        return "Wrong email or password."
    db.table("users").update({"failed_attempts": 0, "locked_until": None}).eq("id", u["id"]).execute()
    _start_session(u)
    return None


def _start_session(u):
    ss.clear()                                  # never carry state over from a previous user
    ss["uid"] = str(u["id"])
    ss["user_email"], ss["user_name"], ss["user_slug"] = u["email"], u.get("name"), u.get("slug")


def current_user_id():
    return ss.get("uid")


def logout():
    ss.clear()
    st.rerun()


def _login_screen():
    apply_theme()
    st.markdown("<style>[data-testid='stSidebar'],[data-testid='collapsedControl'],"
                "[data-testid='stSidebarCollapsedControl']{display:none}</style>", unsafe_allow_html=True)
    _, mid, _ = st.columns([1, 1.3, 1])
    with mid:
        st.markdown("<h1 style='font-family:Newsreader,serif !important;margin-top:8vh'>Studio</h1>", unsafe_allow_html=True)
        tabs = st.tabs(["Sign in", "Create account"] if _registration_open() else ["Sign in"])
        with tabs[0]:
            with st.form("login_form", border=True):
                email = st.text_input("Email", autocomplete="email")
                pw = st.text_input("Password", type="password", autocomplete="current-password")
                if st.form_submit_button("Sign in", type="primary", use_container_width=True):
                    err = login(email, pw)
                    st.error(err) if err else st.rerun()
        if _registration_open():
            with tabs[1]:
                with st.form("register_form", border=True):
                    name = st.text_input("Your name")
                    email = st.text_input("Email", key="reg_email")
                    pw = st.text_input("Password", type="password", key="reg_pw", help="At least 8 characters.")
                    pw2 = st.text_input("Confirm password", type="password", key="reg_pw2")
                    invite = st.text_input("Invite code", value=st.query_params.get("invite", ""), key="reg_invite") \
                        if _mode() == "invite" else None
                    if st.form_submit_button("Create account", type="primary", use_container_width=True):
                        err = register(name, email, pw, pw2, invite)
                        st.error(err) if err else st.rerun()
    st.stop()


def require_login():
    """Call at the top of every page (after set_page_config). Shows sign in / register when logged out."""
    if not ss.get("uid"):
        _login_screen()
    with st.sidebar:
        st.markdown(f"<div style='color:#c9d3cd;font-size:13px;padding:0 4px'>{ss.get('user_name') or ss.get('user_email')}</div>",
                    unsafe_allow_html=True)
        site = secret("SITE_URL", "")
        if site and ss.get("user_slug"):
            st.markdown(f"<a href='{site.rstrip('/')}/u/{ss['user_slug']}' target='_blank' style='font-size:13px;padding:0 4px'>View site</a>",
                        unsafe_allow_html=True)
        if st.button("Sign out", key="signout"):
            logout()
