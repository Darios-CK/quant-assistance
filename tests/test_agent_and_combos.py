from datetime import date
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from qa import agent, regimes, triggers
from qa.sources import calendar, fred, moves, prices
from qa.study import reaction_start, study


def utc(text: str, tz: str = "America/New_York") -> pd.Timestamp:
    return pd.Timestamp(text, tz=tz).tz_convert("UTC")


# ---------------------------------------------------------------- AI loop with a scripted model
def _usage():
    return SimpleNamespace(input_tokens=1000, output_tokens=200, cache_read_input_tokens=500, cache_creation_input_tokens=0)


def _resp(blocks, stop):
    return SimpleNamespace(content=blocks, stop_reason=stop, usage=_usage())


class FakeAPI:
    def __init__(self, responses):
        self.responses, self.calls = list(responses), []
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self._create))

    def _create(self, **kw):
        self.calls.append({**kw, "messages": list(kw["messages"])})
        return self.responses.pop(0)


def test_agent_runs_tools_and_answers_from_results():
    api = FakeAPI([
        _resp([SimpleNamespace(type="text", text="Ich prüfe."),
               SimpleNamespace(type="tool_use", id="a", name="katalog", input={}),
               SimpleNamespace(type="tool_use", id="b", name="ereignis_analyse", input={"quelle": "gibtsnicht:x"})], "tool_use"),
        _resp([SimpleNamespace(type="text", text="Antwort aus den Ergebnissen.")], "end_turn"),
    ])
    steps = []
    text, history, usage = agent.ask("Frage", [], on_step=lambda *a: steps.append(a), api=api)
    assert text == "Antwort aus den Ergebnissen."
    assert [s[0] for s in steps] == ["katalog", "ereignis_analyse"]
    results = api.calls[1]["messages"][-1]["content"]                 # both results in ONE user message
    assert [r["tool_use_id"] for r in results] == ["a", "b"]
    assert results[0]["is_error"] is False and "Abdeckung" in results[0]["content"]
    assert results[1]["is_error"] is True and "Unbekannte Quelle" in results[1]["content"]
    first = api.calls[0]
    assert first["model"] == agent.MODEL and first["fallbacks"] == "default" and first["cache_control"] == {"type": "ephemeral"}
    assert first["thinking"] == {"type": "adaptive"} and "output_config" in first
    assert {t["name"] for t in first["tools"]} >= {"ereignis_analyse", "kette_pruefen", "earnings_analyse", "backtest"}
    assert usage["steps"] == 2 and usage["cost_usd"] > 0
    assert history[0] == {"role": "user", "content": "Frage"} and history[-1]["role"] == "assistant"


def test_agent_stops_tool_loop_at_limit(monkeypatch):
    monkeypatch.setattr(agent, "MAX_STEPS", 1)
    call = lambda i: _resp([SimpleNamespace(type="tool_use", id=f"t{i}", name="katalog", input={})], "tool_use")  # noqa: E731
    api = FakeAPI([call(1), call(2), _resp([SimpleNamespace(type="text", text="Ende")], "end_turn")])
    text, _, usage = agent.ask("Frage", [], api=api)
    assert text == "Ende" and usage["steps"] == 1
    assert api.calls[2]["messages"][-1]["content"][0]["is_error"] is True


def test_refusal_is_reported():
    api = FakeAPI([_resp([], "refusal")])
    text, _, _ = agent.ask("Frage", [], api=api)
    assert "abgelehnt" in text


def test_event_arguments_map_to_command_line():
    argv = agent._argv_event({"quelle": "ezb", "maerkte": "dax", "bedingung": "vix_hoch", "zusammen_mit": "fed",
                              "fenster": 2, "ohne_bereinigung": True})
    assert argv == ["ereignis", "ezb", "--maerkte", "dax", "--bedingung", "vix_hoch", "--zusammen-mit", "fed", "--fenster", "2", "--ohne-bereinigung"]


# ---------------------------------------------------------------- phases and combinations
def test_phase_is_taken_from_the_close_before_the_event():
    days = pd.bdate_range("2024-01-01", "2024-01-10")
    s = pd.Series([False, False, True, True, True, True, True, True], index=days)   # turns on at the close of 03.01.
    ts = pd.Series([utc("2024-01-03 08:30"), utc("2024-01-04 08:30")])
    assert regimes.known_before(s, ts).tolist() == [False, True]


