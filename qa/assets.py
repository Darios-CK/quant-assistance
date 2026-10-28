"""Load the markets of an analysis: closes, unit, close time, benchmark for market adjustment, data checks."""

from __future__ import annotations

import sys

import pandas as pd

from qa import quality
from qa.sources import prices


def load(items: list[dict], period: tuple[pd.Timestamp, pd.Timestamp] | None = None) -> tuple[list[dict], list[str]]:
    """items: dicts with 'symbol' (alias or symbol), optional 'name', 'key' and 'adjust' (default True).
    period: first and last event – the data checks look at this span (plus the beta year before and 3 months after).
    Returns (assets for study(), notes from the data checks).  Markets without data are skipped with a note."""
    assets, notes, benches = [], [], {}
    for it in items:
        symbol, label = prices.resolve(it["symbol"])
        label = it.get("name") or label
        try:
            closes = prices.closes(symbol)
        except Exception as exc:
            msg = f"{label} ({symbol}) übersprungen – keine Kurse: {exc}"
            print("Hinweis: " + msg, file=sys.stderr)
            notes.append(msg)
            continue
        unit = prices.unit(symbol)
        bench_sym = prices.default_bench(symbol) if it.get("adjust", True) else None
        bench = None
        if bench_sym:
            if bench_sym not in benches:
                benches[bench_sym] = prices.closes(bench_sym)
            bench = benches[bench_sym]
        checked = closes
        if period is not None:
            lo, hi = (pd.Timestamp(t).tz_localize(None) if pd.Timestamp(t).tzinfo else pd.Timestamp(t) for t in period)
            checked = closes[(closes.index >= lo - pd.Timedelta(days=400)) & (closes.index <= hi + pd.Timedelta(days=100))]
        notes += quality.check(checked, unit, label)
        assets.append({"key": it.get("key", label), "symbol": symbol, "name": it.get("key", label), "label": label,
                       "unit": unit, "market": prices.market(symbol), "closes": closes, "bench": bench, "bench_symbol": bench_sym})
    return assets, notes
