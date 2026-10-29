"""Slash commands – the Copilot's language.  Work without any AI (free) on the website, in `python -m qa befehl`,
and for Claude through MCP (tool 'befehl').

    /backtest trend_dax.json        files are looked up in the current project, then in the repository
    /wf-quartal trend_dax.json      own commands (.md files) run their lines with $1 … $9 / $ARGUMENTS filled in

Every result is kept as an artifact in the project (artefakte/).
"""

from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import pandas as pd

from qa import catalog, data, metrics, regimes, workflows, workspace
from qa.cache import ROOT

MAX_DEPTH = 3
RUN_TIMEOUT = 300


@dataclass
class Result:
    title: str
    text: str
    ok: bool = True
    chart: pd.DataFrame | None = None          # line chart, index = date
    table: pd.DataFrame | None = None          # downloadable detail (CSV)
    artifact: str = ""                         # path of the kept artifact in the project


@dataclass
class Ctx:
    project: str | None = None
    chat: list = field(default_factory=list)
    save: bool = True
    depth: int = 0


def is_cloud() -> bool:
    return bool(os.getenv("QA_CLOUD")) or str(ROOT).startswith("/mount/src")


# ---------------------------------------------------------------- helpers
def _split(args: list[str]) -> tuple[list[str], dict[str, str]]:
    pos, opt = [], {}
    for a in args:
        k, eq, v = a.partition("=")
        if eq and re.fullmatch(r"[a-zA-Z_]+", k):
            opt[k.lower()] = v
        else:
            pos.append(a)
    return pos, opt


def _need(pos: list[str], n: int, usage: str) -> None:
    if len(pos) < n:
        raise SystemExit(f"Aufruf: {usage}")


def file_path(name: str, ctx: Ctx) -> Path:
    """A project file as a real file on disk (copied to data/tmp), or a file of the repository (strategies/, chains/)."""
    if ctx.project:
        try:
            text = workspace.read(ctx.project, name)
            tmp = ROOT / "data" / "tmp" / ctx.project
            tmp.mkdir(parents=True, exist_ok=True)
            p = tmp / Path(name).name
            p.write_text(text, encoding="utf-8")
            return p
        except SystemExit:
            pass
    allowed = (ROOT / "strategies", ROOT / "chains")                 # never other repository files (.env …)
    for cand in (ROOT / name, ROOT / "strategies" / name, ROOT / "chains" / name):
        if cand.is_file() and cand.resolve().parent in allowed:
            return cand
    where = f"im Projekt '{ctx.project}' und " if ctx.project else ""
    raise SystemExit(f"Datei '{name}' nicht gefunden ({where}in strategies/, chains/)")


def _equity_chart(detail: pd.DataFrame) -> pd.DataFrame | None:
    if detail is None or "rendite_strategie" not in detail:
        return None
    d = detail.set_index("datum")
    return pd.DataFrame({"Strategie": metrics.equity(d["rendite_strategie"]), "Kaufen-und-Halten": metrics.equity(d["rendite_markt"].fillna(0))})


def _cli(argv: list[str], title: str) -> Result:
    from qa.__main__ import run

    try:
        text, per_event, _ = run(argv)
    except SystemExit as exc:
        if isinstance(exc.code, int):                       # argparse already printed what was wrong
            raise SystemExit(f"Ungültige Angaben für /{argv[0]} – Aufruf siehe /commands")
        raise
    chart = _equity_chart(per_event) if argv[0] == "backtest" else None
    return Result(title, text, chart=chart, table=per_event if per_event is not None and len(per_event) else None)


# ---------------------------------------------------------------- built-in commands
def c_ereignis(args, ctx):
    _need(args, 1, "/ereignis <quelle> [--maerkte …] [--bedingung …] …")
    return _cli(["ereignis", *args], f"Ereignis {args[0]}")


def c_earnings(args, ctx):
    _need(args, 1, "/earnings <Ticker>[,<Ticker>…] [--maerkte …]")
    return _cli(["earnings", *args], f"Earnings {args[0]}")


def c_kette(args, ctx):
    _need(args, 1, "/kette <datei.json>")
    return _cli(["kette", str(file_path(args[0], ctx))], f"Kette {args[0]}")


def c_backtest(args, ctx):
    _need(args, 1, "/backtest <strategie.json>")
    return _cli(["backtest", str(file_path(args[0], ctx))], f"Backtest {args[0]}")


