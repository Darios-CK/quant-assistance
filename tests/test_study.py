import numpy as np
import pandas as pd
import pytest

from qa.study import bh_q, normal_move, reaction_start, reactions, study, summarize, verdict

DATES = pd.bdate_range("2024-01-01", "2024-03-29")


def utc(text: str, tz: str) -> pd.Timestamp:
    return pd.Timestamp(text, tz=tz).tz_convert("UTC")


def test_event_before_close_reacts_same_day():
    i = reaction_start(DATES, utc("2024-01-10 14:15", "Europe/Berlin"), "eu")
    assert DATES[i] == pd.Timestamp("2024-01-10")


def test_fomc_after_european_close_reacts_next_day():
    ts = utc("2024-01-10 14:00", "America/New_York")
    assert DATES[reaction_start(DATES, ts, "eu")] == pd.Timestamp("2024-01-11")
    assert DATES[reaction_start(DATES, ts, "us")] == pd.Timestamp("2024-01-10")


def test_weekend_event_reacts_monday():
    i = reaction_start(DATES, utc("2024-01-13 10:00", "America/New_York"), "us")
    assert DATES[i] == pd.Timestamp("2024-01-15")


def test_no_close_before_event_or_data_gap():
    assert reaction_start(DATES, utc("2024-01-01 08:30", "America/New_York"), "us") is None
    assert reaction_start(DATES, utc("2024-06-03 08:30", "America/New_York"), "us") is None


def test_reactions_pct_and_bp():
    closes = pd.Series(np.arange(100.0, 100.0 + len(DATES)), index=DATES)
    ev = pd.DataFrame({"ts": [utc("2024-01-10 08:30", "America/New_York")], "surprise": [1.0]})
    rx = reactions(ev, closes, "pct", "us", (0, 5))
    base = closes[pd.Timestamp("2024-01-09")]
    assert rx["h0"][0] == pytest.approx((base + 1) / base * 100 - 100)
    assert rx["h5"][0] == pytest.approx((base + 6) / base * 100 - 100)
    rx = reactions(ev, closes / 100, "bp", "us", (0,))       # rates in percent: 0.01 pp = 1 bp
    assert rx["h0"][0] == pytest.approx(1.0)


def test_reactions_run_out_of_data():
    closes = pd.Series(np.ones(len(DATES)), index=DATES)
    ev = pd.DataFrame({"ts": [utc("2024-03-28 08:30", "America/New_York")], "surprise": [1.0]})
    assert np.isnan(reactions(ev, closes, "pct", "us", (5,))["h5"][0])


def test_summarize_recovers_slope_and_groups():
    rng = np.random.default_rng(1)
    x = rng.normal(0, 2, 300)
    y = 0.5 * x + rng.normal(0, 0.1, 300)
    s = summarize(x, y)
    assert s["n"] == 300
    assert s["slope_sd"] == pytest.approx(0.5 * np.std(x, ddof=1), rel=0.02)
    assert s["p"] < 1e-6 and s["hi_mean"] > 0 > s["lo_mean"]
    assert s["hi_up"] > 90 and s["lo_up"] < 10 and s["welch_p"] < 1e-6


def test_summarize_ignores_missing_values():
    s = summarize(np.array([1.0, 2.0, np.nan, 4.0, 5.0]), np.array([1.0, np.nan, 3.0, 4.0, 5.0]))
    assert s["n"] == 3


def test_bh_q_matches_reference():
    # reference values from R: p.adjust(c(0.01, 0.04, 0.03, 0.2), "BH")
    assert bh_q([0.01, 0.04, 0.03, 0.2, float("nan")])[:4] == pytest.approx([0.04, 0.0533333, 0.0533333, 0.2], rel=1e-5)


def test_verdict_needs_enough_events():
    assert verdict(10, 0.001, 0.001) == "zu wenig Fälle"
    assert verdict(50, 0.001, 0.05) == "belastbar"
    assert verdict(50, 0.05, 0.3) == "Tendenz"
    assert verdict(50, 0.5, 0.9) == "kein Muster"


def test_normal_move_flat_market_is_zero():
    closes = pd.Series(np.full(len(DATES), 50.0), index=DATES)
    assert normal_move(closes, "pct", 5, DATES[0], DATES[-1]) == pytest.approx(0.0)


def test_study_end_to_end():
    rng = np.random.default_rng(2)
    days = pd.bdate_range("2010-01-01", "2020-12-31")
    surprise = pd.Series(0.0, index=days)
    ev_days = days[10::20]
    surprise[ev_days] = rng.normal(0, 5, len(ev_days))
    ret = 0.2 * surprise + rng.normal(0, 0.05, len(days))   # market reacts on event day only
    closes = pd.Series(100 * np.cumprod(1 + ret / 100), index=days)
    events = pd.DataFrame({"ts": [utc(f"{d:%Y-%m-%d} 08:30", "America/New_York") for d in ev_days],
                           "surprise": surprise[ev_days].to_numpy()})
    summary, per_event = study(events, [{"symbol": "X", "name": "X", "unit": "pct", "market": "us", "closes": closes}], (0, 5))
    day0 = summary[summary["h"] == 0].iloc[0]
    assert day0["verdict"] == "belastbar" and day0["slope_sd"] > 0
    assert len(per_event) == len(ev_days)
