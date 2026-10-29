"""Markdown report of an event study (German, numbers with decimal comma)."""

from __future__ import annotations

import math
from datetime import datetime

import numpy as np
import pandas as pd

from qa.sources.shocks import EventSet
from qa.study import MIN_EVENTS

UNIT = {"pct": "%", "bp": " Bp"}


def num(v: float, digits: int = 2, sign: bool = False, unit: str = "") -> str:
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "–"
    s = f"{v:+.{digits}f}" if sign else f"{v:.{digits}f}"
    return s.replace(".", ",") + unit


def p_text(p: float) -> str:
    if p is None or math.isnan(p):
        return "–"
    return "<0,001" if p < 0.001 else num(p, 3)


def horizon(h: int) -> str:
    return {0: "Reaktionstag", 5: "1 Woche", 20: "1 Monat"}.get(h, f"{h} Tage")


def group(mean: float, up: float, n: int, unit: str) -> str:
    if not n:
        return "–"
    return f"{num(mean, 2, True, unit)} ({num(up, 0)} % ↑, n={n})"


def render(ev: EventSet, summary: pd.DataFrame, used: pd.DataFrame, filters: list[str], notes: list[str] | None = None) -> str:
    sd = float(np.std(used["surprise"], ddof=1)) if len(used) > 1 else float("nan")
    one = bool(summary.get("one_sided", pd.Series([False])).any())
    first, last = used["ts"].min(), used["ts"].max()
    lines = [
        f"# Ereignis-Analyse: {ev.name}",
        "",
        f"- **Überraschung:** {ev.measure}",
        f"- **Ereignisse:** {len(used)} von {first:%d.%m.%Y} bis {last:%d.%m.%Y}"
        + (f" · Filter: {', '.join(filters)}" if filters else ""),
        (f"- **Test:** Ø Reaktion gegenüber der normalen Bewegung an allen Tagen (alle Ereignisse zeigen in dieselbe Richtung)" if one
         else f"- **Typische Überraschung (1 Standardabweichung):** {num(sd, 2)} {ev.unit}"),
        f"- **Quelle:** {ev.source} · Kurse: Yahoo Finance, FRED, Bundesbank, EZB (Tageswerte)",
        f"- **Erstellt:** {datetime.now():%d.%m.%Y %H:%M}",
        "",
        "Lesehilfe: *Je typ. Überraschung* = wie stark sich der Markt im Schnitt bewegte, wenn die Überraschung um eine "
        "typische Größe höher ausfiel. *Oberes/unteres Drittel* = Ereignisse mit den größten bzw. kleinsten Überraschungen "
        "(Ø Bewegung, Anteil steigend, Fälle). *Normal* = durchschnittliche Bewegung über gleich viele Tage ohne Bezug "
        f"zum Ereignis. *q* = p-Wert nach Korrektur für alle Tests dieser Tabelle; belastbar heißt q < 0,10 und mindestens {MIN_EVENTS} Fälle. "
        "*Hälften gleich* = Richtung in der ersten und zweiten Hälfte der Ereignisse dieselbe. *(bereinigt)* = Einzelaktie/Sektor abzüglich "
        "Beta × Index (S&P 500 bzw. DAX), Beta aus dem Jahr vor dem Ereignis.",
        "",
        f"| Markt | Horizont | Fälle | {'Ø Reaktion' if one else 'Je typ. Überraschung'} | Oberes Drittel | Unteres Drittel | Normal | p | q | Hälften gleich | Einordnung |",
        "|---|---|---:|---:|---|---|---:|---:|---:|---|---|",
    ]
    for r in summary.itertuples(index=False):
        u = UNIT[r.unit]
        stable = {True: "ja", False: "nein"}.get(getattr(r, "stable", None), "–")
        hi = "–" if one else group(getattr(r, 'hi_mean', np.nan), getattr(r, 'hi_up', np.nan), getattr(r, 'hi_n', 0), u)
        lo = "–" if one else group(getattr(r, 'lo_mean', np.nan), getattr(r, 'lo_up', np.nan), getattr(r, 'lo_n', 0), u)
        lines.append(
            f"| {r.asset}{' (bereinigt)' if getattr(r, 'adjusted', False) else ''} | {horizon(r.h)} | {r.n} | {num(r.slope_sd, 2, True, u)} | "
            f"{hi} | {lo} | "
            f"{num(r.normal, 2, True, u)} | {p_text(r.p)} | {p_text(r.q)} | {stable} | {r.verdict} |")
    lines += ["", "## Hinweise", ""]
    lines += [f"- {n}" for n in ev.notes + (notes or [])]
    lines += [
        "- Reaktion = Schlusskurs vor dem Ereignis bis Schlusskurs am Reaktionstag (+ Horizont). Ereignisse nach "
        "Börsenschluss (z. B. Fed für europäische Märkte) zählen ab dem nächsten Handelstag.",
        "- Tagesdaten: Am selben Tag erschienen oft weitere Nachrichten; je länger der Horizont, desto mehr anderes steckt in der Bewegung.",
        "- Yahoo: inoffiziell, nur privat; von der Börse genommene Firmen fehlen; Futures ohne Roll-Bereinigung.",
        "- Vergangene Reaktionen sind keine Vorhersage. Muster können sich mit dem Zinsumfeld ändern (z. B. Negativzinsen 2014–2022): mit --von/--bis prüfen.",
    ]
    return "\n".join(lines) + "\n"
