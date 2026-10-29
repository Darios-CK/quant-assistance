"""Events from any adapter series: unusually large changes (z-score against the series' own past), stamped with the
time the value became PUBLIC (release rule of the series) – not the observation date.

    faktor:<alias|A:adapter:series>   options: schwelle (σ, default 2), richtung = hoch | runter | beide
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from qa.adapters import split
from qa.adapters.base import release_times
from qa.sources import prices
from qa.sources.shocks import EventSet

WINDOW = {"d": (250, 120), "w": (104, 52), "m": (60, 36)}     # past observations for the typical change
MIN_SPACING = {"d": 5, "w": 1, "m": 0}


def change(values: pd.Series, unit: str) -> pd.Series:
    return values.diff() * 100 if unit == "bp" else values.pct_change() * 100


def zscores(values: pd.Series, unit: str, freq: str = "d") -> pd.Series:
    win, min_obs = WINDOW.get(freq, WINDOW["d"])
    move = change(values.dropna(), unit)
    vol = move.shift(1).rolling(win, min_periods=min_obs).std()        # only earlier observations
    return (move / vol).replace([np.inf, -np.inf], np.nan).dropna()


def events(name: str, threshold: float = 2.0, direction: str = "beide") -> EventSet:
    symbol, label = prices.resolve(name)
    if not symbol.upper().startswith("A:"):
        raise SystemExit(f"faktor: braucht eine Datenreihe (Kürzel wie epu oder A:<quelle>:<reihe>), nicht '{name}'")
    adapter, series = split(symbol)
    meta = adapter.meta(series)
    v = adapter.load(series)["value"]
    z = zscores(v, meta["unit"], meta["freq"])
    hit = {"hoch": z >= threshold, "runter": z <= -threshold}.get(direction, z.abs() >= threshold)
    picked, last = [], -10**9
    pos = {d: k for k, d in enumerate(z.index)}
    for d, val in z[hit].items():
        if pos[d] - last > MIN_SPACING.get(meta["freq"], 0):
            picked.append((d, float(val)))
            last = pos[d]
    dates = pd.DatetimeIndex([d for d, _ in picked])
    ts = release_times(dates, meta["release"]) if len(dates) else pd.DatetimeIndex([], tz="UTC")
    df = pd.DataFrame({"ts": ts, "surprise": [s for _, s in picked], "beobachtet": dates})
    notes = [f"Ereigniszeit = Veröffentlichung ({'während des Tages, wie ein Kurs' if meta['release'] == 'markt' else meta['release']}); "
             "die Schwelle nutzt nur frühere Werte."]
    if meta.get("note"):
        notes.append(meta["note"])
    return EventSet(f"{meta['name']}: Veränderung ≥ {threshold:g} σ ({direction})", "σ",
                    "Veränderung in Standardabweichungen der früheren Veränderungen", f"{adapter.title} {series}", df, notes)