def c_review(args, ctx):
    _need(args, 1, "/review <strategie.json | kette.json>")
    return Result(f"Review {args[0]}", workflows.review(file_path(args[0], ctx)))


def c_walk_forward(args, ctx):
    pos, opt = _split(args)
    _need(pos, 1, "/walk-forward <strategie.json> [is=24] [oos=6] [schritt=3]   (Monate)")
    text, chart = workflows.walk_forward_report(file_path(pos[0], ctx), int(opt.get("is", 24)), int(opt.get("oos", 6)),
                                                int(opt.get("schritt", opt.get("step", 3))))
    return Result(f"Walk-Forward {pos[0]}", text, chart=chart)


def c_regime(args, ctx):
    _need(args, 1, "/regime-pnl <strategie.json>")
    text, detail = workflows.regime_pnl(file_path(args[0], ctx))
    return Result(f"P&L nach Marktphase {args[0]}", text, table=detail)


def c_overnight(args, ctx):
    pos, opt = _split(args)
    _need(pos, 1, "/overnight <symbol> [von=2000]")
    text, chart = workflows.overnight(pos[0], opt.get("von"))
    return Result(f"Über Nacht vs. Handelszeit {pos[0]}", text, chart=chart)


def c_trades(args, ctx):
    pos, opt = _split(args)
    _need(pos, 1, "/trades <trades.csv> [markt=sp500]   (Spalten: datum, optional symbol, richtung)")
    text, detail = workflows.trades(file_path(pos[0], ctx).read_text(encoding="utf-8"), opt.get("markt", "sp500"))
    return Result(f"Vor deinen Einstiegen {pos[0]}", text, table=detail)


def _goal_path(ctx):
    if not ctx.project:
        raise SystemExit("/goal braucht ein Projekt (der Stand wird dort gespeichert)")
    return ".ziele/aktuell.json"


def c_goal(args, ctx):
    path = _goal_path(ctx)
    raw = workspace.store().read(f"{ctx.project}/{path}")
    state = json.loads(raw) if raw else None
    sub = args[0].lower() if args else "status"
    if sub in ("status", "weiter", "pause", "stopp"):
        if not state:
            raise SystemExit("Kein Ziel aktiv. Starten: /goal <strategie.json> sharpe>=0.8")
        if sub == "pause" and state["status"] == "läuft":
            state["status"] = "pausiert"
        elif sub == "stopp":
            state["status"] = "gestoppt"
        elif sub == "weiter":
            if state["status"] not in ("läuft", "pausiert"):
                raise SystemExit(f"Ziel ist {state['status']} – neu starten mit /goal <datei> <ziel>")
            state["status"] = "läuft"
            state = workflows.goal_step(state, workflows.backtest.load_spec(file_path(state["datei"], ctx)))
    else:
        _need(args, 2, "/goal <strategie.json> <ziel, z. B. sharpe>=0.8> · /goal status|weiter|pause|stopp")
        workflows.parse_goal(args[1])
        state = {"datei": args[0], "ziel": args[1], "status": "läuft", "geprueft": [], "verlauf": [], "versuche": 0}
        state = workflows.goal_step(state, workflows.backtest.load_spec(file_path(args[0], ctx)))
    workspace.write(ctx.project, path, json.dumps(state, ensure_ascii=False, indent=1, default=str))
    return Result(f"Ziel {state['ziel']}", workflows.goal_text(state))


def c_phasen(args, ctx):
    rows = ["| Phase | Bedeutung | gilt gerade | Stand |", "|---|---|---|---|"]
    for r in regimes.current():
        rows.append(f"| {r['phase']} | {r['beschreibung']} | {'ja' if r['aktiv'] else 'nein' if r['aktiv'] is False else '–'} | {r['stand']} |")
    return Result("Marktphasen heute", "# Marktphasen heute\n\n" + "\n".join(rows) + "\n")


def c_kurs(args, ctx):
    from qa.agent import _quotes

    _need(args, 1, "/kurs <symbole, Kommaliste>")
    return Result(f"Kurse {args[0]}", "# Kursstand\n\n" + _quotes(",".join(args)))


def c_katalog(args, ctx):
    return Result("Abdeckung", catalog.as_markdown())


