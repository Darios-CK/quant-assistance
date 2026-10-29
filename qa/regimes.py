"""Market phases and combinations of events – "ECB surprise AND VIX high", "CPI WITHOUT an FOMC meeting that week".

Every phase is known before the event: it is computed from the close of the trading day *before* the event day,
and thresholds that move (credit stress) only use the past.  Combinations filter one event set by another:
'zusammen' keeps events with an event of the other source within ±fenster calendar days, 'ohne' drops them.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from qa.sources import prices

# name: (description, function closes -> boolean Series of the state at each close)
PHASES = {
    "vix_hoch": ("VIX über 25 (Angst)", lambda: prices.closes("^VIX") > 25),
    "vix_niedrig": ("VIX unter 15 (Ruhe)", lambda: prices.closes("^VIX") < 15),
    "trend_auf": ("S&P 500 über seinem 200-Tage-Schnitt", lambda: _above_ma("^GSPC", 200)),
    "trend_ab": ("S&P 500 unter seinem 200-Tage-Schnitt", lambda: ~_above_ma("^GSPC", 200)),
    "dax_trend_auf": ("DAX über seinem 200-Tage-Schnitt", lambda: _above_ma("^GDAXI", 200)),
    "dax_trend_ab": ("DAX unter seinem 200-Tage-Schnitt", lambda: ~_above_ma("^GDAXI", 200)),
    "zinskurve_invers": ("US-Zinskurve invers (10J minus 2J unter 0)", lambda: prices.closes("FRED:T10Y2Y") < 0),
    "zinskurve_normal": ("US-Zinskurve normal (10J minus 2J über 0)", lambda: prices.closes("FRED:T10Y2Y") >= 0),
    "kreditstress": ("Kreditspread Baa über dem 80-%-Wert der letzten 3 Jahre", lambda: _credit_stress()),
    "kein_kreditstress": ("Kreditspread Baa unter dem 80-%-Wert der letzten 3 Jahre", lambda: ~_credit_stress()),
    "zinsen_hoch": ("US-Leitzins (Fed Funds) über 3 %", lambda: prices.closes("FRED:DFF") > 3),
    "zinsen_niedrig": ("US-Leitzins (Fed Funds) unter 1 %", lambda: prices.closes("FRED:DFF") < 1),
}


def _above_ma(symbol: str, days: int) -> pd.Series:
    c = prices.closes(symbol)
    ma = c.rolling(days).mean()
    return (c > ma).where(ma.notna(), False)


def _credit_stress() -> pd.Series:
    s = prices.closes("FRED:BAA10Y")
    limit = s.rolling(756, min_periods=250).quantile(0.8).shift(1)   # threshold from the past 3 years only
    return (s > limit).where(limit.notna(), False)


def state(name: str) -> pd.Series:
    """Boolean phase per trading day, as known at the close of that day."""
    if name not in PHASES:
        raise SystemExit(f"Unbekannte Marktphase '{name}'. Möglich: {', '.join(PHASES)}")
    return PHASES[name][1]().astype(bool).sort_index()


def known_before(s: pd.Series, ts: pd.Series) -> np.ndarray:
    """Value of a daily state at the last close strictly before each event's (local New York) date."""
    days = ts.dt.tz_convert("America/New_York").dt.tz_localize(None).dt.normalize()
    idx = s.index.searchsorted(days, side="left") - 1                # last close before the event day
    out = np.full(len(days), False)
    ok = idx >= 0
    out[ok] = s.to_numpy()[idx[ok]]
    return out


def filter_phases(events: pd.DataFrame, names: list[str]) -> tuple[pd.DataFrame, list[str]]:
    """Keep events during which ALL named phases held."""
    keep = np.full(len(events), True)
    labels = []
    for n in names:
        keep &= known_before(state(n), events["ts"])
        labels.append(PHASES[n][0])
    return events[keep], labels


def near(events: pd.DataFrame, other: pd.DataFrame, window_days: int) -> np.ndarray:
    """True where an event of 'other' lies within ±window_days calendar days."""
    a = events["ts"].to_numpy(dtype="datetime64[ns]")
    b = np.sort(other["ts"].to_numpy(dtype="datetime64[ns]"))
    w = np.timedelta64(window_days, "D") + np.timedelta64(12, "h")
    lo, hi = np.searchsorted(b, a - w, "left"), np.searchsorted(b, a + w, "right")
    return hi > lo


def current() -> list[dict]:
    """Which phases hold right now (latest close) – for 'what did history do in a situation like today?'."""
    out = []
    for name, (desc, _) in PHASES.items():
        try:
            s = state(name)
            out.append({"phase": name, "beschreibung": desc, "aktiv": bool(s.iloc[-1]), "stand": f"{s.index[-1]:%d.%m.%Y}"})
        except Exception as exc:
            out.append({"phase": name, "beschreibung": desc, "aktiv": None, "stand": f"keine Daten: {exc}"})
    return out
