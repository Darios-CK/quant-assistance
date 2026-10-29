import numpy as np
import pandas as pd
import pytest
import requests

from qa import adapters
from qa.adapters import base, events as series_events
from qa.adapters.blocked import BLOCKED
from qa.sources import prices


def test_release_times_use_business_days_and_local_time():
    d = pd.DatetimeIndex(["2024-01-03"])                                   # Wednesday
    ts = base.release_times(d, (1, "16:30", "America/New_York"))
    assert ts[0] == pd.Timestamp("2024-01-04 21:30", tz="UTC")              # Thursday 16:30 ET
    fri = base.release_times(pd.DatetimeIndex(["2024-01-05"]), (1, "08:00", "America/New_York"))
    assert fri[0].day_name() == "Monday"
    assert base.release_times(d, "markt")[0] == pd.Timestamp("2024-01-03 14:30", tz="UTC")


def test_zscores_use_only_earlier_changes():
    v = pd.Series(np.r_[np.full(300, 1.0) + np.random.default_rng(0).normal(0, 0.01, 300), 2.0],
                  index=pd.bdate_range("2020-01-01", periods=301))
    z = series_events.zscores(v, "bp")
    before = series_events.zscores(v.iloc[:-1], "bp")
    assert z.iloc[:-1].equals(before)                                       # adding a later value changes nothing earlier
    assert z.iloc[-1] > 10


def test_blocked_adapters_explain_and_stay_empty():
    assert len(BLOCKED) >= 10
    for a in BLOCKED:
        ok, why = a.available()
        assert not ok and why
        with pytest.raises(SystemExit):
            a.load("x")


def test_missing_key_is_reported(monkeypatch):
    a = base.Adapter()
    a.name, a.title, a.keys = "t", "Test", ("QA_TEST_KEY_NOT_SET",)
    monkeypatch.setattr(base, "env", lambda k: "")
    ok, why = a.available()
    assert not ok and "QA_TEST_KEY_NOT_SET" in why


def test_http_retries_then_succeeds(monkeypatch):
    calls = []

    class R:
        def __init__(self, code):
            self.status_code, self.headers = code, {}

        def raise_for_status(self):
            if self.status_code >= 400:
                raise requests.HTTPError(response=self)

    def fake_get(url, **kw):
        calls.append(url)
        return R(503 if len(calls) < 3 else 200)

    monkeypatch.setattr(base.requests, "get", fake_get)
    monkeypatch.setattr(base.time, "sleep", lambda s: None)
    assert base.http("https://example.org/x", min_interval=0).status_code == 200 and len(calls) == 3


def test_http_does_not_retry_client_errors(monkeypatch):
    calls = []

    class R:
        status_code, headers = 404, {}

        def raise_for_status(self):
            raise requests.HTTPError(response=self)

    monkeypatch.setattr(base.requests, "get", lambda url, **kw: calls.append(1) or R())
    with pytest.raises(requests.HTTPError):
        base.http("https://example.org/y", min_interval=0)
    assert len(calls) == 1


def test_aliases_route_to_adapters():
    assert prices.resolve("vix_struktur")[0] == "A:cboe:VIX_VIX3M"
    assert prices.unit("A:fred:SOFR") == "bp" and prices.unit("A:fred:WALCL") == "pct"
    assert prices.default_bench("A:fred:SOFR") is None
    for alias, (symbol, _) in adapters.ALIASES.items():
        adapter, series = adapters.split(symbol)
        assert series in adapter.SERIES, alias
