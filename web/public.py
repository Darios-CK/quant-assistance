"""Public pages: start, data, community, reports, the analysis tools and the legal pages."""

from __future__ import annotations

import re

import streamlit as st

from qa import catalog, commands, data, legal, regimes, workspace
from qa.cache import ROOT
from qa.sources.prices import ALIASES, FUTURES
from web import ui

AUTO = ROOT / "reports" / "auto"

WORKFLOWS = [
    ("Was machte der Markt vor meinen Einstiegen?", "Eigene Trades als CSV ins Projekt laden: Verlauf vor und nach jedem Einstieg, "
     "verglichen mit normalen Tagen, dazu die Marktphase.", "/trades trades_vorlage.csv"),
    ("Gewinn und Verlust nach Marktregime", "Wie verdient eine Strategie bei hohem VIX, im Abwärtstrend, bei inverser Zinskurve?",
     "/regime-pnl trend_dax.json"),
    ("Über Nacht vs. Handelszeit", "Wo entsteht die Rendite: zwischen Schluss und Eröffnung oder während des Handels?", "/overnight es"),
    ("Optionsrecherche", "Aktuelle Optionskette mit Geld/Brief, offenen Kontrakten und impliziter Volatilität.", "/optionen SPY"),
    ("Walk-Forward quartalsweise", "2 Jahre Entwicklung, 6 Monate Test, jedes Quartal neu gewählt – mit Sharpe-Verfall.",
     "/walk-forward trend_dax.json is=24 oos=6 schritt=3"),
    ("EZB-Überraschung bei hohem VIX", "Kombination zweier Muster: Reaktion von DAX, Bund-Renditen und Banken, nur wenn Angst im Markt ist.",
     "/ereignis ezb --bedingung vix_hoch --maerkte dax,bund2j,banken_eu"),
]


def _go_copilot(line: str) -> None:
    st.session_state["copilot_run"] = line
    st.switch_page(ui.PAGES["copilot"])


# ---------------------------------------------------------------- start
def start() -> None:
    st.markdown("""<div class="qa-hero">
<div class="qa-badge">Kostenlos · freie Marktdaten · jede Zahl gemessen</div>
<h1>Quant-Research von der Idee<br><span>bis zum ehrlichen Test</span></h1>
<p>Projekte, Copilot, Daten und Backtests in einer Umgebung – gebaut um den Research-Prozess:
Hypothese, Messung, Test, Verbesserung. Mit Kausalketten, Marktphasen und Kontrolle gegen Überanpassung.</p></div>""",
                unsafe_allow_html=True)
    c = st.columns([1, 1, 1, 1])
    c[1].page_link(ui.PAGES["copilot"], label="Copilot öffnen", icon=":material/bolt:", width="stretch")
    c[2].page_link(ui.PAGES["daten"], label="Daten ansehen", icon=":material/database:", width="stretch")

    st.markdown('<div class="qa-section">Beispiel-Workflows</div><div class="qa-sub">Ein Klick startet den Befehl im Copilot.</div>',
                unsafe_allow_html=True)
    for row in range(0, len(WORKFLOWS), 3):
        cols = st.columns(3)
        for col, (title, text, line) in zip(cols, WORKFLOWS[row:row + 3]):
            with col.container(border=True, height=210):
                st.markdown(f"**{title}**")
                st.markdown(f'<div class="qa-muted">{text}</div>', unsafe_allow_html=True)
                st.code(line, language=None)
                if st.button("Ausprobieren", key=f"wf_{line}"):
                    _go_copilot(line)

    st.markdown('<div class="qa-section">Drei Bereiche</div>', unsafe_allow_html=True)
    cols = st.columns(3)
    blocks = [
        ("Projekte", "projekte", "Virtuelles Dateisystem je Projekt: Strategien, Ketten, Trades, Skripte. Dateien direkt ausführen, "
         "jedes Ergebnis bleibt als Artefakt, Chats bleiben gespeichert."),
        ("Quant Copilot", "copilot", "Slash-Befehle für Analysen, Backtests, Walk-Forward, Review und Ziele – kostenlos. "
         "In Claude Code / der Claude-App denkt Claude mit denselben Werkzeugen frei mit."),
        ("Community", "community", "Veröffentlichte Projekte und Befehle ansehen und mit einem Klick ins eigene Konto übernehmen."),
    ]
    for col, (title, key, text) in zip(cols, blocks):
        with col.container(border=True, height=190):
            st.markdown(f"**{title}**")
            st.markdown(f'<div class="qa-muted">{text}</div>', unsafe_allow_html=True)
            st.page_link(ui.PAGES[key], label=f"Zu {title}", icon=":material/arrow_forward:")

    st.markdown('<div class="qa-section">Daten</div>', unsafe_allow_html=True)
    stats = [("ab 1927", "Tageskurse (S&P 500)"), (f"{len(FUTURES)}", "CME-Futures"), ("1 Min.", "Kerzen der letzten 30 Tage"),
             ("ALFRED", "Makro als Erstveröffentlichung"), ("EZB · Fed", "Zins-Überraschungen")]
    for col, (big, small) in zip(st.columns(len(stats)), stats):
        col.markdown(f'<div class="qa-stat"><b>{big}</b><span>{small}</span></div>', unsafe_allow_html=True)
    ui.footer()


