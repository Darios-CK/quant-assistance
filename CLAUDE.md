# Quant Assistance (Quant-Analyst) – Regeln für jede Sitzung

Persönliches Forschungswerkzeug (nur Eigengebrauch) für Ereignis-Analysen auf freien Daten. Getrennt von PFMM.
Berichte an den Nutzer: **Deutsch**. Code, Kommentare, Commit-Messages: Englisch.

## Aufbau
- `qa/sources/` Datenquellen: `prices.py` (Yahoo, FRED-Tagesreihen ohne Schlüssel), `shocks.py` (EZB: EA-MPD, Fed: Bauer/Swanson), `fred.py` (ALFRED-Erstveröffentlichungen, braucht `FRED_API_KEY` in `.env`), `earnings.py` (Quartalszahlen mit Konsens), `moves.py` (Kurs-Schocks).
- `qa/triggers.py` eine Schreibweise für alle Auslöser (ezb, fed, fred:/makro:, earnings:, kurs:, technik:, kalender:, wahl:, split:, dividende:, termine:).
- `qa/regimes.py` Marktphasen als Bedingung (Stand am Schluss VOR dem Ereignis) und Kombinationen (`--bedingung`, `--zusammen-mit`, `--ohne`, `--fenster`).
- `qa/catalog.py` Abdeckung aller ~70 Markttreiber (✅/🟡/🔜/❌) – bei neuen Quellen nachführen.
- `scripts/mcp_server.py` dieselben Werkzeuge als MCP-Server für Claude Code / Claude-App (kostenlos im Abo, Anmeldung durch den Nutzer: README).
- `qa/agent.py` Werkzeugliste (Analysen, Befehle, Projekte, Gedächtnis, Daten) und System-Prompt für MCP und den optionalen API-Chat (Claude Opus 5.5, kostet je Frage Geld, ANTHROPIC_API_KEY; Stufe = effort).
- Website wie eine Research-Plattform (`app.py` + `web/`: `public.py` Start/Daten/Community/Berichte/Werkzeuge/Rechtliches, `workbench.py` Projekte/Copilot/Konto, `ui.py` Stil in Hellblau, Anmeldung). Online ist der persönliche Bereich nur mit `APP_PASSWORD` offen; lokal immer.
- `qa/workspace.py` Projekte (virtuelles Dateisystem), Chats, Artefakte, eigene Befehle (.md), Gedächtnis, Anweisungen, Community; `qa/store.py` Speicher lokal (`workspace/`, nicht in Git – persönlich) oder privates GitHub-Repository (`GITHUB_TOKEN` + `WORKSPACE_REPO`).
- `qa/commands.py` Slash-Befehle (eingebaut + eigene, `$1`…`$9`), jedes Ergebnis als Artefakt; `.py` nur lokal ausführen (`is_cloud`). `qa/workflows.py` Über Nacht vs. Handelszeit, P&L nach Marktphase, eigene Trades, rollierender Walk-Forward, `/review`, `/goal` (Ziel nur auf Entwicklungsdaten, Test einmal). `qa/data.py` Daten-API (Suche, Abdeckung, Kerzen, Optionen, Schemas, Nutzung).
- `qa/study.py` Statistik (Marktbereinigung, Steigung, Drittel, Hälften-Test, BH-Korrektur), `qa/quality.py` Datenprüfung, `qa/assets.py` Märkte laden.
- `qa/chain.py` Kettenprüfung aus `chains/*.json`; `qa/report.py` Bericht; `qa/__main__.py` Befehlszeile.
- `qa/backtest.py` Backtests aus `strategies/*.json` (trend, momentum, umkehr, ereignis), `qa/metrics.py` Kennzahlen, Deflated Sharpe, PBO; Versuchsprotokoll `data/trials.jsonl`.
- Befehle für Claude Code: `/kette` (Denkweise: weit denken, hart messen, ehrlich berichten), `/ereignis`.
- Stand aller Anforderungen: `docs/ROADMAP.md` – bei neuen Funktionen dort nachführen.
- Betrieb ohne eigenen Rechner: `routine.json` + `qa/routine.py` (täglicher Lauf nach `reports/auto/`, GitHub Actions `.github/workflows/routine.yml`), Weboberfläche `app.py` (Streamlit Community Cloud). Repository und Streamlit-App sind auf Wunsch des Nutzers (28.10.) öffentlich im Testbetrieb (Streamlit fand das private Repository nicht) – Yahoo erlaubt nur private Nutzung, das Risiko ist dem Nutzer bekannt. Impressum/Datenschutz: `qa/legal.py`, Angaben aus Streamlit-Secrets.
- `qa/cache.py`: alles wird einmal nach `data/` geladen (Parquet / Rohdateien) und danach von der Platte gelesen.
- Ergebnisse: `reports/<Datum>_<Analyse>.md` (Bericht) und `.csv` (jedes Ereignis einzeln).

