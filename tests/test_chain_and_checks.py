import json

import numpy as np
import pandas as pd
import pytest

from qa import chain, quality, triggers
from qa.sources import prices
from qa.sources.earnings import surprise_pct
from qa.sources.moves import shocks
from qa.study import reactions, summarize

DAYS = pd.bdate_range("2015-01-01", "2020-12-31")


def utc(text: str, tz: str = "America/New_York") -> pd.Timestamp:
    return pd.Timestamp(text, tz=tz).tz_convert("UTC")


# ---------------------------------------------------------------- data checks
def test_quality_flags_outlier_frozen_gap_and_nonpositive():
    s = pd.Series(np.linspace(100, 120, len(DAYS)), index=DAYS)
    s.iloc[100] = s.iloc[99] * 1.5                       # +50 % in one day
    s.iloc[200:206] = s.iloc[199]                        # frozen for 6 days
    s = s.drop(DAYS[300:315])                            # three weeks missing
    s.iloc[-1] = 0.0
    notes = " ".join(quality.check(s, "pct", "X"))
    assert "über 25%" in notes and "unverändert" in notes and "Datenlücke" in notes and "≤ 0" in notes


def test_quality_clean_series_has_no_notes():
    rng = np.random.default_rng(0)
    s = pd.Series(100 * np.cumprod(1 + rng.normal(0, 0.01, len(DAYS))), index=DAYS)
    assert quality.check(s, "pct", "X") == []


# ---------------------------------------------------------------- market adjustment
def test_market_adjusted_reaction_removes_index_move():
    rng = np.random.default_rng(3)
    idx = pd.Series(100 * np.cumprod(1 + rng.normal(0, 0.01, len(DAYS))), index=DAYS)
    stock = idx ** 1.5                                   # beta ≈ 1.5, no own news
    stock = stock / stock.iloc[0] * 50
    ev = pd.DataFrame({"ts": [utc(f"{d:%Y-%m-%d} 08:30") for d in DAYS[400::50]], "surprise": 1.0})
    raw = reactions(ev, stock, "pct", "us", (0, 5))
    adj = reactions(ev, stock, "pct", "us", (0, 5), bench=idx)
    assert raw["h5"].abs().mean() > 0.5
    assert adj["h5"].abs().mean() < 0.1                  # nothing left once the market move is taken out
    assert adj["beta"].dropna().between(1.3, 1.7).all()


def test_beta_needs_history_before_event():
    idx = pd.Series(np.linspace(100, 110, len(DAYS)), index=DAYS)
    ev = pd.DataFrame({"ts": [utc(f"{DAYS[30]:%Y-%m-%d} 08:30")], "surprise": [1.0]})
    assert np.isnan(reactions(ev, idx * 2, "pct", "us", (0,), bench=idx)["h0"][0])


def test_default_bench():
    assert prices.default_bench("DAL") == "^GSPC" and prices.default_bench("CON.DE") == "^GDAXI"
    assert all(prices.default_bench(s) is None for s in ("^GSPC", "CAD=X", "CL=F", "BTC-USD", "FRED:DGS10", "DX-Y.NYB"))
    assert prices.market("BTC-USD") == "crypto"


# ---------------------------------------------------------------- event sources
def test_shocks_use_only_past_volatility_and_are_spaced():
    rng = np.random.default_rng(5)
    r = rng.normal(0, 0.01, len(DAYS))
    r[400], r[402], r[600] = 0.08, 0.08, -0.08           # 402 is too close to 400
    s = pd.Series(100 * np.cumprod(1 + r), index=DAYS)
    up = shocks(s, "pct", 4.0, "hoch")
    assert list(up["date"]) == [DAYS[400]]
    both = shocks(s, "pct", 4.0, "beide")
    assert set(both["date"]) == {DAYS[400], DAYS[600]}
    # a shock in the first year has no past volatility to compare with
    assert shocks(s.iloc[:100], "pct", 1.0).empty


