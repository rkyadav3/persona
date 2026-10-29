"""Visual layer that mirrors the EJS admin ("Studio"): cards, stat tiles, pills, breadcrumbs, table headers."""
import html

import streamlit as st

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Figtree:wght@400;500;600;700&family=Newsreader:wght@600&display=swap');
:root { --bg:#eceee9; --panel:#f8f9f6; --ink:#1b2a2f; --muted:#66767a; --line:#d5dad4; --accent:#2f6f62; --danger:#a23b32; --r:6px; }
html, body, [class*="css"] { font-family: Figtree, system-ui, sans-serif; font-size: 15px; }
.stApp { background: var(--bg); color: var(--ink); }
.block-container { padding: 28px 36px; max-width: 1300px; }
h1 { font: 700 26px Figtree, sans-serif !important; margin: 0 0 16px; padding: 0; color: var(--ink); }
h2, h3 { font: 600 16px Figtree, sans-serif !important; color: var(--ink); padding: 0; }
a { color: var(--accent); }

/* sidebar = the dark "Studio" rail */
[data-testid="stSidebar"] { background: var(--ink); width: 210px !important; min-width: 210px !important; }
[data-testid="stSidebarNav"]::before { content: "Studio"; display: block; font: 600 22px Newsreader, serif; color: #fff; padding: 22px 16px 14px; }
[data-testid="stSidebarNav"] a { border-radius: var(--r); color: #c9d3cd; }
[data-testid="stSidebarNav"] a span { color: inherit !important; }
[data-testid="stSidebarNav"] a:hover, [data-testid="stSidebarNav"] a[aria-current="page"] { background: #2a3d43; color: #fff; }
[data-testid="stSidebar"] .stButton > button { background: transparent; color: #9fb3ab; border: 1px solid #2a3d43; }
[data-testid="stSidebar"] hr { border-color: #2a3d43; }

/* cards, buttons, inputs */
[data-testid="stVerticalBlockBorderWrapper"] { background: var(--panel); border: 1px solid var(--line); border-radius: var(--r); }
.stButton > button, .stDownloadButton > button, [data-testid="stLinkButton"] a, [data-testid="stPageLink"] a {
  border-radius: var(--r); border: 1px solid var(--line); background: #fff; color: var(--ink); font-weight: 500; font-size: 14px; }
.stButton > button:hover, [data-testid="stPageLink"] a:hover { background: #f0f3ee; border-color: var(--line); color: var(--ink); }
.stButton > button[kind="primary"] { background: var(--accent); border-color: var(--accent); color: #fff; }
.stButton > button { justify-content: flex-start; text-align: left; min-height: 2.3rem; }
.stButton > button p { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
[data-baseweb="input"], [data-baseweb="textarea"], [data-baseweb="select"] > div { border-radius: var(--r) !important; border-color: var(--line) !important; background: #fff !important; }
[data-testid="stWidgetLabel"] p { font-size: 13px; color: var(--muted); }

/* stat tiles, pills, crumbs, table head */
.stats { display: flex; gap: 14px; flex-wrap: wrap; margin: 8px 0 18px; }
.stat { background: var(--panel); border: 1px solid var(--line); border-radius: var(--r); padding: 14px 20px; }
.stat b { font-size: 28px; margin-right: 6px; }
.stat small { display: block; color: var(--muted); }
.crumbs { color: var(--muted); margin: 0 0 12px; }
.crumbs b { color: var(--ink); font-weight: 500; }
.pill { display: inline-block; white-space: nowrap; font-size: 12px; padding: 2px 8px; border-radius: 99px; background: #dde5df; }
.pill.draft { background: #f1e4c3; }
.muted { color: var(--muted); }
.th { font-size: 13px; color: var(--muted); font-weight: 500; border-bottom: 1px solid var(--line); padding: 4px 0 8px; }
</style>
"""


def apply_theme():
    st.markdown(_CSS, unsafe_allow_html=True)


def esc(s):
    return html.escape(str(s if s is not None else ""))


def pill(status):
    return f'<span class="pill {esc(status)}">{esc(status)}</span>'


def stats(items):
    """items: list of (number, label, sub_label_or_None)."""
    tiles = "".join(
        f'<div class="stat"><b>{esc(n)}</b>{esc(label)}' + (f"<small>{esc(sub)}</small>" if sub else "") + "</div>"
        for n, label, sub in items
    )
    st.markdown(f'<div class="stats">{tiles}</div>', unsafe_allow_html=True)


def crumbs(*parts):
    """Plain-text breadcrumb line; the last part is emphasised."""
    out = [esc(p) for p in parts]
    if out:
        out[-1] = f"<b>{out[-1]}</b>"
    st.markdown(f'<div class="crumbs">{" / ".join(out)}</div>', unsafe_allow_html=True)


def table_header(labels, weights):
    for col, label in zip(st.columns(weights), labels):
        col.markdown(f'<div class="th">{esc(label)}</div>', unsafe_allow_html=True)
