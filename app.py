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

try:                                    # cloud: keys live in Streamlit's secrets, locally in .env
    for _k in ("FRED_API_KEY", "ANTHROPIC_API_KEY"):
        if _k in st.secrets:
            os.environ[_k] = st.secrets[_k]
except Exception:
    pass

from datetime import date                 # noqa: E402

from qa import catalog, legal             # noqa: E402
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


page = st.sidebar.radio("Bereich", ["KI-Analyst", "Berichte", "Ereignis-Analyse", "Kette prüfen", "Quartalszahlen", "Backtest",
                                   "Abdeckung", "Impressum", "Datenschutz"])
st.sidebar.caption("Testbetrieb. Nur gemessene Werte aus der Vergangenheit, keine Anlageberatung. "
                   "Daten: Yahoo Finance, FRED/ALFRED, Bundesbank, EZB, SF Fed.")

CHAT_LIMIT = int(os.getenv("QA_CHAT_LIMIT", "30"))     # questions per day for the whole app (it is public, every question costs money)
EXAMPLES = [
    "Ölpreis steigt an einem Tag stark: Wer reagiert – direkt, über Transport und Reifen, über Währungen und Krypto?",
    "Wie reagieren Bund-Renditen, DAX-Banken und Vonovia auf harte EZB-Überraschungen – und ist das anders, wenn der VIX hoch ist?",
    "Schlagen Microsoft, Apple und Nvidia den Konsens: steigt die Aktie danach über Wochen weiter (Post-Earnings-Drift)?",
    "Was passierte historisch mit S&P 500 und DAX, wenn der S&P unter seine 200-Tage-Linie fiel – in einer Lage wie heute?",
]


@st.cache_resource
def _counter() -> dict:
    return {}


def _chat_allowed() -> tuple[bool, str]:
    from qa import agent

    ok, why = agent.available()
    if not ok:
        return False, why
    password = str(secrets().get("CHAT_PASSWORD", "") or "")
    if not password:
        return False, ("Der Chat ist gesperrt, bis ein Passwort gesetzt ist (CHAT_PASSWORD in den Secrets) – "
                       "die App ist öffentlich und jede Frage kostet über den API-Schlüssel Geld.")
    if st.session_state.get("chat_ok"):
        return True, ""
    entered = st.text_input("Passwort für den KI-Analysten", type="password")
    if entered and entered == password:
        st.session_state["chat_ok"] = True
        st.rerun()
    if entered:
        st.error("Falsches Passwort.")
    return False, ""


if page == "KI-Analyst":
    st.title("KI-Analyst")
    st.caption("Fragen in eigenen Worten. Die KI denkt die Kette weit durch und prüft jede Aussage mit den Analysen dieser App – "
               "Zahlen stammen nur aus Messungen. Keine Anlageberatung. Antworten werden von einer KI erzeugt (Claude, Anthropic).")
    allowed, why = _chat_allowed()
    if why:
        st.info(why)
    if allowed:
        from qa import agent

        used = _counter().get(str(date.today()), 0)
        st.session_state.setdefault("chat_messages", [])
        st.session_state.setdefault("chat_view", [])
        for entry in st.session_state["chat_view"]:
            with st.chat_message(entry["role"]):
                for step in entry.get("steps", []):
                    with st.expander(f"{'⚠️' if step['err'] else '🔧'} {step['name']}: {step['short']}"):
                        st.markdown(step["out"])
                st.markdown(entry["text"])
                if entry.get("usage"):
                    st.caption(entry["usage"])
        cols = st.columns(2)
        clicked = None
        if not st.session_state["chat_view"]:
            for k, ex in enumerate(EXAMPLES):
                if cols[k % 2].button(ex, key=f"ex{k}"):
                    clicked = ex
        question = st.chat_input(f"Frage stellen ({max(0, CHAT_LIMIT - used)} von {CHAT_LIMIT} heute übrig)") or clicked
        if question:
            if used >= CHAT_LIMIT:
                st.warning("Tageslimit erreicht – morgen geht es weiter.")
            else:
                _counter()[str(date.today())] = used + 1
                st.session_state["chat_view"].append({"role": "user", "text": question})
                with st.chat_message("user"):
                    st.markdown(question)
                with st.chat_message("assistant"):
                    steps = []
                    status = st.status("Denke nach und rechne …", expanded=True)

                    def on_step(name, i, out, err):
                        short = i.get("quelle") or i.get("ticker") or (i.get("kette") or {}).get("name") or \
                            (i.get("strategie") or {}).get("name") or i.get("symbole") or ""
                        steps.append({"name": name, "short": str(short)[:80], "out": out, "err": err})
                        status.write(f"{'⚠️' if err else '🔧'} {name}: {str(short)[:80]}")

                    try:
                        text, msgs, usage = agent.ask(question, st.session_state["chat_messages"], on_step)
                        st.session_state["chat_messages"] = msgs
                        line = f"{usage['steps']} Analysen · ca. {usage['cost_usd']:.2f} $"
                    except Exception as exc:
                        text, line = f"Fehler beim KI-Aufruf: {exc}", ""
                    status.update(label=f"Fertig – {len(steps)} Analysen", state="complete", expanded=False)
                    st.markdown(text)
                    if line:
                        st.caption(line)
                st.session_state["chat_view"].append({"role": "assistant", "text": text, "steps": steps, "usage": line})
        if st.session_state["chat_view"] and st.button("Neues Gespräch"):
            st.session_state["chat_messages"], st.session_state["chat_view"] = [], []
            st.rerun()

elif page == "Abdeckung":
    st.markdown(catalog.as_markdown())

elif page == "Berichte":
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
