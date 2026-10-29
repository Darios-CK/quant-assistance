"""Company actions from Yahoo: stock splits and dividend ex-dates (personal use only).

Splits and ex-dates are announced in advance, so the event is known before the day; the reaction counts on the
day itself.  Prices are adjusted for both, so the mechanical drop on the ex-date does not show as a loss.
"""

from __future__ import annotations

import warnings
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd

from qa.cache import cached
from qa.sources.shocks import EventSet

NEW_YORK = ZoneInfo("America/New_York")


def _actions(symbol: str) -> pd.DataFrame:
    import yfinance as yf

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        a = yf.Ticker(symbol).actions
    if a is None or a.empty:
        return pd.DataFrame(columns=["date", "dividend", "split"])
    idx = a.index.tz_localize(None) if a.index.tz is not None else a.index
    col = lambda name: a[name].to_numpy(float) if name in a else [0.0] * len(a)   # noqa: E731  (column may be missing)
    return pd.DataFrame({"date": idx.normalize(), "dividend": col("Dividends"), "split": col("Stock Splits")})


def events(kind: str, symbol: str) -> EventSet:
    symbol = symbol.upper()
    a = cached(f"actions_{symbol}", lambda: _actions(symbol), max_age_h=24)
    col, label = {"split": ("split", "Aktiensplits"), "dividende": ("dividend", "Dividenden-Ex-Tage")}[kind]
    rows = a[a[col] > 0]
    if rows.empty:
        raise SystemExit(f"Yahoo kennt keine {label} für {symbol}.")
    ts = pd.to_datetime([datetime(d.year, d.month, d.day, 9, 30, tzinfo=NEW_YORK) for d in rows["date"]], utc=True)
    surprise = rows[col].to_numpy(float) if kind == "split" else pd.Series(rows[col]).pct_change().fillna(0).to_numpy() * 100
    measure = ("Split-Verhältnis (z. B. 4 = 4:1)" if kind == "split"
               else "Änderung der Dividende gegenüber der vorigen Zahlung in % (Erhöhung > 0, Kürzung < 0)")
    return EventSet(f"{label} {symbol}", "x" if kind == "split" else "%", measure, "Yahoo Finance (Kapitalmaßnahmen)",
                    pd.DataFrame({"ts": ts, "surprise": surprise}),
                    ["Kurse sind um Splits und Dividenden bereinigt; gemessen wird die Bewegung darüber hinaus."])
