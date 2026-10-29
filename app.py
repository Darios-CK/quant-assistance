"""Web interface (Streamlit): read the daily reports and start analyses in the browser.

Local:  .venv/bin/streamlit run app.py
Cloud:  Streamlit Community Cloud, main file app.py; FRED key under Settings → Secrets as FRED_API_KEY = "…".
"""

from __future__ import annotations

import os
import re
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
AUTO = ROOT / "reports" / "auto"

try:                                    # cloud: the key lives in Streamlit's secrets, locally in .env
    if "FRED_API_KEY" in st.secrets:
        os.environ["FRED_API_KEY"] = st.secrets["FRED_API_KEY"]
except Exception:
    pass

from qa import legal                 # noqa: E402
from qa.__main__ import run          # noqa: E402  (after the key is in the environment)
from qa.sources.prices import ALIASES  # noqa: E402

st.set_page_config(page_title="Quant-Analyst", page_icon="📈", layout="wide")


@st.cache_data(ttl=6 * 3600, show_spinner=False)
def analyse(argv: tuple[str, ...]) -> tuple[str, bytes]:
    text, per_event, _ = run(list(argv))
    return text, per_event.to_csv(index=False).encode("utf-8")


def show(argv: list[str], name: str) -> None:
    with st.spinner("Rechne … (beim ersten Mal werden Kurse geladen, das dauert etwas)"):
        try:
            text, csv = analyse(tuple(argv))
        except SystemExit as exc:
            st.error(str(exc))
            return
        except Exception as exc:
            st.error(f"Analyse fehlgeschlagen: {exc}")
            return
    st.caption("Befehl: `python -m qa " + " ".join(argv) + "`")
    c1, c2 = st.columns(2)
    c1.download_button("Bericht (Markdown)", text, f"{name}.md", "text/markdown")
    c2.download_button("Jedes Ereignis (CSV)", csv, f"{name}.csv", "text/csv")
    st.markdown(text)


def markets_input(default: str, key: str) -> str:
    return st.text_input("Märkte (Kommaliste)", default, key=key,
                         help="Kürzel (" + ", ".join(ALIASES) + "), jedes Yahoo-Symbol (z. B. SAP.DE) oder FRED:<Reihe>")


def period(key: str) -> list[str]:
    c1, c2 = st.columns(2)
    von = c1.text_input("von (Jahr)", "", key=f"{key}_von")
    bis = c2.text_input("bis (Jahr)", "", key=f"{key}_bis")
    return (["--von", von] if von else []) + (["--bis", bis] if bis else [])


def secrets():
    try:
        return st.secrets
    except Exception:
        return {}


page = st.sidebar.radio("Bereich", ["Berichte", "Ereignis-Analyse", "Kette prüfen", "Quartalszahlen", "Backtest", "Impressum", "Datenschutz"])
st.sidebar.caption("Testbetrieb. Nur gemessene Werte aus der Vergangenheit, keine Anlageberatung. "
                   "Daten: Yahoo Finance, FRED/ALFRED, Bundesbank, EZB, SF Fed.")

if page == "Berichte":
    st.title("Automatische Berichte")
    index = AUTO / "README.md"
    if not index.exists():
        st.info("Noch keine automatischen Berichte. Sie entstehen beim täglichen Lauf (`python -m qa routine`).")
    else:
        head = index.read_text(encoding="utf-8")
        stand = re.search(r"Stand: (.+)", head)
        st.caption(stand.group(1) if stand else "")
        titles = dict(re.findall(r"\[(.+?)\]\((\w+)\.md\)", head))
        failed = re.findall(r"^\| ([^\[|][^|]*) \| (fehlgeschlagen[^|]*) \|", head, re.M)
        for title, why in failed:
            st.warning(f"{title.strip()}: {why.strip()}")
        if titles:
            choice = st.selectbox("Bericht", list(titles))
            st.markdown((AUTO / f"{titles[choice]}.md").read_text(encoding="utf-8"))

