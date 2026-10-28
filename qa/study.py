"""Event study on daily closes: how did a market move after events, depending on the size of the surprise?

For every event the reaction runs from the last close *before* the event to the close h trading days after the
reaction day (h = 0: the reaction day itself).  An event after a market's close counts from the next trading day.

Single stocks and sector ETFs are measured *market-adjusted* (abnormal return): their move minus beta × the
index move, with beta estimated on the year before the event (ending BETA_GAP days earlier, so the event itself
never enters its own beta).  Otherwise every weak market day would look like a "reaction".

Per market and horizon:
  - slope of reaction on surprise (OLS), scaled to one typical surprise (one standard deviation)
  - upper and lower third of surprises: mean, median, share of rising cases, Welch test between the two
  - the market's normal move over the same number of days, for comparison
  - whether the slope has the same sign in the first and the second half of the events (stability)
With many markets and horizons some results look significant by chance, so every p-value gets a
Benjamini–Hochberg q-value; "belastbar" needs q < 0.10 and at least MIN_EVENTS events.
"""

from __future__ import annotations

from datetime import datetime, time
from datetime import timezone as dt_tz
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
from scipy import stats as st

HORIZONS = (0, 5, 20)
MIN_EVENTS = 20
MAX_GAP_DAYS = 5          # no close within this many days of the event: data gap, event skipped
BETA_WINDOW, BETA_GAP, BETA_MIN = 250, 10, 120
CLOSE = {"eu": (ZoneInfo("Europe/Berlin"), time(17, 30)), "us": (ZoneInfo("America/New_York"), time(16, 0)),
         "crypto": (dt_tz.utc, time(23, 59, 59)),
         "ecb_fix": (ZoneInfo("Europe/Berlin"), time(14, 15))}   # ECB reference rates: an ECB decision at 14:15 counts from the next day


def reaction_start(dates: pd.DatetimeIndex, ts: pd.Timestamp, market: str) -> int | None:
    """Index of the first close that can contain the reaction to an event at ts (UTC)."""
    tz, close = CLOSE[market]
    local = ts.tz_convert(tz)
    day = pd.Timestamp(local.date())
    after_close = local.to_pydatetime() >= datetime.combine(local.date(), close, tzinfo=tz)
    i = int(dates.searchsorted(day, side="right" if after_close else "left"))
    if i >= len(dates) or i == 0 or (dates[i] - day).days > MAX_GAP_DAYS:
        return None
    return i


def _move(a: float, b: float, unit: str) -> float:
    return (b - a) * 100 if unit == "bp" else (b / a - 1) * 100


def _beta(ra: np.ndarray, rb: np.ndarray, i: int) -> float:
    """Beta from daily returns strictly before the event window (returns index k = move from close k-1 to k)."""
    lo, hi = max(1, i - BETA_GAP - BETA_WINDOW), i - BETA_GAP
    a, b = ra[lo:hi], rb[lo:hi]
    ok = ~(np.isnan(a) | np.isnan(b))
    if ok.sum() < BETA_MIN or np.var(b[ok]) == 0:
        return np.nan
    return float(np.cov(a[ok], b[ok])[0, 1] / np.var(b[ok], ddof=1))


def reactions(events: pd.DataFrame, closes: pd.Series, unit: str, market: str,
              horizons: tuple[int, ...] = HORIZONS, bench: pd.Series | None = None) -> pd.DataFrame:
    """One row per event: surprise and the move after h days for each horizon (NaN where data runs out).
    With bench: market-adjusted move (move − beta × bench move over the same closes)."""
    if bench is not None:
        both = pd.concat([closes.rename("a"), bench.rename("b")], axis=1, join="inner").dropna()
        closes, b = both["a"], both["b"].to_numpy(float)
    dates, values = closes.index, closes.to_numpy(float)
    if bench is not None:
        ra = np.r_[np.nan, values[1:] / values[:-1] - 1]
        rb = np.r_[np.nan, b[1:] / b[:-1] - 1]
    rows = []
    for ev in events.itertuples(index=False):
        i = reaction_start(dates, ev.ts, market)
        row = {"ts": ev.ts, "surprise": ev.surprise, "reaction_day": dates[i] if i is not None else pd.NaT}
        beta = _beta(ra, rb, i) if bench is not None and i is not None else None
        if bench is not None:
            row["beta"] = beta
        for h in horizons:
            ok = i is not None and i + h < len(values)
            move = _move(values[i - 1], values[i + h], unit) if ok else np.nan
            if ok and bench is not None:
                move = move - beta * (b[i + h] / b[i - 1] - 1) * 100 if not np.isnan(beta) else np.nan
            row[f"h{h}"] = move
        rows.append(row)
    return pd.DataFrame(rows)


def normal_move(closes: pd.Series, unit: str, h: int, start: pd.Timestamp, end: pd.Timestamp) -> float:
    """Average move over h+1 trading days on all days of the period – what 'no event' looks like."""
    s = closes[(closes.index >= start) & (closes.index <= end)].to_numpy(float)
    if len(s) <= h + 1:
        return np.nan
    a, b = s[:-(h + 1)], s[h + 1:]
    return float(np.mean((b - a) * 100 if unit == "bp" else (b / a - 1) * 100))


