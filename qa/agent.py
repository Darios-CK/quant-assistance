"""AI analyst: Claude with this project's analyses as tools.

The model thinks the question through (chains over several levels, combinations of conditions) and every number
in its answer comes from a tool run – event studies, chain checks, earnings, backtests.  It never computes or
remembers market figures itself.

Needs ANTHROPIC_API_KEY (environment, .env or Streamlit secrets).  Each question costs money: see COST_NOTE.
Model and effort can be changed with QA_MODEL / QA_EFFORT.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Callable

import anthropic
from dotenv import load_dotenv

from qa import catalog, regimes, triggers
from qa.cache import ROOT
from qa.sources import prices

MODEL = os.getenv("QA_MODEL", "claude-opus-5-5")
EFFORT = os.getenv("QA_EFFORT", "high")
MAX_STEPS = int(os.getenv("QA_MAX_STEPS", "14"))      # tool rounds per question – caps cost and runaway loops
MAX_RESULT_CHARS = 24000
PRICE_PER_MTOK = {"claude-opus-5-5": (4.0, 20.0, 0.20)}  # input, output, cache read (USD) – for the cost line only
COST_NOTE = "Claude Opus 5.5: 4 $ je 1 Mio. Eingabe-Tokens, 20 $ je 1 Mio. Ausgabe-Tokens; eine Analyse-Frage kostet typischerweise 0,10–1 $."

SYSTEM = f"""Du bist der Quant Copilot von Quant Assistance. Du beantwortest Fragen zu Märkten, indem du die Werkzeuge
benutzt, die echte historische Daten auswerten. Antworte auf Deutsch.

## Denkweise: weit denken, hart messen, ehrlich berichten

1. Weit denken. Bleib nicht bei "Öl steigt, Nasdaq fällt". Baue Ketten über mehrere Ebenen: direkt Betroffene
   (Kosten, Erlöse), dann Kunden, Lieferanten, Wettbewerber, Ersatzprodukte, Rohstoffketten, Konzernverflechtungen
   (Mutter, Töchter, eigene Sparten), dazu Währungen, Zinsen, Inflationserwartung, Rohstoffe und Krypto.
   Denk an Gegenkräfte (Absicherung, Preisweitergabe) und daran, dass die Ursache eines Auslösers die Richtung
   umdrehen kann (Angebots- vs. Nachfrageschock). Verflechtungen, die nicht allgemein bekannt sind, kennzeichnest
   du als Annahme.
2. Hart messen. Jede Behauptung über Märkte prüfst du mit einem Werkzeug. Bei Ketten mit kette_pruefen (jedes Glied
   gegen den Auslöser, marktbereinigt). Bei Kombinationen ("Muster A und Muster B") nutzt du die Bedingungen
   (Marktphasen) und zusammen_mit / ohne. Wichtige Ergebnisse prüfst du in Teilzeiträumen (von/bis) oder einer
   zweiten Phase gegen. Wenn eine Frage im Detail gewünscht ist, geh ins Detail: mehrere Horizonte, Teilzeiträume,
   Phasen, einzelne Firmen und die Gruppe.
3. Ehrlich berichten. Zahlen NUR aus Werkzeug-Ergebnissen – nie aus deinem Gedächtnis: Kursverläufe vor deinem
   Trainingsende kennst du auswendig, das ist kein Beleg. Nenne zu jedem Ergebnis Fallzahl, Zeitraum und Einordnung
   (belastbar / Tendenz / kein Muster / zu wenig Fälle). Sag, was die Daten ANDERS zeigen als die Hypothese – das
   ist das Wertvollste. Nenne, wie viele Varianten du gerechnet hast (jede zählt), und die Grenzen: Tagesdaten
   (gleichzeitige Nachrichten), Yahoo ohne delistete Firmen, fehlender Konsens bei Konjunkturdaten, wenige Fälle.

## Regeln
- Keine Kauf- oder Verkaufsempfehlung, keine Kursziele. Du beschreibst, was in der Vergangenheit gemessen wurde.
- Was gratis nicht messbar ist (siehe Katalog, ❌), sagst du offen; schlag den nächstbesten messbaren Stellvertreter vor.
- Für Ereignisse ohne Datenquelle (Zölle, Produktstarts, Skandale) darfst du termine:<Daten> nutzen. Die Daten
  stammen dann aus deinem Wissen: kennzeichne das, nimm nur Termine, bei denen du sicher bist, und bitte den Nutzer,
  sie zu prüfen.
