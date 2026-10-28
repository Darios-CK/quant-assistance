"""Data checks before any analysis: outliers, frozen prices, gaps, impossible values.

Problems are reported, never silently repaired – the user decides whether a result built on them still holds.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

OUTLIER_PCT = 25.0       # one-day move above this (prices): split error, ticker change or a real crash – check
OUTLIER_BP = 75.0        # one-day move above this (rates, basis points)
STALE_RUN = 5            # this many identical closes in a row: price probably not updated
GAP_DAYS = 10            # calendar days without a close (longer than any holiday)


def check(closes: pd.Series, unit: str, name: str) -> list[str]:
    s = closes.dropna()
    if len(s) < 2:
        return [f"{name}: zu wenige Kurse ({len(s)})."]
    notes, v = [], s.to_numpy(float)
    if unit == "pct":
        if (v <= 0).any():
            notes.append(f"{name}: {int((v <= 0).sum())} Kurse ≤ 0 – Datenfehler.")
        move = np.abs(np.diff(v) / v[:-1] * 100)
        limit, label = OUTLIER_PCT, "%"
    else:
        move = np.abs(np.diff(v) * 100)
        limit, label = OUTLIER_BP, " Bp"
    big = s.index[1:][move > limit]
    if len(big):
        days = ", ".join(f"{d:%d.%m.%Y}" for d in big[:3]) + (" …" if len(big) > 3 else "")
        notes.append(f"{name}: {len(big)} Tag(e) mit Bewegung über {limit:g}{label} ({days}) – Split, Tickerwechsel oder echter Crash? prüfen.")
    same = np.r_[False, np.diff(v) == 0]
    runs = pd.Series(same).groupby((~pd.Series(same)).cumsum()).sum()
    if (runs >= STALE_RUN - 1).any():
        notes.append(f"{name}: Kurs mehrfach {STALE_RUN}+ Tage unverändert – eingefrorene Daten möglich.")
    gaps = np.diff(s.index.to_numpy()).astype("timedelta64[D]").astype(int)
    if (gaps > GAP_DAYS).any():
        notes.append(f"{name}: {int((gaps > GAP_DAYS).sum())} Datenlücke(n) über {GAP_DAYS} Tage.")
    return notes
