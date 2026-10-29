"""Cboe index histories (VIX term structure, SKEW) and the free put/call archive (2006–2019)."""

from __future__ import annotations

import io

import pandas as pd

from qa.adapters.base import Adapter, http

INDEX_URL = "https://cdn-api.cboe.com/api/global/us_indices/daily_prices/{}_History.csv"
PC_URL = "https://cdn.cboe.com/resources/options/volume_and_call_put_ratios/{}.csv"


class Cboe(Adapter):
    name, title, homepage = "cboe", "Cboe", "https://www.cboe.com"
    SERIES = {
        "VIX": {"name": "VIX (30 Tage)"}, "VIX9D": {"name": "VIX 9 Tage"}, "VIX3M": {"name": "VIX 3 Monate"},
        "VIX6M": {"name": "VIX 6 Monate"}, "SKEW": {"name": "Cboe SKEW (Absicherung gegen Crash)"},
        "VIX_VIX3M": {"name": "VIX-Laufzeitstruktur (VIX / VIX3M; über 1 = Backwardation)",
                      "note": "über 1: kurzfristige Angst höher als langfristige (Backwardation)"},
        "TOTALPC": {"name": "Put/Call-Ratio gesamt (Cboe)", "note": "freies Archiv nur 11/2006 – 10/2019"},
        "EQUITYPC": {"name": "Put/Call-Ratio Aktienoptionen (Cboe)", "note": "freies Archiv nur 11/2006 – 10/2019"},
    }

    def _index(self, name: str) -> pd.DataFrame:
        df = pd.read_csv(io.StringIO(http(INDEX_URL.format(name)).text))
        col = "CLOSE" if "CLOSE" in df.columns else df.columns[-1]
        out = pd.DataFrame({"value": pd.to_numeric(df[col], errors="coerce").to_numpy()},
                           index=pd.to_datetime(df["DATE"], format="%m/%d/%Y").rename("date"))
        return out.dropna()

    def fetch(self, series: str) -> pd.DataFrame:
        if series == "VIX_VIX3M":
            a, b = self._index("VIX")["value"], self._index("VIX3M")["value"]
            return (a / b).dropna().rename("value").to_frame()
        if series in ("TOTALPC", "EQUITYPC"):
            lines = http(PC_URL.format(series.lower())).text.splitlines()
            start = next(i for i, ln in enumerate(lines) if ln.upper().startswith("DATE"))
            df = pd.read_csv(io.StringIO("\n".join(lines[start:])), skipinitialspace=True)
            return pd.DataFrame({"value": pd.to_numeric(df["P/C Ratio"], errors="coerce").to_numpy()},
                                index=pd.to_datetime(df["DATE"], format="mixed").rename("date")).dropna()
        return self._index(series)