- Werkzeug-Fehler (z. B. fehlender FRED-Schlüssel, unbekannter Ticker) erklärst du kurz und versuchst einen sinnvollen
  anderen Weg.
- Halte die Antwort gegliedert: kurzes Ergebnis zuerst, dann die Belege (Tabelle oder Liste), dann Grenzen.
  Höchstens so viele Werkzeug-Aufrufe wie für eine belastbare Antwort nötig.

## Projekte, Befehle, Gedächtnis
- Arbeite in Projekten: Strategien, Ketten, Trades-CSV und Skripte liegen dort (projekte, datei_lesen, datei_schreiben).
  Neue Strategien/Ketten schreibst du als Datei ins Projekt und testest sie mit befehl ('/backtest datei.json').
- Slash-Befehle über das Werkzeug befehl: /review vor jedem Ergebnis, das du als tragfähig darstellst; /walk-forward,
  /regime-pnl, /overnight, /trades, /goal, /optionen, /kerzen; eigene Befehle des Nutzers stehen in /commands.
- Lies zu Beginn eines Gesprächs gedaechtnis. Eigene Anweisungen des Nutzers befolgst du immer und änderst sie nie.
  Mit merken speicherst du nur Dauerhaftes, das der Nutzer gesagt oder bestätigt hat (Arbeitsweise, Entscheidungen
  im Projekt) – nie Marktzahlen.
- Daten: symbole_suchen, symbol_aufloesen, abdeckung, kerzen_vorschau (max. 500 Kerzen/31 Tage), schema_erklaeren,
  daten_anleitung. Ticks, Quotes, Orderbuch und Options-Historie gibt es gratis nicht – sag das und nimm Ersatz.

## Quellen für Ereignisse (Parameter quelle)
{triggers.__doc__}

## Marktphasen für Bedingungen (bedingung, Kommaliste, alle müssen gelten)
{chr(10).join(f"- {k}: {v[0]}" for k, v in regimes.PHASES.items())}