## Befehle
- Tests: `.venv/bin/python -m pytest -q`
- Befehl: `.venv/bin/python -m qa befehl "/overnight es" [--projekt start]` · Website lokal: `.venv/bin/streamlit run app.py`
- Analyse: `.venv/bin/python -m qa ereignis ezb|fed|fred:<Reihe>|earnings:<Ticker>|kurs:<Symbol> [--maerkte …] [--von …] [--bis …] [--art …]`
- Katalog: `.venv/bin/python -m qa katalog` · Chat: `.venv/bin/python -m qa chat "Frage"`
- Earnings: `.venv/bin/python -m qa earnings <Ticker>[,<Ticker>…] [--maerkte …]` · Kette: `.venv/bin/python -m qa kette chains/<datei>.json` · Backtest: `.venv/bin/python -m qa backtest strategies/<datei>.json`
- Märkte-Kürzel: `.venv/bin/python -m qa maerkte`

## Regeln für Analysen (wichtiger als alles andere)
- **Zahlen nur aus Messungen.** Jede Zahl in einer Antwort stammt aus einem Bericht oder einer Rechnung in diesem Projekt – nie aus dem Gedächtnis des Sprachmodells. Kursverläufe und Ereignisse vor dem Trainingsende kennt das Modell auswendig; das ist kein Beleg.
- **Immer Fallzahl, p/q-Wert und Zeitraum nennen.** „Belastbar“ nur, wenn der Bericht es sagt (q < 0,10, mindestens 20 Fälle).
- **Nichts aus der Zukunft:** Makrodaten nur als Erstveröffentlichung (ALFRED), erwartete Werte nur aus vorher bekannten Daten, Reaktion erst ab dem Schlusskurs vor dem Ereignis.
- **Jede getestete Variante zählt.** Wer zehn Varianten probiert und eine zeigt, muss die anderen neun erwähnen. Backtests: Testzeitraum (`holdout_ab`) nie nachträglich verschieben, um ein Ergebnis zu retten; neue Parameter-Varianten landen im Versuchsprotokoll und erhöhen die Hürde.
- **Regime prüfen:** wichtige Ergebnisse auch für Teilzeiträume rechnen (`--von/--bis`, z. B. vor/nach 2014 wegen Negativzinsen).
- Bekannte Grenzen nennen: Tagesdaten (andere Nachrichten am selben Tag), Yahoo ohne delistete Firmen, Futures ohne Roll-Bereinigung, kein Konsens bei FRED-Reihen.
- Keine Kauf-/Verkaufsempfehlungen; beschreiben, was gemessen wurde.

## Konventionen
- Neue Berechnungen bekommen Unit-Tests (`tests/`). Kein Ersatzwert, wenn eine Quelle fehlt: Hinweis ausgeben.
- Kostenlose Quellen bevorzugen; kostenpflichtige Anbieter nur nach Zustimmung. Schlüssel nur in `.env`, nie ausgeben.
- FRED-Downloads ohne eigenen User-Agent (FREDs CDN verwirft unbekannte Browser-Kennungen).
- **Neue Quelle = Tagesversatz prüfen:** Tagesänderung am Ereignistag und am Folgetag mit einer bekannten Überraschung korrelieren (z. B. EZB). Bundesbank datiert Werte einen Handelstag zu spät (in `_bbk` korrigiert); EZB-Referenzkurse werden um 14:15 festgestellt (Markt `ecb_fix`).
- Inoffizielle Quellen (Stooq, pytrends, Websites) darf ich nutzen (Entscheidung des Nutzers 29.10.2026, Risiko bei ihm) – aber nie Captchas, Logins oder aktive Sperren umgehen; dann Faktor „blockiert“ mit Grund.
- Arbeitsweise seit 29.10.2026: Faktorenliste in `FEATURES.md` (Status offen/in Arbeit/fertig/blockiert; „fertig“ nur mit Daten → Event/Feature → nutzbar in Ereignisstudie und Kette → Live-Test mit echten Daten, Ausgabe zeigen). Etappen: Datenschicht → Event-Speicher → Analyse → Ketten → Oberfläche; nach jeder Etappe FEATURES.md + kurze Zusammenfassung. Schlüsselfreie Quellen zuerst. SEC-Kontakt steht in `.env` (`SEC_USER_AGENT`). Live-Tests: `pytest -m live` lokal und wöchentlich in GitHub Actions.
- Commit/Push nur auf ausdrücklichen Wunsch.
