"""Shared look and helpers of the website: styles, login of the owner, result display."""

from __future__ import annotations

import os

import streamlit as st

from qa import commands, workspace

BRAND = "Quant Assistance"
PAGES: dict = {}                                   # filled by app.py: key -> st.Page, for switch_page

CSS = """
<style>
:root { --accent:#5cc8ff; --accent2:#a8e6ff; --line:rgba(140,190,255,.15); --muted:#94a6c2; }
.stApp { background: radial-gradient(1100px 480px at 50% -140px, rgba(92,200,255,.18), transparent 70%), #0b1220; }
.block-container { max-width: 1180px; padding-top: 4.5rem; }
h1, h2, h3 { letter-spacing: -.02em; }
.qa-hero { text-align:center; padding: 40px 0 10px; }
.qa-hero h1 { font-size: 3.2rem; line-height: 1.07; margin: 0 0 16px; font-weight: 700; }
.qa-hero h1 span { background: linear-gradient(90deg,#5cc8ff,#b3ecff); -webkit-background-clip:text; background-clip:text; color:transparent; }
.qa-hero p { color: var(--muted); font-size: 1.12rem; max-width: 760px; margin: 0 auto; }
.qa-badge { display:inline-block; border:1px solid var(--line); border-radius:999px; padding:4px 13px; color:#a8e6ff;
            font-size:.8rem; margin-bottom:18px; background:rgba(92,200,255,.07); }
.qa-section { margin: 46px 0 6px; font-size: 1.55rem; font-weight: 680; letter-spacing:-.02em; }
.qa-sub { color: var(--muted); margin-bottom: 16px; }
.qa-stat { border:1px solid var(--line); border-radius:14px; padding:16px 10px; text-align:center; background:rgba(18,29,49,.65); }
.qa-stat b { display:block; font-size:1.45rem; color:#5cc8ff; }
.qa-stat span { color: var(--muted); font-size:.84rem; }
.qa-muted { color: var(--muted); font-size: .86rem; }
.qa-footer { border-top:1px solid var(--line); margin-top:56px; padding-top:16px; color:#7f8ea6; font-size:.8rem; text-align:center; }
div[data-testid="stVerticalBlockBorderWrapper"] { border-color: var(--line) !important; border-radius: 14px !important;
            background: linear-gradient(180deg, rgba(92,200,255,.05), rgba(18,29,49,.55)); }
div[data-testid="stChatMessage"] { background: rgba(18,29,49,.55); border:1px solid var(--line); border-radius:14px; }
.stButton > button, .stDownloadButton > button, a[data-testid="stPageLink-NavLink"] { border-radius: 10px; }
code { color: #a8e6ff; }
</style>
"""


def style() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def secrets():
    try:
        return st.secrets
    except Exception:
        return {}


def footer() -> None:
    st.markdown(f'<div class="qa-footer">{BRAND} · Testbetrieb · Nur gemessene Werte aus der Vergangenheit, keine Anlageberatung · '
                'Daten: Yahoo Finance, FRED/ALFRED, Bundesbank, EZB, SF Fed</div>', unsafe_allow_html=True)


def header(title: str, sub: str = "") -> None:
    st.markdown(f"## {title}")
    if sub:
        st.markdown(f'<div class="qa-sub">{sub}</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------- owner login
def _password() -> str:
    try:
        s = secrets()
        pw = s.get("APP_PASSWORD", "") or s.get("CHAT_PASSWORD", "")
    except Exception:                                  # no secrets file at all
        pw = ""
    return str(pw or os.getenv("APP_PASSWORD", ""))


def is_owner() -> bool:
    """Locally you are always the owner; on the public website only after entering APP_PASSWORD."""
    return not commands.is_cloud() or bool(st.session_state.get("owner"))


def require_owner(what: str) -> None:
    if is_owner():
        workspace_ready()
        return
    st.markdown(f"## {what}")
    pw = _password()
    if not pw:
        st.info("Dieser Bereich ist persönlich (Projekte, Gedächtnis, eigene Befehle) und auf der öffentlichen Website gesperrt, "
                "bis ein Passwort gesetzt ist: Streamlit → App settings → Secrets → `APP_PASSWORD = \"…\"`. "
                "Lokal (`streamlit run app.py`) und in Claude Code ist er sofort nutzbar.")
        st.stop()
    with st.form("login"):
        entered = st.text_input("Passwort", type="password")
        if st.form_submit_button("Anmelden", type="primary"):
            if entered == pw:
                st.session_state["owner"] = True
                st.rerun()
            st.error("Falsches Passwort.")
    st.stop()


def workspace_ready() -> None:
    if not st.session_state.get("seeded"):
        try:
            workspace.seed()
        except Exception as exc:
            st.warning(f"Speicher nicht erreichbar: {exc}")
        st.session_state["seeded"] = True
    if commands.is_cloud() and workspace.store().kind == "lokal":
        st.warning("Projekte liegen gerade nur auf dem Streamlit-Server und gehen beim nächsten Neustart verloren. Dauerhaft: "
                   "privates GitHub-Repository als Speicher eintragen (Konto → Verbindung).", icon="⚠️")


# ---------------------------------------------------------------- results
def show_result(res: commands.Result, key: str) -> None:
    if not res.ok:
        st.error(res.text.strip())
        return
    if res.chart is not None and len(res.chart):
        st.line_chart(res.chart, height=280, color=["#5cc8ff", "#7f8ea6"][:res.chart.shape[1]] if res.chart.shape[1] <= 2 else None)
    st.markdown(res.text)
    cols = st.columns(3)
    cols[0].download_button("Bericht (.md)", res.text, f"{res.title}.md", "text/markdown", key=f"md_{key}")
    if res.table is not None and len(res.table):
        cols[1].download_button("Daten (.csv)", res.table.to_csv(index=False).encode("utf-8"), f"{res.title}.csv", "text/csv", key=f"csv_{key}")
    if res.artifact:
        cols[2].caption(f"Gespeichert: {res.artifact}")
