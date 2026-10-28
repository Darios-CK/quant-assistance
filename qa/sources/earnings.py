"""Company earnings with the analysts' consensus (Yahoo Finance via yfinance): real surprises, free.

Surprise = (reported EPS − consensus EPS) / |consensus| in percent.  With a consensus near zero this explodes,
so it is capped at ±CAP percent; the grouping into thirds is unaffected by the cap.
Yahoo gives the time of the release (before the open / after the close), which decides the reaction day.
"""

from __future__ import annotations

import warnings

import numpy as np
import pandas as pd

from qa.cache import cached
from qa.sources.shocks import EventSet

CAP = 100.0


def _fetch(symbol: str) -> pd.DataFrame:
    import yfinance as yf

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        d = yf.Ticker(symbol).get_earnings_dates(limit=100)
    if d is None or d.empty:
        raise ValueError(f"Yahoo liefert keine Gewinntermine für {symbol}")
    d = d.rename(columns={"EPS Estimate": "estimate", "Reported EPS": "reported", "Surprise(%)": "surprise_yahoo"})
    d = d.dropna(subset=["estimate", "reported"])
    return pd.DataFrame({"ts": d.index.tz_convert("UTC"), "estimate": d["estimate"].to_numpy(float),
                         "reported": d["reported"].to_numpy(float)}).sort_values("ts").reset_index(drop=True)


def surprise_pct(reported: np.ndarray, estimate: np.ndarray) -> np.ndarray:
    with np.errstate(divide="ignore", invalid="ignore"):
        s = (reported - estimate) / np.abs(estimate) * 100
    s = np.where(np.abs(estimate) < 1e-9, np.sign(reported - estimate) * CAP, s)
    return np.clip(s, -CAP, CAP)


def events(symbol: str) -> EventSet:
    d = cached(f"earnings_{symbol}", lambda: _fetch(symbol), max_age_h=24)
    out = pd.DataFrame({"ts": pd.to_datetime(d["ts"], utc=True), "surprise": surprise_pct(d["reported"].to_numpy(), d["estimate"].to_numpy()),
                        "estimate": d["estimate"], "reported": d["reported"], "symbol": symbol})
    return EventSet(f"Quartalszahlen {symbol}", "%", "Gewinn je Aktie gegenüber Analysten-Konsens in % (begrenzt auf ±100 %)",
                    "Yahoo Finance (Gewinntermine mit Konsens)", out,
                    ["Konsens laut Yahoo; ältere Quartale können lückenhaft sein.",
                     "Überraschung nur beim Gewinn je Aktie – Umsatz und Ausblick fehlen, bewegen den Kurs aber oft stärker."])