# ---------------------------------------------------------------- data
COVER = [
    ("Kerzen", "1 Minute bis 1 Monat (Yahoo): Tag+ ganze Historie · 1m 30 Tage · 2m–90m 60 Tage · 1h 730 Tage", "✅"),
    ("Futures", f"{len(FUTURES)} CME-Märkte (Indizes, Zinsen, Energie, Metalle, Devisen, Agrar, Krypto), vorderster Kontrakt, ohne Roll-Bereinigung", "🟡"),
    ("US- und EU-Aktien, ETFs, Indizes", "Tageskurse bereinigt um Splits/Dividenden; delistete Firmen fehlen", "🟡"),
    ("Optionen", "aktuelle Ketten (Yahoo); keine Historie", "🟡"),
    ("Einzelne Trades, Quotes, Orderbuch", "gratis nicht verfügbar", "❌"),
    ("Zinsen und Makro", "FRED/ALFRED (Erstveröffentlichung), Bundesbank, EZB", "✅"),
    ("Zentralbank-Überraschungen", "EZB (EA-MPD), Fed (Bauer/Swanson)", "✅"),
    ("Quartalszahlen", "Termine und Konsens-Überraschung (Yahoo)", "✅"),
    ("SEC EDGAR (Insider, 13F, Bilanzen)", "geplant", "🔜"),
]