def c_maerkte(args, ctx):
    from qa.sources import prices

    rows = [{"kürzel": k, "symbol": s, "name": n} for k, (s, n) in prices.ALIASES.items()]
    return Result("Märkte", "# Kürzel für Märkte\n\n" + data.table(rows) + "\n\nAußerdem jedes Yahoo-Symbol, FRED:<Reihe>, BBK:…, EZB:…\n")


def c_suche(args, ctx):
    pos, opt = _split(args)
    _need(pos, 1, "/suche <text> [art=aktie|etf|index|future|waehrung|krypto|fonds]")
    return Result(f"Suche {' '.join(pos)}", f"# Symbole: {' '.join(pos)}\n\n" + data.table(data.search(" ".join(pos), opt.get("art", ""))) + "\n")


def c_aufloesen(args, ctx):
    _need(args, 1, "/aufloesen <kürzel oder ticker>")
    names = [n for a in args for n in a.split(",") if n.strip()]
    return Result(f"Symbol {args[0]}", f"# Symbol: {', '.join(names)}\n\n" + data.table([data.resolve(n) for n in names]) + "\n")


def c_abdeckung(args, ctx):
    _need(args, 1, "/abdeckung <symbol>")
    c = data.coverage(args[0])
    return Result(f"Abdeckung {args[0]}", f"# Daten für {c['name']} ({c['symbol']})\n\n" + "\n".join(f"- **{k}:** {v}" for k, v in c.items()) + "\n")


def c_schema(args, ctx):
    names = [a.lower() for a in args] or list(data.SCHEMAS)
    out = ["# Datenschemas", ""]
    for n in names:
        if n not in data.SCHEMAS:
            raise SystemExit(f"Unbekanntes Schema '{n}'. Möglich: {', '.join(data.SCHEMAS)}")
        title, fields = data.SCHEMAS[n]
        out += [f"## {n}: {title}", ""] + [f"- **{k}:** {v}" for k, v in fields.items()] + [""]
    return Result("Schemas", "\n".join(out))


def c_kerzen(args, ctx):
    pos, opt = _split(args)
    _need(pos, 1, "/kerzen <symbol> [intervall=1d|1h|5m|1m …] [tage=31]")
    interval = opt.get("intervall", pos[1] if len(pos) > 1 else "1d")
    days = int(opt.get("tage", pos[2] if len(pos) > 2 else 31))
    df = data.preview_bars(pos[0], interval, days)
    tz = f", Zeit {df.index.tz}" if getattr(df.index, "tz", None) is not None else ""
    text = (f"# Kerzen {pos[0]} ({interval}, letzte {min(days, data.PREVIEW_MAX_DAYS)} Tage, {len(df)} Kerzen{tz})\n\n"
            + data.frame_md(df.tail(60)) + ("\n\n_(nur die letzten 60 gezeigt – alle in der CSV)_" if len(df) > 60 else "") + "\n")
    return Result(f"Kerzen {pos[0]}", text, chart=df[["close"]].rename(columns={"close": pos[0]}), table=df.reset_index())


def c_optionen(args, ctx):
    _need(args, 1, "/optionen <symbol> [verfall JJJJ-MM-TT]")
    exp, calls, puts, all_exp = data.option_chain(args[0], args[1] if len(args) > 1 else None)
    fmt = lambda d: data.table(d.head(25).round(4).to_dict("records"))  # noqa: E731
    text = (f"# Optionen {args[0]} – Verfall {exp}\n\nVerfallstermine: {', '.join(all_exp[:12])}{' …' if len(all_exp) > 12 else ''}\n\n"
            f"## Calls\n\n{fmt(calls)}\n\n## Puts\n\n{fmt(puts)}\n\nAktueller Stand von Yahoo (verzögert), keine Historie.\n")
    return Result(f"Optionen {args[0]}", text, table=pd.concat([calls.assign(art="call"), puts.assign(art="put")]))


def c_nutzung(args, ctx):
    u = data.usage()
    st = workspace.store()
    text = (f"# Nutzung\n\n- **Zwischengespeicherte Dateien:** {u['dateien']} ({u['groesse_mb']} MB), zuletzt {u['zuletzt']}\n"
            f"- **Je Quelle:** {', '.join(f'{k} {v}' for k, v in u['je_quelle'].items()) or '–'}\n"
            f"- **Projekte:** {len(workspace.projects())} · Speicher: {st.kind}\n"
            "- Alle Quellen sind kostenlos; es gibt kein Kontingent außer den Grenzen der Anbieter.\n")
    return Result("Nutzung", text)