def bh_q(p: list[float]) -> list[float]:
    """Benjamini–Hochberg q-values (NaN stays NaN)."""
    arr = np.asarray(p, float)
    q = np.full(arr.shape, np.nan)
    ok = ~np.isnan(arr)
    if not ok.any():
        return q.tolist()
    v = arr[ok]
    order = np.argsort(v)
    ranked = v[order] * len(v) / np.arange(1, len(v) + 1)
    ranked = np.minimum.accumulate(ranked[::-1])[::-1]
    out = np.empty_like(v)
    out[order] = np.minimum(ranked, 1.0)
    q[ok] = out
    return q.tolist()


def _slope(x: np.ndarray, y: np.ndarray) -> float:
    return float(st.linregress(x, y).slope) if len(x) >= 5 and np.std(x) > 0 else np.nan


def summarize(x: np.ndarray, y: np.ndarray) -> dict:
    """Statistics of one market/horizon: x = surprises, y = reactions (in event order)."""
    ok = ~(np.isnan(x) | np.isnan(y))
    x, y = x[ok], y[ok]
    out = {"n": int(len(x))}
    if len(y) >= 3 and np.std(y) > 0:
        # is the average reaction different from zero? (used when all events point the same way, e.g. oil up-shocks)
        half = len(y) // 2
        out |= {"mean": float(np.mean(y)), "mean_p": float(st.ttest_1samp(y, 0.0).pvalue),
                "mean_stable": bool(np.sign(np.mean(y[:half])) == np.sign(np.mean(y[half:])) == np.sign(np.mean(y)))}
    if len(x) < 3 or np.std(x) == 0:
        return out | {"slope_sd": np.nan, "p": np.nan, "stable": None}
    lr = st.linregress(x, y)
    out |= {"slope_sd": float(lr.slope * np.std(x, ddof=1)), "p": float(lr.pvalue), "r": float(lr.rvalue)}
    half = len(x) // 2
    s1, s2 = _slope(x[:half], y[:half]), _slope(x[half:], y[half:])
    out["stable"] = None if np.isnan(s1) or np.isnan(s2) else bool(np.sign(s1) == np.sign(s2) == np.sign(lr.slope))
    # thirds by rank, so ties (many equal surprises) cannot make one group bigger than the other
    order, third = np.argsort(x, kind="stable"), len(x) // 3
    groups = {"hi": order[len(x) - third:], "lo": order[:third]}
    for name, idx in groups.items():
        g = y[idx]
        out |= {f"{name}_n": int(len(g)), f"{name}_mean": float(np.mean(g)) if len(g) else np.nan,
                f"{name}_median": float(np.median(g)) if len(g) else np.nan,
                f"{name}_up": float(np.mean(g > 0) * 100) if len(g) else np.nan}
    a, b = y[groups["hi"]], y[groups["lo"]]
    out["welch_p"] = float(st.ttest_ind(a, b, equal_var=False).pvalue) if min(len(a), len(b)) >= 3 else np.nan
    return out


def verdict(n: int, p: float, q: float) -> str:
    if n < MIN_EVENTS or np.isnan(p):
        return "zu wenig Fälle"
    if q < 0.10:
        return "belastbar"
    if p < 0.10:
        return "Tendenz"
    return "kein Muster"


def finish(summary: pd.DataFrame) -> pd.DataFrame:
    """q-values over all rows of one table, then the verdict."""
    summary["q"] = bh_q(summary["p"].tolist())
    summary["verdict"] = [verdict(n, p, q) for n, p, q in zip(summary["n"], summary["p"], summary["q"])]
    return summary


def study(events: pd.DataFrame, assets: list[dict], horizons: tuple[int, ...] = HORIZONS) -> tuple[pd.DataFrame, pd.DataFrame]:
    """assets: dicts with symbol, name, unit, market, closes and optionally bench (closes of the index).
    Returns (summary, reactions per event)."""
    rows, per_event = [], []
    start, end = events["ts"].min().tz_localize(None), events["ts"].max().tz_localize(None)
    for a in assets:
        rx = reactions(events, a["closes"], a["unit"], a["market"], horizons, a.get("bench"))
        per_event.append(rx.assign(asset=a["name"]))
        adjusted = a.get("bench") is not None
        for h in horizons:
            s = summarize(rx["surprise"].to_numpy(float), rx[f"h{h}"].to_numpy(float))
            s |= {"asset": a["name"], "symbol": a["symbol"], "unit": a["unit"], "h": h, "adjusted": adjusted,
                  "normal": np.nan if adjusted else normal_move(a["closes"], a["unit"], h, start, end)}
            rows.append(s)
    return finish(pd.DataFrame(rows)), pd.concat(per_event, ignore_index=True)


def pooled(per_event: pd.DataFrame, horizons: tuple[int, ...], name: str, unit: str = "pct") -> pd.DataFrame:
    """One summary over the events of many assets together (e.g. the earnings of many companies)."""
    rows, per_event = [], per_event.sort_values("ts")      # time order, so the stability halves are early vs late
    for h in horizons:
        s = summarize(per_event["surprise"].to_numpy(float), per_event[f"h{h}"].to_numpy(float))
        rows.append(s | {"asset": name, "symbol": "", "unit": unit, "h": h, "adjusted": "beta" in per_event, "normal": np.nan})
    return pd.DataFrame(rows)