def daten() -> None:
    ui.header("Daten", "Was es gibt, was nicht – und alles zum Nachschlagen. Dieselben Funktionen gibt es als Befehle, für Claude (MCP) und in Python.")
    tabs = st.tabs(["Abdeckung", "Symbole", "Kerzen", "Optionen", "Futures", "Schemas", "Python & MCP", "Nutzung"])
    with tabs[0]:
        st.markdown("| Daten | Umfang | |\n|---|---|---|\n" + "\n".join(f"| {a} | {b} | {c} |" for a, b, c in COVER))
        st.caption("✅ vorhanden · 🟡 mit Einschränkung · 🔜 geplant · ❌ gratis nicht verfügbar. Quellen: Yahoo Finance, FRED/ALFRED, "
                   "Bundesbank, EZB, Federal Reserve Bank of San Francisco, EA-MPD.")
        sym = st.text_input("Abdeckung für ein Symbol", "es", key="cov_sym")
        if st.button("Prüfen", key="cov_go"):
            with st.spinner("Lade …"):
                c = data.coverage(sym)
            st.markdown("\n".join(f"- **{k}:** {v}" for k, v in c.items()))
    with tabs[1]:
        c1, c2 = st.columns([3, 1])
        q = c1.text_input("Suche", "siemens", key="s_q")
        art = c2.selectbox("Art", ["", *data.KINDS], key="s_art", format_func=lambda x: x or "alle")
        if q:
            with st.spinner("Suche …"):
                st.dataframe(data.search(q, art), width="stretch", hide_index=True)
    with tabs[2]:
        c1, c2, c3 = st.columns(3)
        sym = c1.text_input("Symbol", "nq", key="k_sym")
        iv = c2.selectbox("Intervall", list(data.INTERVALS), index=list(data.INTERVALS).index("1h"), key="k_iv")
        days = c3.number_input("Tage (max. 31)", 1, data.PREVIEW_MAX_DAYS, 5, key="k_days")
        if st.button("Laden", key="k_go", type="primary"):
            try:
                with st.spinner("Lade Kerzen …"):
                    df = data.preview_bars(sym, iv, int(days))
                st.line_chart(df["close"], height=300, color="#5cc8ff")
                st.dataframe(df, width="stretch")
                st.download_button("CSV", df.to_csv().encode("utf-8"), f"{sym}_{iv}.csv", "text/csv")
            except SystemExit as exc:
                st.error(str(exc))
        st.caption(f"Vorschau: höchstens {data.PREVIEW_MAX_BARS} Kerzen über {data.PREVIEW_MAX_DAYS} Tage. Mehr per Python im Projekt.")
    with tabs[3]:
        sym = st.text_input("Symbol", "SPY", key="o_sym")
        if st.button("Kette laden", key="o_go"):
            try:
                with st.spinner("Lade …"):
                    exp, calls, puts, _ = data.option_chain(sym)
                st.markdown(f"**Verfall {exp}** (aktueller Stand, verzögert)")
                a, b = st.columns(2)
                a.markdown("Calls")
                a.dataframe(calls, hide_index=True, width="stretch")
                b.markdown("Puts")
                b.dataframe(puts, hide_index=True, width="stretch")
            except SystemExit as exc:
                st.error(str(exc))
    with tabs[4]:
        st.dataframe([{"Kürzel": k, "Symbol": s, "Markt": n} for k, (s, n) in FUTURES.items()], hide_index=True, width="stretch")
        st.caption("Vorderster Kontrakt von Yahoo ohne Roll-Bereinigung: an Rolltagen springt der Kurs.")
        with st.expander("Alle Kürzel"):
            st.dataframe([{"Kürzel": k, "Symbol": s, "Name": n} for k, (s, n) in ALIASES.items()], hide_index=True, width="stretch")
    with tabs[5]:
        for name, (title, fields) in data.SCHEMAS.items():
            with st.expander(f"{name} – {title}"):
                st.markdown("\n".join(f"- **{k}:** {v}" for k, v in fields.items()))
    with tabs[6]:
        st.markdown("**In einem Python-Skript im Projekt** (`/ausfuehren skript.py`, lokal):")
        st.code(data.__doc__.split("\n\n")[1], language="python")
        st.markdown(data.GUIDE)
        st.markdown("**Claude verbinden (MCP, kostenlos im Claude-Abo):** einmal im Terminal")
        st.code('claude mcp add --scope user quant -- ~/quant-analyst/.venv/bin/python ~/quant-analyst/scripts/mcp_server.py', language="bash")
        st.caption("Dann in Claude Code fragen. Werkzeuge u. a.: symbole_suchen, abdeckung, symbol_aufloesen, schema_erklaeren, "
                   "nutzung, daten_anleitung, kerzen_vorschau, befehl, projekte, datei_lesen/-schreiben, merken, gedaechtnis.")
    with tabs[7]:
        st.markdown(commands.c_nutzung([], commands.Ctx()).text)
    ui.footer()


