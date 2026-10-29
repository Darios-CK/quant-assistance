"""Real data, end to end, for every factor served by the FRED and Cboe adapters:
(1) data load, (2) events are built, (3) the events run through an event study AND a chain check."""

import json

import pandas as pd
import pytest

from qa import adapters, chain, triggers
from qa.assets import load as load_assets
from qa.study import study

pytestmark = pytest.mark.live

STALE_OK = {"putcall", "putcall_aktien"}            # free Cboe archive ends 10/2019


@pytest.mark.parametrize("alias", sorted(adapters.ALIASES))
def test_factor_end_to_end(alias, tmp_path):
    symbol, _ = adapters.ALIASES[alias]
    adapter, series = adapters.split(symbol)
    df = adapter.load(series)
    assert len(df) > 200, f"{alias}: zu wenige Werte ({len(df)})"
    if alias not in STALE_OK:
        assert df.index[-1] > pd.Timestamp.now() - pd.Timedelta(days=45), f"{alias}: letzter Wert {df.index[-1]:%d.%m.%Y}"

    ev = triggers.load(f"faktor:{alias}")
    assert len(ev.df) >= 5 and ev.df["ts"].dt.tz is not None
    assert (ev.df["ts"] >= ev.df["beobachtet"].dt.tz_localize("UTC")).all()          # never before it was observed

    assets, _ = load_assets([{"symbol": "sp500"}], (ev.df["ts"].min(), ev.df["ts"].max()))
    summary, per_event = study(ev.df, assets, (0, 5))
    assert len(summary) == 2 and summary["n"].min() > 0

    spec = {"name": f"Test {alias}", "frage": "läuft die Kette?", "ausloeser": {"quelle": f"faktor:{alias}"}, "horizonte": [0, 5],
            "glieder": [{"id": "markt", "symbol": "sp500", "name": "S&P 500", "nach": "ausloeser", "erwartung": "?", "warum": "Test"}]}
    path = tmp_path / "kette.json"
    path.write_text(json.dumps(spec), encoding="utf-8")
    text, _ = chain.run(path)
    assert "S&P 500" in text