def c_anleitung(args, ctx):
    return Result("Daten-Anleitung", data.GUIDE)


def c_merken(args, ctx):
    _need(args, 1, "/merken <text>")
    e = workspace.remember(" ".join(args), ctx.project)
    return Result("Gemerkt", f"Gemerkt [{e['id']}]: {e['text']}\n")


def c_vergessen(args, ctx):
    _need(args, 1, "/vergessen <nummer>")
    ok = workspace.forget(int(args[0]))
    return Result("Vergessen", f"Eintrag {args[0]} {'gelöscht' if ok else 'gibt es nicht'}.\n")


def c_gedaechtnis(args, ctx):
    items = workspace.memory()
    on = workspace.settings()["gedaechtnis_an"]
    text = f"# Gedächtnis ({'an' if on else 'aus'})\n\n" + ("\n".join(f"- [{m['id']}] {m['text']}" + (f" _(Projekt {m['projekt']})_" if m["projekt"] else "")
                                                             for m in items) or "_leer_") + "\n\nLöschen: `/vergessen <nummer>` · Bearbeiten und Ausschalten: Konto → Gedächtnis\n"
    return Result("Gedächtnis", text)


def c_anweisungen(args, ctx):
    text = workspace.instructions().strip()
    return Result("Anweisungen", "# Eigene Anweisungen\n\n" + (text or "_keine_") + "\n\nÄndern nur unter Konto → Anweisungen (der Copilot ändert sie nie).\n")


def c_create(args, ctx):
    raw = " ".join(args)
    m = re.match(r"^([A-Za-z0-9][\w-]*)\s*(.*)$", raw)
    if not m or not m.group(2):
        raise SystemExit("Aufruf: /create-command <name> [Beschreibung ::] /befehl … ; /befehl …   ($1 … $9, $ARGUMENTS für Eingaben)")
    name, rest = m.group(1), m.group(2)
    desc, _, body = rest.partition("::") if "::" in rest else ("", "", rest)
    lines = [ln.strip() for ln in body.split(";") if ln.strip()]
    if name in BUILTINS:
        raise SystemExit(f"/{name} ist ein eingebauter Befehl – anderen Namen wählen")
    path = workspace.save_command(name, desc.strip(), lines, ctx.project)
    return Result(f"Befehl /{name}", f"Befehl **/{name}** gespeichert ({path}):\n\n```\n" + "\n".join(lines) + "\n```\n")


def c_commands(args, ctx):
    lines = ["# Befehle", "", "## Eingebaut", ""] + [f"- `{u}` – {d}" for _, (_, u, d) in sorted(BUILTINS.items())]
    own = workspace.own_commands(ctx.project)
    lines += ["", "## Eigene", ""] + ([f"- `/{n}` – {c['beschreibung'] or ' ; '.join(c['zeilen'])} _({c['ort']})_" for n, c in sorted(own.items())] or
                                      ["_noch keine – mit /create-command anlegen oder aus der Community importieren_"])
    return Result("Befehle", "\n".join(lines) + "\n")


def c_compact(args, ctx):
    """Keep the last two exchanges; everything before becomes one summary line per command."""
    chat = ctx.chat
    if len(chat) <= 4:
        return Result("Zusammenfassen", "Verlauf ist schon kurz.\n")
    old, keep = chat[:-4], chat[-4:]
    lines = ["**Zusammenfassung früherer Schritte**", ""]
    for i, m in enumerate(old):
        if m.get("role") == "user":
            answer = next((x.get("text", "") for x in old[i + 1:i + 2] if x.get("role") == "assistant"), "")
            key = next((ln.strip("#* ") for ln in answer.splitlines() if ln.startswith(("## Einordnung", "## Ergebnis", "**Status"))), "")
            head = next((ln.strip("# ") for ln in answer.splitlines() if ln.startswith("# ")), "")
            lines.append(f"- `{m.get('text', '')[:120]}` → {key or head or answer[:120]}")
    chat[:] = [{"role": "assistant", "text": "\n".join(lines)}] + keep
    return Result("Zusammenfassen", f"{len(old)} ältere Nachrichten zusammengefasst; die letzten {len(keep)} bleiben.\n")