# ---------------------------------------------------------------- community
def community() -> None:
    ui.header("Community", "Veröffentlichte Projekte und Befehle. Übernehmen kopiert sie in dein Konto.")
    owner = ui.is_owner()
    try:
        projs, cmds = workspace.community_projects(), workspace.community_commands()
    except Exception as exc:
        st.error(f"Community nicht erreichbar: {exc}")
        return
    t1, t2 = st.tabs([f"Projekte ({len(projs)})", f"Befehle ({len(cmds)})"])
    com = workspace.community()
    with t1:
        if not projs:
            st.info("Noch nichts veröffentlicht. Eigene Projekte: Projekte → Veröffentlichen.")
        for name in projs:
            with st.container(border=True):
                files = [p.split("/", 2)[2] for p in com.list(f"projekte/{name}")]
                readme = com.read(f"projekte/{name}/README.md") or ""
                st.markdown(f"**{name}** · {len(files)} Dateien")
                if readme:
                    st.markdown(f'<div class="qa-muted">{readme.splitlines()[-1] if readme.strip() else ""}</div>', unsafe_allow_html=True)
                f = st.selectbox("Datei ansehen", ["–", *files], key=f"cf_{name}")
                if f != "–":
                    st.code(com.read(f"projekte/{name}/{f}") or "", language="json" if f.endswith(".json") else None)
                if owner:
                    target = st.text_input("Als Projekt", name, key=f"ct_{name}")
                    if st.button("Übernehmen", key=f"ci_{name}"):
                        try:
                            st.success(f"Übernommen als Projekt '{workspace.import_project(name, target)}'")
                        except SystemExit as exc:
                            st.error(str(exc))
    with t2:
        if not cmds:
            st.info("Noch keine veröffentlichten Befehle.")
        for name, cmd in sorted(cmds.items()):
            with st.container(border=True):
                st.markdown(f"**/{name}** – {cmd['beschreibung']}")
                st.code("\n".join(cmd["zeilen"]), language=None)
                if owner and st.button("Übernehmen", key=f"cc_{name}"):
                    try:
                        st.success(f"Gespeichert: {workspace.import_command(name)}")
                    except SystemExit as exc:
                        st.error(str(exc))
    if not owner:
        st.caption("Übernehmen und Veröffentlichen nach Anmeldung (Projekte).")
    ui.footer()


# ---------------------------------------------------------------- reports and tools
@st.cache_data(ttl=6 * 3600, show_spinner=False)
def _analyse(argv: tuple[str, ...]) -> tuple[str, bytes]:
    from qa.__main__ import run

    text, per_event, _ = run(list(argv))
    return text, per_event.to_csv(index=False).encode("utf-8")


def _show(argv: list[str], name: str) -> None:
    with st.spinner("Rechne … (beim ersten Mal werden Kurse geladen, das dauert etwas)"):
        try:
            text, csv = _analyse(tuple(argv))
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


def _markets(default: str, key: str) -> str:
    return st.text_input("Märkte (Kommaliste)", default, key=key,
                         help="Kürzel (siehe Daten → Futures/Alle Kürzel), jedes Yahoo-Symbol (z. B. SAP.DE) oder FRED:<Reihe>")


def _period(key: str) -> list[str]:
    c1, c2 = st.columns(2)
    von = c1.text_input("von (Jahr)", "", key=f"{key}_von")
    bis = c2.text_input("bis (Jahr)", "", key=f"{key}_bis")
    return (["--von", von] if von else []) + (["--bis", bis] if bis else [])


def berichte() -> None:
    ui.header("Berichte", "Werden jeden Werktag automatisch neu gerechnet (GitHub Actions).")
    index = AUTO / "README.md"
    if not index.exists():
        st.info("Noch keine automatischen Berichte.")
        return
    head = index.read_text(encoding="utf-8")
    stand = re.search(r"Stand: (.+)", head)
    st.caption(stand.group(1) if stand else "")
    titles = dict(re.findall(r"\[(.+?)\]\((\w+)\.md\)", head))
    for title, why in re.findall(r"^\| ([^\[|][^|]*) \| (fehlgeschlagen[^|]*) \|", head, re.M):
        st.warning(f"{title.strip()}: {why.strip()}")
    if titles:
        choice = st.selectbox("Bericht", list(titles))
        st.markdown((AUTO / f"{titles[choice]}.md").read_text(encoding="utf-8"))
    ui.footer()