elif page == "Ereignis-Analyse":
    st.title("Ereignis-Analyse")
    kind = st.selectbox("Ereignis", ["EZB-Sitzungen", "Fed-Sitzungen", "Kurs-Schock", "Konjunkturdaten (FRED)"])
    argv: list[str]
    if kind == "EZB-Sitzungen":
        mass = st.selectbox("Überraschung", ["gesamt", "zins", "ausblick"])
        art = st.selectbox("Art", ["alle", "zins-schock", "info-schock"])
        argv = ["ereignis", "ezb", "--mass", mass, "--art", art]
        markets = markets_input("dax,stoxx50,banken_eu,immobilien_eu,eurusd,deutsche_bank,vonovia", "m_ezb")
    elif kind == "Fed-Sitzungen":
        mass = st.selectbox("Überraschung", ["roh", "bereinigt"])
        art = st.selectbox("Art", ["alle", "zins-schock", "info-schock"])
        argv = ["ereignis", "fed", "--mass", mass, "--art", art]
        markets = markets_input("sp500,nasdaq100,us2y,us10y,eurusd,gold,dax", "m_fed")
    elif kind == "Kurs-Schock":
        sym = st.text_input("Auslöser (Symbol)", "CL=F", help="z. B. CL=F (Öl), GC=F (Gold), ^VIX, BTC-USD, EURUSD=X")
        c1, c2 = st.columns(2)
        richtung = c1.selectbox("Richtung", ["hoch", "runter", "beide"])
        schwelle = c2.number_input("Schwelle (Standardabweichungen)", 1.5, 5.0, 2.0, 0.5)
        argv = ["ereignis", f"kurs:{sym}", "--richtung", richtung, "--schwelle", str(schwelle)]
        markets = markets_input("sp500,dax,us10y,eurusd,gold,bitcoin", "m_kurs")
    else:
        series = st.text_input("FRED-Reihe", "PPIFIS", help="z. B. PPIFIS (Erzeugerpreise), CPIAUCSL (Verbraucherpreise), PAYEMS (Beschäftigte)")
        methode = st.selectbox("Überraschung", ["naiv", "veraenderung"])
        argv = ["ereignis", f"fred:{series}", "--methode", methode]
        markets = markets_input("sp500,us2y,us10y,eurusd,gold,dax", "m_fred")
    argv += ["--maerkte", markets] + period("e")
    if st.button("Rechnen", type="primary"):
        show(argv, "ereignis")

elif page == "Kette prüfen":
    st.title("Kette prüfen")
    st.caption("Kette als JSON: Auslöser und Glieder mit erwarteter Richtung und Begründung. Jedes Glied wird gegen den Auslöser gemessen.")
    files = sorted((ROOT / "chains").glob("*.json"))
    choice = st.selectbox("Vorlage", [f.name for f in files])
    text = st.text_area("Kette (anpassbar)", (ROOT / "chains" / choice).read_text(encoding="utf-8"), height=380)
    if st.button("Prüfen", type="primary"):
        tmp = ROOT / "data" / "web_kette.json"
        tmp.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_text(text, encoding="utf-8")
        show(["kette", str(tmp)], "kette")

elif page == "Backtest":
    st.title("Backtest")
    st.caption("Regel als JSON. Parameter werden nur auf den Daten vor 'holdout_ab' gewählt; danach zählt der Testzeitraum. "
               "Deflated Sharpe und PBO berücksichtigen, wie viele Varianten probiert wurden.")
    files = sorted((ROOT / "strategies").glob("*.json"))
    choice = st.selectbox("Vorlage", [f.name for f in files])
    text = st.text_area("Strategie (anpassbar)", (ROOT / "strategies" / choice).read_text(encoding="utf-8"), height=320)
    if st.button("Testen", type="primary"):
        tmp = ROOT / "data" / "web_strategie.json"
        tmp.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_text(text, encoding="utf-8")
        show(["backtest", str(tmp)], "backtest")

elif page == "Impressum":
    gaps = legal.missing(secrets())
    if gaps:
        st.warning("Betreiberangaben fehlen noch: " + ", ".join(gaps) + ". Eintragen unter App settings → Secrets (Vorlage: .streamlit/secrets.example.toml).")
    st.markdown(legal.impressum(secrets()))

elif page == "Datenschutz":
    st.markdown(legal.privacy(secrets()))

else:
    st.title("Quartalszahlen")
    st.caption("Eine Firma: Reaktion der Aktie (und weiterer Märkte) auf ihre Zahlen. Mehrere Firmen: Muster über alle zusammen.")
    tickers = st.text_input("Ticker (Kommaliste)", "AAPL,MSFT,GOOGL,AMZN")
    extra = st.text_input("Weitere Märkte (nur bei einer Firma)", "", help="z. B. AMD,TSM,bitcoin")
    argv = ["earnings", tickers] + (["--maerkte", extra] if extra and "," not in tickers else []) + period("g")
    if st.button("Rechnen", type="primary"):
        show(argv, "earnings")