def c_ausfuehren(args, ctx):
    _need(args, 1, "/ausfuehren <datei.py | strategie.json | kette.json>")
    name = args[0]
    if name.endswith(".json"):
        spec = json.loads(file_path(name, ctx).read_text(encoding="utf-8"))
        return c_kette([name], ctx) if "glieder" in spec else c_backtest([name], ctx)
    if not name.endswith(".py"):
        raise SystemExit("Ausführbar sind .py-Skripte und .json-Strategien/-Ketten")
    if is_cloud():
        raise SystemExit("Python-Skripte laufen aus Sicherheitsgründen nur lokal (auf deinem Rechner oder in Claude Code), "
                         "nicht auf der öffentlichen Website.")
    if not ctx.project:
        raise SystemExit("/ausfuehren braucht ein Projekt")
    with tempfile.TemporaryDirectory(prefix="qa_run_") as tmp:
        before = {}
        for f in workspace.files(ctx.project):
            if f.startswith(("chats/", "artefakte/", ".ziele/")):
                continue
            p = Path(tmp) / f
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(workspace.store().read_bytes(f"{ctx.project}/{f}"))
            before[f] = p.stat().st_mtime
        env = os.environ | {"PYTHONPATH": str(ROOT), "MPLBACKEND": "Agg"}
        try:
            proc = subprocess.run([sys.executable, name], cwd=tmp, env=env, capture_output=True, text=True, timeout=RUN_TIMEOUT)
            out, code = (proc.stdout + ("\n" + proc.stderr if proc.stderr else ""))[-20000:], proc.returncode
        except subprocess.TimeoutExpired:
            out, code = f"Abgebrochen nach {RUN_TIMEOUT} Sekunden.", -1
        saved = []
        for p in Path(tmp).rglob("*"):
            rel = p.relative_to(tmp).as_posix()
            if p.is_file() and p.stat().st_size < 2_000_000 and before.get(rel) != p.stat().st_mtime and "__pycache__" not in rel:
                workspace.write(ctx.project, f"ausgabe/{rel}", p.read_bytes())
                saved.append(f"ausgabe/{rel}")
    text = (f"# Ausgeführt: {name} (Exit-Code {code})\n\n```\n{out.strip() or '(keine Ausgabe)'}\n```\n"
            + (f"\nNeue Dateien: {', '.join(saved)}\n" if saved else ""))
    return Result(f"Ausführen {name}", text, ok=code == 0)


BUILTINS: dict[str, tuple[Callable, str, str]] = {
    "ereignis": (c_ereignis, "/ereignis <quelle> [--maerkte …] [--bedingung …]", "Wie reagierten Märkte auf Ereignisse (EZB, Fed, Makro, Kurs-Schocks …)"),
    "earnings": (c_earnings, "/earnings <Ticker,…> [--maerkte …]", "Reaktion auf Quartalszahlen gegenüber dem Konsens"),
    "kette": (c_kette, "/kette <datei.json>", "Kausalkette Glied für Glied prüfen"),
    "backtest": (c_backtest, "/backtest <strategie.json>", "Strategie ehrlich testen (Kosten, Test, Deflated Sharpe, PBO)"),
    "review": (c_review, "/review <datei.json>", "Prüft auf die Fehler, die Ergebnisse am häufigsten ungültig machen"),
    "walk-forward": (c_walk_forward, "/walk-forward <strategie.json> [is=24] [oos=6] [schritt=3]", "Rollierender Walk-Forward mit Sharpe-Verfall"),
    "regime-pnl": (c_regime, "/regime-pnl <strategie.json>", "Gewinn und Verlust nach Marktphase"),
    "overnight": (c_overnight, "/overnight <symbol> [von=2000]", "Über Nacht vs. Handelszeit"),
    "trades": (c_trades, "/trades <trades.csv> [markt=sp500]", "Was machte der Markt vor deinen Einstiegen?"),
    "goal": (c_goal, "/goal <strategie.json> <ziel> · status|weiter|pause|stopp", "Varianten prüfen, bis ein Ziel erreicht ist"),
    "phasen": (c_phasen, "/phasen", "Welche Marktphasen gerade gelten"),
    "kurs": (c_kurs, "/kurs <symbole>", "Letzter Kurs und Veränderung"),
    "katalog": (c_katalog, "/katalog", "Welche Markttreiber gratis messbar sind"),
    "maerkte": (c_maerkte, "/maerkte", "Kürzel für Märkte und Futures"),
    "suche": (c_suche, "/suche <text> [art=…]", "Symbole suchen (Aktien, ETFs, Indizes, Futures, Währungen, Krypto)"),
    "aufloesen": (c_aufloesen, "/aufloesen <kürzel>", "Kürzel in das eindeutige Symbol übersetzen"),
    "abdeckung": (c_abdeckung, "/abdeckung <symbol>", "Welche Daten es für ein Symbol gibt und ab wann"),
    "schema": (c_schema, "/schema [name]", "Felder der Datenschemas erklären"),
    "kerzen": (c_kerzen, "/kerzen <symbol> [intervall] [tage]", "Vorschau: höchstens 500 Kerzen über 31 Tage"),
    "optionen": (c_optionen, "/optionen <symbol> [verfall]", "Aktuelle Optionskette"),
    "nutzung": (c_nutzung, "/nutzung", "Was geladen und gespeichert ist"),
    "anleitung": (c_anleitung, "/anleitung", "Anleitung für Kerzen, Futures, große Abfragen"),
    "merken": (c_merken, "/merken <text>", "Etwas ins Gedächtnis schreiben"),
    "vergessen": (c_vergessen, "/vergessen <nummer>", "Eintrag aus dem Gedächtnis löschen"),
    "gedaechtnis": (c_gedaechtnis, "/gedaechtnis", "Gedächtnis anzeigen"),
    "anweisungen": (c_anweisungen, "/anweisungen", "Eigene Anweisungen anzeigen"),
    "create-command": (c_create, "/create-command <name> [Beschreibung ::] /befehl … ; /befehl …", "Eigenen Befehl anlegen"),
    "commands": (c_commands, "/commands", "Alle Befehle"),
    "compact": (c_compact, "/compact", "Verlauf zusammenfassen"),
    "ausfuehren": (c_ausfuehren, "/ausfuehren <datei>", "Projektdatei ausführen (.py nur lokal, .json überall)"),
}
ALIASES = {"hilfe": "commands", "befehle": "commands", "wf": "walk-forward", "run": "ausfuehren", "ziel": "goal"}