## Märkte
Kürzel: {", ".join(prices.ALIASES)}. Außerdem jedes Yahoo-Symbol (z. B. SAP.DE, GT, JETS, ^N225, BTC-USD, NG=F) und
FRED:<Reihe> bzw. BBK:/EZB: für Zinsreihen. Einzelaktien und Sektor-ETFs werden automatisch gegen S&P 500 bzw.
DAX bereinigt.
"""

OBJ = {"type": "object"}
TOOLS = [
    {"name": "ereignis_analyse",
     "description": "Wie reagierten Märkte auf Ereignisse? Reaktion am Reaktionstag, nach 1 Woche und 1 Monat, nach Größe "
                    "der Überraschung, mit Fallzahl, p/q-Wert und Einordnung. Kombinationen über bedingung (Marktphasen) "
                    "und zusammen_mit / ohne (andere Quelle innerhalb ±fenster Tagen).",
     "input_schema": {"type": "object", "properties": {
         "quelle": {"type": "string", "description": "z. B. ezb, fed, makro:cpi, kurs:CL=F, technik:^GSPC:sma200_runter, kalender:januar, wahl:us, termine:2019-05-05,2019-08-01"},
         "maerkte": {"type": "string", "description": "Kommaliste, z. B. dax,bund2j,banken_eu,SAP.DE"},
         "von": {"type": "string"}, "bis": {"type": "string"},
         "mass": {"type": "string", "description": "ezb: zins|ausblick|gesamt; fed: roh|bereinigt"},
         "art": {"type": "string", "description": "alle|zins-schock|info-schock (ezb, fed)"},
         "methode": {"type": "string", "description": "makro/fred: naiv|veraenderung"},
         "schwelle": {"type": "number", "description": "kurs: Standardabweichungen (Standard 2)"},
         "richtung": {"type": "string", "description": "kurs: hoch|runter|beide"},
         "horizonte": {"type": "string", "description": "Handelstage, z. B. 0,5,20,60"},
         "bedingung": {"type": "string", "description": "Marktphasen, Kommaliste, z. B. vix_hoch,trend_ab"},
         "zusammen_mit": {"type": "string", "description": "andere Quelle, die in der Nähe liegen muss"},
         "ohne": {"type": "string", "description": "andere Quelle, die NICHT in der Nähe liegen darf"},
         "fenster": {"type": "integer", "description": "Abstand in Kalendertagen für zusammen_mit/ohne (Standard 3)"},
         "ohne_bereinigung": {"type": "boolean"}},
         "required": ["quelle"]}},
    {"name": "kette_pruefen",
     "description": "Prüft eine Kausalkette Glied für Glied gegen den Auslöser (marktbereinigt, alle Tests gemeinsam korrigiert). "
                    "kette = {name, frage, ausloeser: {quelle, …Optionen wie schwelle/richtung/mass}, von, bis, horizonte, "
                    "glieder: [{id, symbol, name, nach (id des Vorgängers oder 'ausloeser'), erwartung ('+'|'-'|'?'), warum}]}. "
                    "8–20 Glieder über mehrere Ebenen sind gut.",
     "input_schema": {"type": "object", "properties": {"kette": OBJ}, "required": ["kette"]}},
    {"name": "earnings_analyse",
     "description": "Reaktion auf Quartalszahlen gegenüber dem Analysten-Konsens. Ein Ticker: die Aktie selbst und optional "
                    "weitere Märkte (wer reagiert noch?). Mehrere Ticker (Kommaliste): jede Firma einzeln und alle zusammen.",
     "input_schema": {"type": "object", "properties": {
         "ticker": {"type": "string"}, "maerkte": {"type": "string"}, "von": {"type": "string"}, "bis": {"type": "string"},
         "horizonte": {"type": "string"}}, "required": ["ticker"]}},
    {"name": "backtest",
     "description": "Testet eine Handelsregel ehrlich: Kosten, Testzeitraum (holdout_ab), Walk-Forward, Deflated Sharpe, PBO, "
                    "Stresstests. strategie = {name, markt, regel: trend|momentum|umkehr|ereignis, parameter: {…Listen…}, "
                    "short, kosten_bp, holdout_ab, warum; bei ereignis zusätzlich ausloeser: {quelle, …}, richtung: mit|gegen}. "
                    "Parameter: trend schnell/langsam; momentum lookback/skip; umkehr tage/schwelle/halten; ereignis halten/schwelle.",
     "input_schema": {"type": "object", "properties": {"strategie": OBJ}, "required": ["strategie"]}},
    {"name": "katalog",
     "description": "Welche Markttreiber mit freien Daten messbar sind, mit welcher Quelle – und welche nicht.",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "marktphasen_aktuell",
     "description": "Welche Marktphasen gerade gelten (VIX, Trend, Zinskurve, Kreditstress, Leitzins) – um zu prüfen, wie "
                    "Muster in einer Lage wie heute verliefen.",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "befehl",
     "description": "Führt einen Slash-Befehl aus (eingebaut oder eigener des Nutzers), z. B. '/overnight es', "
                    "'/walk-forward trend_dax.json is=24 oos=6 schritt=3', '/review strategie.json', '/regime-pnl strategie.json', "
                    "'/trades meine_trades.csv', '/goal strategie.json sharpe>=0.8', '/optionen AAPL', '/commands'. "
                    "Dateinamen beziehen sich auf das Projekt. Ergebnisse werden im Projekt als Artefakt gespeichert.",
     "input_schema": {"type": "object", "properties": {
         "zeile": {"type": "string"}, "projekt": {"type": "string", "description": "Projektname (siehe projekte)"}},
         "required": ["zeile"]}},
    {"name": "projekte",
     "description": "Projekte des Nutzers; mit projekt: dessen Dateien (Strategien, Ketten, Trades, Skripte, Artefakte, Chats).",
     "input_schema": {"type": "object", "properties": {"projekt": {"type": "string"}}}},
    {"name": "datei_lesen",
     "description": "Liest eine Datei aus einem Projekt.",
     "input_schema": {"type": "object", "properties": {"projekt": {"type": "string"}, "pfad": {"type": "string"}}, "required": ["projekt", "pfad"]}},
    {"name": "datei_schreiben",
     "description": "Schreibt eine Datei in ein Projekt (z. B. eine Strategie- oder Ketten-JSON, Notizen, ein Python-Skript). "
                    "Legt das Projekt an, falls es fehlt.",
     "input_schema": {"type": "object", "properties": {"projekt": {"type": "string"}, "pfad": {"type": "string"}, "inhalt": {"type": "string"}},
                      "required": ["projekt", "pfad", "inhalt"]}},
    {"name": "merken",
     "description": "Merkt sich etwas Dauerhaftes über den Nutzer, seine Arbeitsweise oder eine Projekt-Entscheidung (sichtbar und "
                    "löschbar für den Nutzer). Nur Fakten, die der Nutzer gesagt oder bestätigt hat; keine Marktzahlen.",
     "input_schema": {"type": "object", "properties": {"text": {"type": "string"}, "projekt": {"type": "string"}}, "required": ["text"]}},
    {"name": "gedaechtnis",
     "description": "Liest Gedächtnis und eigene Anweisungen des Nutzers (Anweisungen immer befolgen, nie ändern).",
     "input_schema": {"type": "object", "properties": {"projekt": {"type": "string"}}}},
    {"name": "symbole_suchen",
     "description": "Sucht Symbole: Kürzel, CME-Futures, Aktien, ETFs, Indizes, Währungen, Krypto.",
     "input_schema": {"type": "object", "properties": {"text": {"type": "string"},
                      "art": {"type": "string", "description": "aktie|etf|index|future|waehrung|krypto|fonds"}}, "required": ["text"]}},
    {"name": "abdeckung",
     "description": "Welche Daten es für ein Symbol gibt: Tageswerte (Zeitraum), Intraday-Grenzen, Optionen.",
     "input_schema": {"type": "object", "properties": {"symbol": {"type": "string"}}, "required": ["symbol"]}},
    {"name": "symbol_aufloesen",
     "description": "Übersetzt Kürzel oder Ticker in das eindeutige Symbol mit Quelle, Einheit, Börse und Vergleichsindex.",
     "input_schema": {"type": "object", "properties": {"namen": {"type": "string", "description": "Kommaliste"}}, "required": ["namen"]}},
    {"name": "schema_erklaeren",
     "description": "Erklärt die Felder eines Datenschemas: kerzen, schlusskurse, ereignisse, reaktionen, backtest, optionskette, trades, orderbuch.",
     "input_schema": {"type": "object", "properties": {"name": {"type": "string"}}}},
    {"name": "nutzung",
     "description": "Was geladen und gespeichert ist (Cache, Projekte, Speicherort).",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "daten_anleitung",
     "description": "Anleitung: Kerzen und Intervalle, Futures ohne Roll-Bereinigung, große Abfragen per Skript, Grenzen der freien Daten.",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "kerzen_vorschau",
     "description": "Vorschau von höchstens 500 OHLCV-Kerzen über höchstens 31 Tage. Intervalle 1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo.",
     "input_schema": {"type": "object", "properties": {"symbol": {"type": "string"}, "intervall": {"type": "string"},
                      "tage": {"type": "integer"}}, "required": ["symbol"]}},
    {"name": "kursstand",
     "description": "Letzter Kurs und Veränderung über 1 Tag, 1 Woche, 1 Monat, 1 Jahr für Symbole oder Kürzel.",
     "input_schema": {"type": "object", "properties": {"symbole": {"type": "string", "description": "Kommaliste"}}, "required": ["symbole"]}},
]


# ---------------------------------------------------------------- tool execution
def _argv_event(i: dict) -> list[str]:
    argv = ["ereignis", str(i["quelle"])]
    for key, flag in (("maerkte", "--maerkte"), ("von", "--von"), ("bis", "--bis"), ("mass", "--mass"), ("art", "--art"),
                      ("methode", "--methode"), ("schwelle", "--schwelle"), ("richtung", "--richtung"), ("horizonte", "--horizonte"),
                      ("bedingung", "--bedingung"), ("zusammen_mit", "--zusammen-mit"), ("ohne", "--ohne"), ("fenster", "--fenster")):
        if i.get(key) not in (None, ""):
            argv += [flag, str(i[key])]
    if i.get("ohne_bereinigung"):
        argv.append("--ohne-bereinigung")
    return argv


def _spec_file(kind: str, spec) -> str:
    if isinstance(spec, str):
        spec = json.loads(spec)
    folder = ROOT / "data" / "agent"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{kind}_{abs(hash(json.dumps(spec, sort_keys=True))) % 10**8}.json"
    path.write_text(json.dumps(spec, ensure_ascii=False, indent=1), encoding="utf-8")
    return str(path)


def _quotes(symbols: str) -> str:
    rows = ["| Markt | Stand | Datum | 1 Tag | 1 Woche | 1 Monat | 1 Jahr |", "|---|---:|---|---:|---:|---:|---:|"]
    for name in [s.strip() for s in symbols.split(",") if s.strip()]:
        sym, label = prices.resolve(name)
        try:
            c = prices.closes(sym)
        except Exception as exc:
            rows.append(f"| {label} | keine Daten: {exc} | | | | | |")
            continue
        unit = prices.unit(sym)
        chg = lambda n: (f"{(c.iloc[-1] - c.iloc[-1 - n]) * 100:+.1f} Bp" if unit == "bp" else f"{(c.iloc[-1] / c.iloc[-1 - n] - 1) * 100:+.2f} %") if len(c) > n else "–"  # noqa: E731
        rows.append(f"| {label} | {c.iloc[-1]:.4g} | {c.index[-1]:%d.%m.%Y} | {chg(1)} | {chg(5)} | {chg(21)} | {chg(252)} |")
    return "\n".join(rows) + "\n\nTagesschlusskurse (Yahoo/FRED/Bundesbank/EZB), können verzögert sein."


def execute(name: str, i: dict) -> str:
    from qa.__main__ import run

    if name == "ereignis_analyse":
        return run(_argv_event(i))[0]
    if name == "kette_pruefen":
        return run(["kette", _spec_file("kette", i["kette"])])[0]
    if name == "earnings_analyse":
        argv = ["earnings", str(i["ticker"])]
        for key in ("maerkte", "von", "bis", "horizonte"):
            if i.get(key):
                argv += [f"--{key}", str(i[key])]
        return run(argv)[0]
    if name == "backtest":
        return run(["backtest", _spec_file("strategie", i["strategie"])])[0]
    if name == "katalog":
        return catalog.as_markdown()
    if name == "marktphasen_aktuell":
        rows = ["| Phase | Bedeutung | gilt gerade | Stand |", "|---|---|---|---|"]
        for r in regimes.current():
            rows.append(f"| {r['phase']} | {r['beschreibung']} | {'ja' if r['aktiv'] else 'nein' if r['aktiv'] is False else '–'} | {r['stand']} |")
        return "\n".join(rows)
    if name == "kursstand":
        return _quotes(i["symbole"])
    return _workspace_tool(name, i)


def _workspace_tool(name: str, i: dict) -> str:
    from qa import commands, data, workspace

    project = i.get("projekt") or None
    if name == "befehl":
        if project and project not in workspace.projects():
            raise SystemExit(f"Projekt '{project}' gibt es nicht – vorhanden: {', '.join(workspace.projects()) or 'keine'}")
        results = commands.run(str(i["zeile"]), commands.Ctx(project))
        return "\n\n".join(r.text + (f"\n_(gespeichert: {r.artifact})_" if r.artifact else "") for r in results)
    if name == "projekte":
        if project:
            return f"Dateien in {project}:\n" + "\n".join(f"- {f}" for f in workspace.files(project))
        return "Projekte: " + (", ".join(workspace.projects()) or "keine")
    if name == "datei_lesen":
        return workspace.read(i["projekt"], i["pfad"])
    if name == "datei_schreiben":
        if i["projekt"] not in workspace.projects():
            workspace.create(i["projekt"])
        workspace.write(i["projekt"], i["pfad"], str(i["inhalt"]))
        return f"Gespeichert: {i['projekt']}/{i['pfad']}"
    if name == "merken":
        e = workspace.remember(i["text"], project)
        return f"Gemerkt [{e['id']}]: {e['text']}"
    if name == "gedaechtnis":
        return workspace.context_for_ai(project) or "Gedächtnis und Anweisungen sind leer."
    if name == "symbole_suchen":
        return data.table(data.search(i["text"], i.get("art", "")))
    if name == "abdeckung":
        return "\n".join(f"- {k}: {v}" for k, v in data.coverage(i["symbol"]).items())
    if name == "symbol_aufloesen":
        return data.table([data.resolve(n.strip()) for n in str(i["namen"]).split(",") if n.strip()])
    if name == "schema_erklaeren":
        return commands.c_schema([i["name"]] if i.get("name") else [], commands.Ctx()).text
    if name == "nutzung":
        return commands.c_nutzung([], commands.Ctx()).text
    if name == "daten_anleitung":
        return data.GUIDE
    if name == "kerzen_vorschau":
        df = data.preview_bars(i["symbol"], i.get("intervall") or "1d", int(i.get("tage") or 31))
        return f"{len(df)} Kerzen\n\n" + data.frame_md(df)
    raise ValueError(f"unbekanntes Werkzeug {name}")


def _run_tool(name: str, i: dict) -> tuple[str, bool]:
    try:
        out = execute(name, i)
        return (out if len(out) <= MAX_RESULT_CHARS else out[:MAX_RESULT_CHARS] + "\n… (gekürzt)"), False
    except SystemExit as exc:                     # our own input errors: readable message for the model
        return f"Fehler: {exc}", True
    except Exception as exc:
        return f"Fehler: {type(exc).__name__}: {exc}", True


# ---------------------------------------------------------------- conversation
def client() -> anthropic.Anthropic:
    load_dotenv(ROOT / ".env")
    return anthropic.Anthropic()


LEVELS = {"Niedrig": "low", "Mittel": "medium", "Hoch": "high", "Maximal": "max"}


def ask(question: str, history: list, on_step: Callable[[str, dict, str, bool], None] | None = None,
        api: anthropic.Anthropic | None = None, effort: str | None = None, context: str = "") -> tuple[str, list, dict]:
    """One user question.  history: earlier messages (append-only, returned extended).
    Returns (answer text, new history, usage with tokens and estimated cost)."""
    api = api or client()
    messages = list(history) + [{"role": "user", "content": question}]
    usage = {"input": 0, "output": 0, "cache_read": 0, "cache_write": 0, "steps": 0}
    text = ""
    for _ in range(MAX_STEPS + 3):                         # tool rounds plus room for the final answer after the limit
        response = api.beta.messages.create(
            model=MODEL, max_tokens=16000,
            system=[{"type": "text", "text": SYSTEM}] + ([{"type": "text", "text": context}] if context else []),
            tools=TOOLS, messages=messages,
            thinking={"type": "adaptive"},
            output_config={"effort": effort or EFFORT},
            cache_control={"type": "ephemeral"},            # system prompt + tools + earlier turns are reused
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",                            # a safety refusal is retried on a suitable model
        )
        u = response.usage
        usage["input"] += u.input_tokens
        usage["output"] += u.output_tokens
        usage["cache_read"] += u.cache_read_input_tokens or 0
        usage["cache_write"] += u.cache_creation_input_tokens or 0
        messages.append({"role": "assistant", "content": response.content})   # keep thinking blocks unchanged
        text = "\n".join(b.text for b in response.content if b.type == "text").strip()

        if response.stop_reason == "refusal":
            text = text or "Die Anfrage wurde aus Sicherheitsgründen abgelehnt."
            break
        if response.stop_reason == "pause_turn":
            continue
        if response.stop_reason == "max_tokens":
            text += "\n\n(Antwort wurde wegen der Längenbegrenzung abgeschnitten.)"
            break
        calls = [b for b in response.content if b.type == "tool_use"]
        if response.stop_reason != "tool_use" or not calls:
            break
        if usage["steps"] >= MAX_STEPS:
            messages.append({"role": "user", "content": [
                {"type": "tool_result", "tool_use_id": c.id, "is_error": True,
                 "content": "Limit an Werkzeug-Aufrufen erreicht – bitte jetzt mit den vorhandenen Ergebnissen antworten."} for c in calls]})
            continue
        results = []
        for c in calls:                                     # all results go back in one message
            out, err = _run_tool(c.name, dict(c.input))
            usage["steps"] += 1
            if on_step:
                on_step(c.name, dict(c.input), out, err)
            results.append({"type": "tool_result", "tool_use_id": c.id, "content": out, "is_error": err})
        messages.append({"role": "user", "content": results})
    usage["cost_usd"] = cost(usage)
    return text, messages, usage


def cost(usage: dict) -> float:
    inp, outp, cached = PRICE_PER_MTOK.get(MODEL, (4.0, 20.0, 0.20))
    return (usage["input"] * inp + usage["cache_write"] * inp * 1.25 + usage["cache_read"] * cached + usage["output"] * outp) / 1e6


def available() -> tuple[bool, str]:
    load_dotenv(ROOT / ".env")
    if os.getenv("ANTHROPIC_API_KEY"):
        return True, ""
    return False, ("Für den Chat fehlt ein Anthropic-API-Schlüssel (ANTHROPIC_API_KEY). Anlegen unter https://console.anthropic.com "
                   "→ API Keys; lokal in .env, in der Cloud unter Streamlit → Settings → Secrets eintragen. " + COST_NOTE)
