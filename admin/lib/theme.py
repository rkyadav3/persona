"""Visual layer that mirrors the EJS admin ("Studio"): cards, stat tiles, pills, breadcrumbs, table headers."""
import html

import streamlit as st

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Figtree:wght@400;500;600&family=Newsreader:wght@500;600&display=swap');
html, body, [class*="css"] { font-family: 'Figtree', system-ui, sans-serif; }
h1, h2, h3 { font-family: 'Newsreader', Georgia, serif !important; color: #1b2a2f; letter-spacing: -0.01em; }
.block-container { padding-top: 2rem; max-width: 1200px; }
[data-testid="stVerticalBlockBorderWrapper"] { background: #fff; border-radius: 12px; border-color: #e3e0d6; }
.stButton > button, .stDownloadButton > button,
[data-testid="stLinkButton"] a, [data-testid="stPageLink"] a { border-radius: 8px; }
.stats { display: flex; gap: 14px; flex-wrap: wrap; margin: 8px 0 20px; }
.stat { background: #fff; border: 1px solid #e3e0d6; border-radius: 12px; padding: 16px 24px; min-width: 180px; }
.stat b { font-family: 'Newsreader', Georgia, serif; font-size: 2.1rem; margin-right: 6px; }
.stat small { display: block; color: #6b7a7e; margin-top: 2px; }
.crumbs { color: #6b7a7e; font-size: .92rem; margin: 2px 0 14px; }
.crumbs b { color: #1b2a2f; font-weight: 600; }
.pill { display: inline-block; padding: 2px 10px; border-radius: 999px; font-size: .78rem; font-weight: 600; }
.pill.published { background: #dff2e4; color: #1d6b3a; }
.pill.draft { background: #fdf0c9; color: #8a6410; }
.muted { color: #6b7a7e; }
.th { color: #6b7a7e; font-size: .75rem; text-transform: uppercase; letter-spacing: .06em;
      border-bottom: 1px solid #e3e0d6; padding-bottom: 6px; }
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
