import numpy as np
import pandas as pd
import pytest

from qa.sources import prices
from qa.sources.fred import surprises
from qa.sources.shocks import _ecb_date, classify


def test_ecb_text_dates_are_day_first():
    assert _ecb_date("05/06/2025") == pd.Timestamp("2025-06-05")
    assert _ecb_date(pd.Timestamp("1999-01-07")) == pd.Timestamp("1999-01-07")


def test_classify_sign_rule():
    rates = pd.Series([5.0, 5.0, -3.0, 0.0])
    stocks = pd.Series([-1.0, 1.0, 2.0, 1.0])
    assert classify(rates, stocks).tolist() == ["zins-schock", "info-schock", "zins-schock", "unklar"]


def _releases(values, delays):
    periods = pd.date_range("2020-01-01", periods=len(values), freq="MS")
    return pd.DataFrame({"period": periods, "value": values,
                         "released": [p + pd.Timedelta(days=d) for p, d in zip(periods, delays)]})


def test_naive_surprise_uses_only_past_changes():
    values = 100 * np.cumprod(np.r_[1.0, np.full(14, 1.01)])     # +1 % every month
    values[-1] = values[-2] * 1.03                              # last month +3 %
    df = surprises(_releases(values, [45] * 15), "naiv")
    assert df["surprise"].iloc[:-1].abs().max() == pytest.approx(0, abs=1e-9)
    assert df["surprise"].iloc[-1] == pytest.approx(2.0, abs=1e-6)  # 3 % minus the 1 % average before it


def test_archive_stamped_values_are_dropped():
    values = 100 * np.cumprod(np.r_[1.0, np.full(14, 1.01)])
    delays = [3000] * 5 + [45] * 10                              # first five: archive start, not a release date
    df = surprises(_releases(values, delays), "veraenderung")
    assert (df["released"] - df["period"]).dt.days.max() <= 75
    assert len(df) == 10


def test_symbols_units_and_markets():
    assert prices.resolve("dax") == ("^GDAXI", "DAX")
    assert prices.resolve("SAP.DE") == ("SAP.DE", "SAP.DE")
    assert prices.unit("FRED:DGS10") == "bp" and prices.unit("^GSPC") == "pct"
    assert prices.market("DBK.DE") == "eu" and prices.market("^GDAXI") == "eu"
    assert prices.market("EURUSD=X") == "us" and prices.market("FRED:DGS2") == "us"


def test_official_sources_units_and_markets():
    assert prices.unit("BBK:BBSIS/x") == "bp" and prices.unit("EZB:YC/x") == "bp" and prices.unit("EZB:EXR/x") == "pct"
    assert prices.market("BBK:BBSIS/x") == "eu" and prices.market("EZB:EXR/x") == "ecb_fix"
    assert prices.default_bench("BBK:BBSIS/x") is None and prices.default_bench("EZB:EXR/x") is None


def test_bundesbank_csv_parsing(monkeypatch):
    text = ('"";BBSIS.D.X;BBSIS.D.X_FLAGS\n"";Renditen 10 Jahre;\nEinheit;PROZENT;\n'
            "1997-08-06;.;Kein Wert vorhanden\n1997-08-07;5,76;\n1997-08-08;\n1997-08-11;5,80;\n")

    class R:
        def raise_for_status(self):
            pass

    r = R()
    r.text = text
    monkeypatch.setattr(prices.requests, "get", lambda *a, **k: r)
    df = prices._bbk("BBSIS/D.X")
    # the value dated 11.08. belongs to the prices of 07.08. (one trading day earlier); the last value has no date yet
    assert df["close"].tolist() == [5.80]
    assert str(df.index[0].date()) == "1997-08-07"