def test_near_window():
    a = pd.DataFrame({"ts": [utc("2024-01-10 08:30"), utc("2024-02-10 08:30")]})
    b = pd.DataFrame({"ts": [utc("2024-01-12 14:00")]})
    assert regimes.near(a, b, 3).tolist() == [True, False]
    assert regimes.near(a, b, 1).tolist() == [False, False]


def test_filter_phases(monkeypatch):
    days = pd.bdate_range("2024-01-01", "2024-03-29")
    monkeypatch.setitem(regimes.PHASES, "test", ("Test", lambda: pd.Series(days.month >= 2, index=days)))
    ev = pd.DataFrame({"ts": [utc("2024-01-15 08:30"), utc("2024-02-15 08:30")], "surprise": [1.0, 2.0]})
    kept, labels = regimes.filter_phases(ev, ["test"])
    assert kept["surprise"].tolist() == [2.0] and labels == ["Test"]
    with pytest.raises(SystemExit):
        regimes.filter_phases(ev, ["gibtsnicht"])


# ---------------------------------------------------------------- new event sources
def test_calendar_rules():
    assert calendar._third_friday(2024, 3) == date(2024, 3, 15)
    assert all(d.weekday() == 4 and 15 <= d.day <= 21 for d in calendar.dates("optionsverfall", date(2025, 12, 31)))
    assert {d.month for d in calendar.dates("hexensabbat", date(2025, 12, 31))} == {3, 6, 9, 12}
    assert calendar.dates("santa", date(2024, 12, 31))[-1] == date(2024, 12, 24)    # 31, 30, 27, 26, 24 (Mon–Fri)
    assert all(d.weekday() == 0 for d in calendar.dates("montag", date(2000, 12, 31)))


def test_election_reaction_counts_from_next_day():
    ev = calendar.election("de").df
    days = pd.bdate_range("2021-09-20", "2021-10-01")
    sunday = ev["ts"][ev["ts"].dt.year == 2021].iloc[0]
    assert days[reaction_start(days, sunday, "eu")] == pd.Timestamp("2021-09-27")      # Monday after the Sunday vote


def test_custom_dates_and_errors():
    ev = triggers.load("termine:2019-05-05,2018-03-01")
    assert ev.df["ts"].dt.year.tolist() == [2018, 2019]
    assert triggers.one_sided("termine:2019-05-05")
    with pytest.raises(SystemExit):
        triggers.load("termine:05.05.2019")


def test_technical_crossings():
    idx = pd.bdate_range("2020-01-01", periods=400)
    c = pd.Series(np.r_[np.linspace(100, 200, 300), np.linspace(200, 100, 100)], index=idx)
    down = moves.crossings(c, "sma200_runter")
    assert len(down) == 1 and down[0] > idx[300]
    assert moves.crossings(c, "hoch52")[0] == idx[250]                                  # first day with a full year behind it


def test_macro_short_names_and_rate_changes():
    assert fred.MACRO["cpi"][0] == "CPIAUCSL" and fred.MACRO["fed_bilanz"][1] == "16:30"
    periods = pd.date_range("2020-01-01", periods=16, freq="MS")
    first = pd.DataFrame({"period": periods, "value": np.r_[np.full(15, 4.0), 4.5],
                          "released": periods + pd.Timedelta(days=35)})
    df = fred.surprises(first, "veraenderung", rate=True)
    assert df["change"].iloc[-1] == pytest.approx(0.5)                                 # percentage points, not percent


def test_one_sided_study_tests_against_normal_drift():
    days = pd.bdate_range("2000-01-03", "2009-12-31")
    closes = pd.Series(100 * np.cumprod(np.full(len(days), 1.001)), index=days)        # +0.1 % every single day
    ev = pd.DataFrame({"ts": [utc(f"{d:%Y-%m-%d} 09:30") for d in days[300::40]], "surprise": 1.0})
    asset = {"symbol": "X", "name": "X", "unit": "pct", "market": "us", "closes": closes}
    summary, _ = study(ev, [asset], (0,), one_sided=True)
    row = summary.iloc[0]
    assert row["slope_sd"] == pytest.approx(0.1, abs=1e-6)                             # plain average reported
    assert row["verdict"] != "belastbar"                                                # but no different from a normal day