def expand(lines: list[str], args: list[str]) -> list[str]:
    out = []
    for ln in lines:
        ln = ln.replace("$ARGUMENTS", " ".join(shlex.quote(a) for a in args))
        ln = re.sub(r"\$(\d)", lambda m: shlex.quote(args[int(m.group(1)) - 1]) if int(m.group(1)) <= len(args) else "", ln)
        out.append(ln.strip())
    return out


def run(line: str, ctx: Ctx | None = None) -> list[Result]:
    """Run one slash command line; own commands expand to several."""
    ctx = ctx or Ctx()
    line = line.strip()
    if not line.startswith("/"):
        raise SystemExit("Befehle beginnen mit / – Übersicht: /commands")
    try:
        parts = shlex.split(line[1:])
    except ValueError as exc:
        raise SystemExit(f"Befehl nicht lesbar: {exc}")
    if not parts:
        raise SystemExit("Leerer Befehl – Übersicht: /commands")
    name, args = parts[0].lower(), parts[1:]
    name = ALIASES.get(name, name)
    if name in BUILTINS:
        try:
            res = BUILTINS[name][0](args, ctx)
        except SystemExit as exc:
            res = Result(f"/{name}", f"Fehler: {exc}\n", ok=False)
        except Exception as exc:
            res = Result(f"/{name}", f"Fehler: {type(exc).__name__}: {exc}\n", ok=False)
        if ctx.save and ctx.project and res.ok and name not in ("compact", "commands", "merken", "vergessen", "gedaechtnis", "anweisungen", "create-command"):
            try:
                res.artifact = workspace.save_artifact(ctx.project, f"{name} {' '.join(args)}", f"<!-- {line} -->\n{res.text}")
            except Exception:
                pass
        return [res]
    own = workspace.own_commands(ctx.project)
    if name in own:
        if ctx.depth >= MAX_DEPTH:
            return [Result(f"/{name}", "Fehler: eigene Befehle rufen sich zu tief gegenseitig auf\n", ok=False)]
        sub = Ctx(ctx.project, ctx.chat, ctx.save, ctx.depth + 1)
        out = []
        for ln in expand(own[name]["zeilen"], args):
            out += run(ln, sub)
        return out
    return [Result(f"/{name}", f"Fehler: unbekannter Befehl /{name} – Übersicht: /commands\n", ok=False)]
