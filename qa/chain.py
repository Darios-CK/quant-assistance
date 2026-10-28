"""Chain check: a chain of effects written down as a hypothesis, every link measured against the trigger.

The AI (or the user) may think as far as it likes – oil up → freight costs → truckers → their tyre suppliers.
This module decides which links the data actually show.  Every link is measured directly against the trigger
events (market-adjusted for single stocks and sector ETFs), on all horizons, and all tests of one chain share one
Benjamini–Hochberg correction.

Chain file (JSON):
{
  "name": "Ölpreis-Schock",
  "frage": "Was passiert, wenn Öl stark steigt?",
  "ausloeser": {"quelle": "kurs:CL=F", "schwelle": 2, "richtung": "hoch"},
  "von": "2008", "bis": null, "horizonte": [0, 5, 20],
  "glieder": [
    {"id": "airlines", "symbol": "JETS", "name": "US-Airlines", "nach": "ausloeser",
     "erwartung": "-", "warum": "Kerosin ist der größte Kostenblock"},
    {"id": "goodyear", "symbol": "GT", "nach": "trucking", "erwartung": "?", "warum": "…"}
  ]
}
erwartung: "+" = moves in the direction of the trigger surprise, "-" = against it, "?" = no expectation.
marktbereinigt (per link, default true): single stocks and sector ETFs net of their market index.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from qa import assets as asset_loader
from qa import triggers
from qa.report import horizon, num, p_text
from qa.study import HORIZONS, bh_q, study, verdict

ROOT_ID = "ausloeser"


def _filter(df: pd.DataFrame, von, bis) -> pd.DataFrame:
    if von:
        df = df[df["ts"] >= pd.Timestamp(f"{von}-01-01" if len(str(von)) == 4 else str(von), tz="UTC")]
    if bis:
        df = df[df["ts"] <= pd.Timestamp(f"{bis}-12-31" if len(str(bis)) == 4 else str(bis), tz="UTC")]
    return df


def status(verdict_: str, value: float, expect: str) -> str:
    if verdict_ == "zu wenig Fälle":
        return "⬜ zu wenig Fälle"
    if np.isnan(value) or verdict_ == "kein Muster":
        return "⬜ nicht nachweisbar"
    if expect not in ("+", "-"):
        direction = "gleichläufig" if value > 0 else "gegenläufig"
        return f"✅ Zusammenhang belegt ({direction})" if verdict_ == "belastbar" else f"〰️ Tendenz ({direction})"
    matches = (value > 0) == (expect == "+")
    if verdict_ == "belastbar":
        return "✅ bestätigt" if matches else "❌ Gegenteil belegt"
    return "〰️ Tendenz" if matches else "〰️ Tendenz zum Gegenteil"


def evaluate(summary: pd.DataFrame, one_sided: bool) -> pd.DataFrame:
    """Pick the test (average reaction for one-sided triggers, slope otherwise), correct all p-values together."""
    s = summary.copy()
    if one_sided:
        s["value"], s["p_used"], s["stable_used"] = s.get("mean"), s.get("mean_p"), s.get("mean_stable")
    else:
        s["value"], s["p_used"], s["stable_used"] = s["slope_sd"], s["p"], s["stable"]
    s["q_used"] = bh_q(s["p_used"].astype(float).tolist())
    s["verdict_used"] = [verdict(n, p, q) for n, p, q in zip(s["n"], s["p_used"].astype(float), s["q_used"])]
    return s


def run(path: Path) -> tuple[str, pd.DataFrame]:
    spec = json.loads(Path(path).read_text(encoding="utf-8"))
    trig = spec["ausloeser"]
    source = trig["quelle"]
    opts = {k: v for k, v in trig.items() if k != "quelle"}
    ev = triggers.load(source, **opts)
    df = _filter(ev.df, spec.get("von"), spec.get("bis"))
    if df.empty:
        raise SystemExit("Keine Auslöser-Ereignisse im gewählten Zeitraum.")
    links = spec["glieder"]
    ids = {l["id"] for l in links}
    for l in links:
        if l.get("nach", ROOT_ID) not in ids | {ROOT_ID}:
            raise SystemExit(f"Glied {l['id']}: Vorgänger '{l['nach']}' gibt es nicht.")
    items = [{"symbol": l["symbol"], "key": l["id"], "name": l.get("name"), "adjust": l.get("marktbereinigt", True)} for l in links]
    loaded, notes = asset_loader.load(items, (df["ts"].min(), df["ts"].max()))
    horizons = tuple(spec.get("horizonte") or HORIZONS)
    summary, per_event = study(df, loaded, horizons)
    one = triggers.one_sided(source, **opts)
    s = evaluate(summary, one)
    return render(spec, ev, df, links, loaded, s, one, notes, horizons), per_event


def render(spec, ev, df, links, loaded, s, one, notes, horizons) -> str:
    info = {a["key"]: a for a in loaded}
    best = {}
    for key, g in s.groupby("asset"):
        g = g.dropna(subset=["p_used"])
        if len(g):
            best[key] = g.loc[g["p_used"].astype(float).idxmin()]
    measure = "Ø Reaktion" if one else "je typ. Überraschung"
    lines = [f"# Kettenprüfung: {spec.get('name', '')}", ""]
    if spec.get("frage"):
        lines += [f"> {spec['frage']}", ""]
    lines += [
        f"- **Auslöser:** {ev.name} – {ev.measure}",
        f"- **Ereignisse:** {len(df)} von {df['ts'].min():%d.%m.%Y} bis {df['ts'].max():%d.%m.%Y}",
        f"- **Test:** {'Ø Reaktion ≠ 0 (alle Auslöser zeigen in dieselbe Richtung)' if one else 'Steigung Reaktion ~ Größe der Überraschung'}; "
        f"{len(s)} Tests ({len(loaded)} Glieder × {len(horizons)} Horizonte), gemeinsam korrigiert (q).",
        f"- **Quelle:** {ev.source}{'' if 'Kurse' in ev.source else ' · Kurse Yahoo/FRED'} · Erstellt {datetime.now():%d.%m.%Y %H:%M}",
        "- **Gemessen** wird pro Glied der Horizont mit dem kleinsten p-Wert; alle Horizonte stehen unten in der Tabelle und zählen in der Korrektur mit.",
        "",
        "Erwartung ↑ = bewegt sich mit dem Auslöser, ↓ = dagegen. Einzelaktien und Sektor-ETFs marktbereinigt (gegen S&P 500 bzw. DAX).",
        "",
        "## Kette",
        "",
    ]
    arrows = {"+": "↑", "-": "↓"}

    def walk(parent: str, depth: int):
        for l in [l for l in links if l.get("nach", ROOT_ID) == parent]:
            a, r = info.get(l["id"]), best.get(l["id"])
            label = (a["label"] if a else l.get("name") or l["symbol"]) + f" ({l['symbol']})"
            if a is None or r is None:
                lines.append(f"{'  ' * depth}- ⬜ **{label}** · keine Daten")
            else:
                st_ = status(r["verdict_used"], float(r["value"]), l.get("erwartung", "?"))
                unit = "%" if r["unit"] == "pct" else " Bp"
                stable = {True: "stabil", False: "nicht stabil"}.get(r["stable_used"], "–")
                lines.append(
                    f"{'  ' * depth}- {st_} **{label}** · erwartet {arrows.get(l.get('erwartung', '?'), '?')} · "
                    f"{measure} {num(float(r['value']), 2, True, unit)} ({horizon(int(r['h']))}, n={int(r['n'])}, "
                    f"q={p_text(float(r['q_used']))}, {stable}) — *{l.get('warum', '')}*")
                parent_r = best.get(parent)
                if parent != ROOT_ID and st_.startswith("✅") and (parent_r is None or not str(parent_r["verdict_used"]) == "belastbar"):
                    lines.append(f"{'  ' * (depth + 1)}- Hinweis: reagiert, obwohl der Vorgänger nicht belegt ist – Wirkung läuft vermutlich über einen anderen Weg.")
            walk(l["id"], depth + 1)

    walk(ROOT_ID, 0)
    lines += ["", "## Alle Messungen", "",
              f"| Glied | Horizont | Fälle | {measure} | p | q | Hälften gleich | Einordnung |",
              "|---|---|---:|---:|---:|---:|---|---|"]
    for r in s.itertuples(index=False):
        a = info[r.asset]
        unit = "%" if r.unit == "pct" else " Bp"
        stable = {True: "ja", False: "nein"}.get(r.stable_used, "–")
        lines.append(f"| {a['label']}{' (bereinigt)' if r.adjusted else ''} | {horizon(r.h)} | {r.n} | {num(float(r.value), 2, True, unit)} | "
                     f"{p_text(float(r.p_used))} | {p_text(float(r.q_used))} | {stable} | {r.verdict_used} |")
    lines += ["", "## Hinweise", ""] + [f"- {n}" for n in ev.notes + notes] + [
        "- Jedes Glied wird direkt gegen den Auslöser gemessen. Ein bestätigtes Glied zeigt einen Zusammenhang, nicht den Mechanismus aus „warum“ – der bleibt eine Begründung, die zu prüfen ist (Geschäftsbericht, Umsatzanteile).",
        "- „Hälften gleich“: Die Richtung war in der ersten und zweiten Hälfte der Ereignisse dieselbe. Nein = Muster hängt an einer Phase.",
        "- Yahoo: von der Börse genommene Firmen fehlen (Survivorship Bias); Tagesdaten enthalten andere Nachrichten desselben Tages.",
    ]
    return "\n".join(lines) + "\n"
