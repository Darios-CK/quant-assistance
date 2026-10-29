"""Price shocks as events: days on which a market moved unusually strongly (e.g. oil +2 standard deviations).

"Unusual" is measured against the volatility of the year *before* the day, so no later data enters.
Shocks closer than MIN_SPACING trading days to the previous one are dropped: a five-day sell-off is one event.
"""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from qa.sources import prices
from qa.sources.shocks import EventSet

VOL_WINDOW, VOL_MIN = 250, 120
MIN_SPACING = 5
OPEN = {"eu": (ZoneInfo("Europe/Berlin"), 9, 0), "us": (ZoneInfo("America/New_York"), 9, 30), "crypto": (ZoneInfo("UTC"), 0, 1)}


def shocks(closes: pd.Series, unit: str, threshold: float = 2.0, direction: str = "beide") -> pd.DataFrame:
    """(date, z): daily move divided by the standard deviation of the previous VOL_WINDOW daily moves."""
    v = closes.dropna()
    move = v.diff() * 100 if unit == "bp" else v.pct_change() * 100
    vol = move.shift(1).rolling(VOL_WINDOW, min_periods=VOL_MIN).std()
    z = (move / vol).dropna()
    hit = {"hoch": z >= threshold, "runter": z <= -threshold}.get(direction, z.abs() >= threshold)
    picked, last = [], -MIN_SPACING - 1
    pos = {d: k for k, d in enumerate(v.index)}
    for d, val in z[hit].items():
        if pos[d] - last > MIN_SPACING:
            picked.append((d, float(val)))
            last = pos[d]
    return pd.DataFrame(picked, columns=["date", "z"])


TECHNICAL = {
    "sma200_hoch": "schließt über dem 200-Tage-Schnitt (vorher darunter)",
    "sma200_runter": "schließt unter dem 200-Tage-Schnitt (vorher darüber)",
    "hoch52": "neues 52-Wochen-Hoch (erstes seit mindestens einem Monat)",
    "tief52": "neues 52-Wochen-Tief (erstes seit mindestens einem Monat)",
}
CLOSE_TIME = {"eu": (ZoneInfo("Europe/Berlin"), 17, 35), "us": (ZoneInfo("America/New_York"), 16, 5), "crypto": (ZoneInfo("UTC"), 23, 59)}


def crossings(c: pd.Series, kind: str) -> list[pd.Timestamp]:
    if kind in ("sma200_hoch", "sma200_runter"):
        above = c > c.rolling(200).mean()
        valid = c.rolling(200).mean().notna()
        flip = above & ~above.shift(1, fill_value=False) if kind == "sma200_hoch" else ~above & above.shift(1, fill_value=False)
        hits = flip & valid & valid.shift(1, fill_value=False)
    elif kind in ("hoch52", "tief52"):
        prior = c.shift(1).rolling(250, min_periods=250)
        new = c > prior.max() if kind == "hoch52" else c < prior.min()
        recent = new.shift(1, fill_value=False).rolling(21, min_periods=1).max().astype(bool)
        hits = new & ~recent
    else:
        raise SystemExit(f"Unbekannte Technik-Marke '{kind}'. Möglich: {', '.join(TECHNICAL)}")
    return list(c.index[hits.to_numpy()])


def technical(symbol: str, kind: str) -> EventSet:
    symbol, name = prices.resolve(symbol)
    days = crossings(prices.closes(symbol), kind)
    tz, hh, mm = CLOSE_TIME[prices.market(symbol)]
    # the signal exists only at the close: every market counts from the next trading day
    ts = pd.to_datetime([datetime(d.year, d.month, d.day, hh, mm, tzinfo=tz) for d in days], utc=True)
    return EventSet(f"{name} {TECHNICAL[kind]}", "–", "Technische Marke (alle Ereignisse gleich, getestet wird die Ø Reaktion danach)",
                    f"Kurse {symbol}", pd.DataFrame({"ts": ts, "surprise": 1.0}),
                    ["Das Signal steht erst zum Schlusskurs fest; gemessen wird ab dem nächsten Handelstag."])


def events(symbol: str, threshold: float = 2.0, direction: str = "beide") -> EventSet:
    symbol, name = prices.resolve(symbol)
    unit, market = prices.unit(symbol), prices.market(symbol)
    df = shocks(prices.closes(symbol), unit, threshold, direction)
    tz, hh, mm = OPEN[market]
    # the shock happens during its day: every market counts that day from its previous close
    ts = [datetime(d.year, d.month, d.day, hh, mm, tzinfo=tz) for d in df["date"]]
    out = pd.DataFrame({"ts": pd.to_datetime(ts, utc=True), "surprise": df["z"].to_numpy(float)})
    side = {"hoch": "nach oben", "runter": "nach unten"}.get(direction, "in beide Richtungen")
    return EventSet(f"Schock-Tage {name}", "σ", f"Tagesbewegung {name} in Standardabweichungen des Vorjahres (Schwelle {threshold:g}σ, {side})",
                    f"Kurse {symbol} (Yahoo/FRED)", out,
                    [f"Schock = Tagesbewegung von mindestens {threshold:g} Standardabweichungen; Schocks innerhalb von {MIN_SPACING} Handelstagen zählen einmal.",
                     "Der Reaktionstag ist der Schock-Tag selbst: gleichzeitige Bewegung, nicht unbedingt Ursache und Wirkung. "
                     "Die längeren Horizonte enthalten diesen Tag; der Unterschied zum Reaktionstag ist das, was danach noch folgte."])
