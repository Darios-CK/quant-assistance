"""Website (Streamlit): Quant Assistance – projects, Copilot, data, community, reports and the analysis tools.

Local:  .venv/bin/streamlit run app.py       (you are the owner: projects, Copilot and account open without a password)
Cloud:  Streamlit Community Cloud, main file app.py.  Secrets: APP_PASSWORD (personal area), optional GITHUB_TOKEN +
        WORKSPACE_REPO (lasting storage), FRED_API_KEY, ANTHROPIC_API_KEY (paid AI answers), [impressum], [privacy].
"""

from __future__ import annotations

import os

import streamlit as st

try:                                    # cloud: keys live in Streamlit's secrets, locally in .env
    for _k in ("FRED_API_KEY", "ANTHROPIC_API_KEY", "GITHUB_TOKEN", "WORKSPACE_REPO", "COMMUNITY_REPO"):
        if _k in st.secrets:
            os.environ[_k] = str(st.secrets[_k])
except Exception:
    pass

from web import public, ui, workbench   # noqa: E402  (after the keys are in the environment)

st.set_page_config(page_title=ui.BRAND, page_icon=":material/insights:", layout="wide")
ui.style()

ui.PAGES.update({
    "start": st.Page(public.start, title="Start", icon=":material/home:", url_path="start", default=True),
    "projekte": st.Page(workbench.projekte, title="Projekte", icon=":material/folder:", url_path="projekte"),
    "copilot": st.Page(workbench.copilot, title="Quant Copilot", icon=":material/bolt:", url_path="copilot"),
    "daten": st.Page(public.daten, title="Daten", icon=":material/database:", url_path="daten"),
    "community": st.Page(public.community, title="Community", icon=":material/groups:", url_path="community"),
    "berichte": st.Page(public.berichte, title="Berichte", icon=":material/article:", url_path="berichte"),
    "ereignis": st.Page(public.ereignis, title="Ereignis-Analyse", icon=":material/event:", url_path="ereignis"),
    "kette": st.Page(public.kette, title="Kette prüfen", icon=":material/account_tree:", url_path="kette"),
    "earnings": st.Page(public.earnings, title="Quartalszahlen", icon=":material/request_quote:", url_path="quartalszahlen"),
    "backtest": st.Page(public.backtest, title="Backtest", icon=":material/show_chart:", url_path="backtest"),
    "abdeckung": st.Page(public.abdeckung, title="Abdeckung", icon=":material/checklist:", url_path="abdeckung"),
    "konto": st.Page(workbench.konto, title="Konto", icon=":material/person:", url_path="konto"),
    "impressum": st.Page(public.impressum, title="Impressum", icon=":material/info:", url_path="impressum"),
    "datenschutz": st.Page(public.datenschutz, title="Datenschutz", icon=":material/shield:", url_path="datenschutz"),
})
P = ui.PAGES
nav = st.navigation({
    "": [P["start"], P["projekte"], P["copilot"], P["daten"], P["community"], P["berichte"]],
    "Werkzeuge": [P["ereignis"], P["kette"], P["earnings"], P["backtest"], P["abdeckung"]],
    "Konto": [P["konto"], P["impressum"], P["datenschutz"]],
}, position="top")
nav.run()
