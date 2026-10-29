import json

import numpy as np
import pandas as pd
import pytest

from qa import backtest, metrics
from qa.sources import prices

DAYS = pd.bdate_range("2000-01-03", "2020-12-31")


def series(values) -> pd.Series:
    return pd.Series(np.asarray(values, float), index=DAYS[: len(values)])


# ---------------------------------------------------------------- metrics
def test_max_drawdown_and_equity():
    r = series([0.10, -0.50, 0.20])
    assert metrics.max_drawdown(r) == pytest.approx(-0.5)
    assert metrics.equity(r).iloc[-1] == pytest.approx(1.1 * 0.5 * 1.2)


def test_sharpe_scaling_and_psr():
    rng = np.random.default_rng(0)
    r = rng.normal(0.001, 0.01, 2520)
    assert metrics.sharpe(r) == pytest.approx(metrics.sharpe(r, annual=False) * np.sqrt(252))
    assert metrics.psr(r) > 0.9                              # clear positive drift over 10 years
    assert metrics.psr(-r) < 0.1


def test_more_trials_raise_the_bar():
    sharpes = list(np.random.default_rng(1).normal(0, 0.03, 50))
    assert metrics.expected_max_sharpe(sharpes, 1) == 0.0
    assert metrics.expected_max_sharpe(sharpes, 100) > metrics.expected_max_sharpe(sharpes, 10) > 0
    r = np.random.default_rng(2).normal(0.0005, 0.01, 2000)
    assert metrics.dsr(r, sharpes, 100) < metrics.psr(r)


def test_pbo_is_high_for_noise_and_low_for_a_real_winner():
    rng = np.random.default_rng(3)
    noise = rng.normal(0, 0.01, (2000, 10))
    assert metrics.pbo(noise) > 0.25
    real = noise.copy()
    real[:, 0] += 0.002                                      # one variant really is better
    assert metrics.pbo(real) < 0.1


def test_summary_fields():
    rng = np.random.default_rng(4)
    r = pd.Series(rng.normal(0.0004, 0.01, len(DAYS)), index=DAYS)
    pos = pd.Series(1.0, index=DAYS)
    m = metrics.summary(r, pos, r * 0.5 + rng.normal(0, 0.005, len(DAYS)))
    for k in ("cagr", "vol", "sharpe", "sortino", "mdd", "calmar", "skew", "kurt", "hit", "win_loss", "var95", "es95", "exposure", "beta", "stress"):
        assert k in m
    assert m["exposure"] == 1.0 and m["es95"] <= m["var95"] < 0
    assert set(m["stress"]) == set(metrics.STRESS)


# ---------------------------------------------------------------- no look-ahead
def test_signal_trades_only_from_next_day():
    c = series(np.r_[np.full(300, 100.0), np.full(300, 200.0)])     # jump on day 300
    held = backtest._trend(c, {"schnell": 1, "langsam": 2}, short=False)
    assert held.iloc[300] == 0.0 and held.iloc[301] == 1.0          # signal at the close of day 300, held from day 301
    r = backtest.strategy_returns(c, held, cost_bp=0)
    assert r.iloc[300] == 0.0                                       # the jump itself is not earned


def test_costs_on_every_change():
    c = series(np.full(10, 100.0))
    held = series([0, 1, 1, 0, -1, -1, 0, 0, 0, 0])
    r = backtest.strategy_returns(c, held, cost_bp=10)
    assert r.sum() == pytest.approx(-(1 + 1 + 1 + 1) * 0.001)     # four units of turnover, no price change


def test_reversal_uses_only_past_volatility():
    rng = np.random.default_rng(5)
    c = series(100 * np.cumprod(1 + rng.normal(0, 0.01, 600)))
    held = backtest._reversal(c, {"tage": 3, "schwelle": 2.0, "halten": 5}, short=False)
    changed = c.copy()
    changed.iloc[500:] *= 3                                          # change the future only
    held2 = backtest._reversal(changed, {"tage": 3, "schwelle": 2.0, "halten": 5}, short=False)
    assert (held.iloc[:500] == held2.iloc[:500]).all()


def test_event_rule_enters_after_reaction_day_and_threshold_from_past():
    c = series(np.full(400, 100.0))
    ts = [pd.Timestamp(f"{d:%Y-%m-%d} 14:15", tz="Europe/Berlin").tz_convert("UTC") for d in DAYS[20:400:20]]
    ev = pd.DataFrame({"ts": ts, "surprise": [1.0, -1.0] * 9 + [5.0]})
    held = backtest._event(c, {"halten": 3, "schwelle": 0.0}, True, ev, "eu", "mit")
    first = DAYS.get_loc(ts[10].tz_convert("Europe/Berlin").tz_localize(None).normalize())
    assert held.iloc[first] == 0 and (held.iloc[first + 1:first + 4] == 1.0).all()   # 11th event: first with 10 earlier ones
    assert (held.iloc[: DAYS.get_loc(ts[9].tz_convert("Europe/Berlin").tz_localize(None).normalize()) + 1] == 0).all()


def test_walk_forward_picks_from_past_years_only():
    idx = pd.bdate_range("2000-01-03", "2009-12-31")
    a = pd.Series(np.where(idx.year < 2007, 0.001, -0.001), index=idx)    # good early, bad late
    b = pd.Series(np.where(idx.year < 2007, -0.0005, 0.002), index=idx)
    noise = np.random.default_rng(6).normal(0, 0.001, len(idx))
    m = pd.DataFrame({0: a + noise, 1: b + noise})
    _, picks = backtest.walk_forward(m, 2000)
    assert dict(picks)[2007] == 0                                    # in 2007 only 2000–2006 is known: a looked better


def test_trials_are_counted_once(tmp_path):
    spec = {"markt": "dax", "regel": "trend"}
    log = tmp_path / "t.jsonl"
    grid = [{"schnell": 20, "langsam": 200}, {"schnell": 50, "langsam": 200}]
    assert backtest.log_trials(spec, grid, log) == 2
    assert backtest.log_trials(spec, grid, log) == 2                 # same variants again: no new trials
    assert backtest.log_trials(spec, grid + [{"schnell": 100, "langsam": 200}], log) == 3


def test_run_end_to_end(tmp_path, monkeypatch):
    rng = np.random.default_rng(7)
    c = pd.Series(100 * np.cumprod(1 + rng.normal(0.0003, 0.01, len(DAYS))), index=DAYS)
    monkeypatch.setattr(prices, "closes", lambda s: c)
    monkeypatch.setattr(backtest, "TRIALS", tmp_path / "trials.jsonl")
    spec = {"name": "T", "markt": "dax", "regel": "trend", "parameter": {"schnell": [20, 50], "langsam": [200]},
            "kosten_bp": 5, "holdout_ab": "2015-01-01"}
    path = tmp_path / "s.json"
    path.write_text(json.dumps(spec))
    text, detail = backtest.run(path)
    assert "## Einordnung" in text and "Test (nie zur Wahl genutzt)" in text and "Deflated Sharpe" in text
    assert {"rendite_strategie", "position", "rendite_markt"} <= set(detail.columns)


def test_rate_series_rejected(tmp_path):
    path = tmp_path / "s.json"
    path.write_text(json.dumps({"markt": "us10y", "regel": "trend", "parameter": {"schnell": [20], "langsam": [200]}}))
    with pytest.raises(SystemExit, match="Zinsreihe"):
        backtest.run(path)