def test_earnings_surprise_capped_and_zero_consensus():
    s = surprise_pct(np.array([1.1, 0.5, 0.02, 0.01]), np.array([1.0, 1.0, 0.0, 0.001]))
    assert s[0] == pytest.approx(10.0) and s[1] == pytest.approx(-50.0)
    assert s[2] == 100.0 and s[3] == 100.0


def test_one_sided_triggers():
    assert triggers.one_sided("kurs:CL=F", richtung="hoch")
    assert not triggers.one_sided("kurs:CL=F", richtung="beide")
    assert not triggers.one_sided("ezb")


def test_mean_test_in_summarize():
    y = np.r_[np.full(30, 1.0), np.full(30, 1.2)] + np.random.default_rng(1).normal(0, 0.1, 60)
    s = summarize(np.full(60, 2.5), y)                   # all surprises equal: only the mean test works
    assert s["mean"] > 1 and s["mean_p"] < 1e-10 and s["mean_stable"] and np.isnan(s["p"])


# ---------------------------------------------------------------- chain verdicts
@pytest.mark.parametrize("verdict,value,expect,result", [
    ("belastbar", -1.0, "-", "✅ bestätigt"),
    ("belastbar", 1.0, "-", "❌ Gegenteil belegt"),
    ("Tendenz", 1.0, "+", "〰️ Tendenz"),
    ("Tendenz", -1.0, "+", "〰️ Tendenz zum Gegenteil"),
    ("kein Muster", 1.0, "+", "⬜ nicht nachweisbar"),
    ("zu wenig Fälle", 1.0, "+", "⬜ zu wenig Fälle"),
    ("belastbar", 1.0, "?", "✅ Zusammenhang belegt (gleichläufig)"),
])
def test_chain_status(verdict, value, expect, result):
    assert chain.status(verdict, value, expect) == result


def test_chain_end_to_end_with_synthetic_markets(tmp_path, monkeypatch):
    rng = np.random.default_rng(9)
    n = len(DAYS)
    oil_r = rng.normal(0, 0.01, n)
    shock_days = np.arange(300, n - 30, 25)
    oil_r[shock_days] = 0.06
    market = pd.Series(100 * np.cumprod(1 + rng.normal(0, 0.008, n)), index=DAYS)
    airline_r = np.diff(np.log(market.to_numpy()), prepend=np.log(100)) + rng.normal(0, 0.005, n)
    airline_r[shock_days] -= 0.03                        # airlines lose 3 % on oil-shock days
    data = {"CL=F": pd.Series(60 * np.cumprod(1 + oil_r), index=DAYS), "^GSPC": market,
            "DAL": pd.Series(30 * np.exp(np.cumsum(airline_r)), index=DAYS),
            "XYZ": pd.Series(20 * np.cumprod(1 + rng.normal(0, 0.01, n)), index=DAYS)}
    monkeypatch.setattr(prices, "closes", lambda s: data[s])
    spec = {"name": "Test", "ausloeser": {"quelle": "kurs:CL=F", "schwelle": 3, "richtung": "hoch"},
            "glieder": [{"id": "air", "symbol": "DAL", "nach": "ausloeser", "erwartung": "-", "warum": "Kerosin"},
                        {"id": "x", "symbol": "XYZ", "nach": "air", "erwartung": "+", "warum": "Zufall"}]}
    path = tmp_path / "c.json"
    path.write_text(json.dumps(spec))
    text, per_event = chain.run(path)
    assert "✅ bestätigt **DAL (DAL)**" in text
    assert "⬜ nicht nachweisbar **XYZ (XYZ)**" in text
    assert set(per_event["asset"]) == {"air", "x"}


def test_chain_rejects_unknown_parent(tmp_path, monkeypatch):
    spec = {"ausloeser": {"quelle": "ezb"}, "glieder": [{"id": "a", "symbol": "DAX", "nach": "gibtsnicht"}]}
    path = tmp_path / "c.json"
    path.write_text(json.dumps(spec))
    monkeypatch.setattr(triggers, "load", lambda *a, **k: type("E", (), {"df": pd.DataFrame({"ts": [utc("2020-01-02 08:30")], "surprise": [1.0]})})())
    with pytest.raises(SystemExit, match="Vorgänger"):
        chain.run(path)