def ereignis() -> None:
    ui.header("Ereignis-Analyse", "Wie reagierten Märkte auf Ereignisse – nach Größe der Überraschung, mit Fallzahl und Einordnung.")
    kind = st.selectbox("Ereignis", ["EZB-Sitzungen", "Fed-Sitzungen", "Kurs-Schock", "Konjunkturdaten (FRED)"])
    if kind == "EZB-Sitzungen":
        mass = st.selectbox("Überraschung", ["gesamt", "zins", "ausblick"])
        art = st.selectbox("Art", ["alle", "zins-schock", "info-schock"])
        argv = ["ereignis", "ezb", "--mass", mass, "--art", art]
        markets = _markets("bund2j,bund10j,dax,stoxx50,banken_eu,immobilien_eu,eurusd,deutsche_bank,vonovia", "m_ezb")
    elif kind == "Fed-Sitzungen":
        mass = st.selectbox("Überraschung", ["roh", "bereinigt"])
        art = st.selectbox("Art", ["alle", "zins-schock", "info-schock"])
        argv = ["ereignis", "fed", "--mass", mass, "--art", art]
        markets = _markets("sp500,nasdaq100,us2y,us10y,eurusd,gold,dax", "m_fed")
    elif kind == "Kurs-Schock":
        sym = st.text_input("Auslöser (Symbol)", "CL=F", help="z. B. CL=F (Öl), GC=F (Gold), ^VIX, BTC-USD, EURUSD=X")
        c1, c2 = st.columns(2)
        richtung = c1.selectbox("Richtung", ["hoch", "runter", "beide"])
        schwelle = c2.number_input("Schwelle (Standardabweichungen)", 1.5, 5.0, 2.0, 0.5)
        argv = ["ereignis", f"kurs:{sym}", "--richtung", richtung, "--schwelle", str(schwelle)]
        markets = _markets("sp500,dax,us10y,eurusd,gold,bitcoin", "m_kurs")
    else:
        series = st.text_input("FRED-Reihe", "PPIFIS", help="z. B. PPIFIS (Erzeugerpreise), CPIAUCSL (Verbraucherpreise), PAYEMS (Beschäftigte)")
        methode = st.selectbox("Überraschung", ["naiv", "veraenderung"])
        argv = ["ereignis", f"fred:{series}", "--methode", methode]
        markets = _markets("sp500,us2y,us10y,eurusd,gold,dax", "m_fred")
    phases = st.multiselect("Nur in Marktphase (Kombination)", list(regimes.PHASES))
    argv += ["--maerkte", markets] + _period("e") + (["--bedingung", ",".join(phases)] if phases else [])
    if st.button("Rechnen", type="primary"):
        _show(argv, "ereignis")
    ui.footer()


def _json_tool(folder: str, title: str, sub: str, cmd: str, label: str) -> None:
    ui.header(title, sub)
    files = sorted((ROOT / folder).glob("*.json"))
    choice = st.selectbox("Vorlage", [f.name for f in files])
    text = st.text_area("Datei (anpassbar)", (ROOT / folder / choice).read_text(encoding="utf-8"), height=360)
    if st.button(label, type="primary"):
        tmp = ROOT / "data" / f"web_{cmd}.json"
        tmp.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_text(text, encoding="utf-8")
        _show([cmd, str(tmp)], cmd)
    ui.footer()


def kette() -> None:
    _json_tool("chains", "Kette prüfen", "Auslöser und Glieder mit erwarteter Richtung und Begründung – jedes Glied wird gegen den Auslöser gemessen.",
               "kette", "Prüfen")


def backtest() -> None:
    _json_tool("strategies", "Backtest", "Parameter nur auf Daten vor 'holdout_ab' gewählt; Deflated Sharpe und PBO zählen alle Varianten.",
               "backtest", "Testen")


def earnings() -> None:
    ui.header("Quartalszahlen", "Eine Firma: Reaktion der Aktie (und weiterer Märkte). Mehrere Firmen: Muster über alle zusammen.")
    tickers = st.text_input("Ticker (Kommaliste)", "AAPL,MSFT,GOOGL,AMZN")
    extra = st.text_input("Weitere Märkte (nur bei einer Firma)", "", help="z. B. AMD,TSM,bitcoin")
    argv = ["earnings", tickers] + (["--maerkte", extra] if extra and "," not in tickers else []) + _period("g")
    if st.button("Rechnen", type="primary"):
        _show(argv, "earnings")
    ui.footer()


def abdeckung() -> None:
    st.markdown(catalog.as_markdown())
    ui.footer()


def impressum() -> None:
    gaps = legal.missing(ui.secrets())
    if gaps:
        st.warning("Betreiberangaben fehlen noch: " + ", ".join(gaps) + ". Eintragen unter App settings → Secrets.")
    st.markdown(legal.impressum(ui.secrets()))


def datenschutz() -> None:
    st.markdown(legal.privacy(ui.secrets()))
