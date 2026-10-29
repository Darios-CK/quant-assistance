"""FRED series without a key (fredgraph CSV) – for market-derived and weekly series that are not revised much.

Macro releases that get revised (CPI, payrolls …) do NOT come from here: they need the first release from ALFRED
(qa/sources/fred.py, FRED_API_KEY) – otherwise later revisions would leak into the past.
"""

from __future__ import annotations

import io

import pandas as pd

from qa.adapters.base import Adapter, http

NY, CHI = "America/New_York", "America/Chicago"
H41 = (1, "16:30", NY)                         # Fed balance sheet (H.4.1): Wednesday level, published Thursday 16:30 ET


class Fred(Adapter):
    name, title, homepage = "fred", "FRED (St. Louis Fed)", "https://fred.stlouisfed.org"
    SERIES = {
        "USEPUINDXD": {"name": "Economic Policy Uncertainty (USA, täglich)", "unit": "pct", "release": (1, "09:00", NY),
                       "note": "aus Zeitungsartikeln des Vortags; Veröffentlichungszeit angenommen: nächster Werktag 9:00 ET"},
        "T5YIE": {"name": "Breakeven-Inflation 5J", "unit": "bp"},
        "T10YIE": {"name": "Breakeven-Inflation 10J", "unit": "bp"},
        "T5YIFR": {"name": "Inflationserwartung 5J in 5J", "unit": "bp"},
        "DFII5": {"name": "Realzins 5J (TIPS)", "unit": "bp"},
        "DFII10": {"name": "Realzins 10J (TIPS)", "unit": "bp"},
        "RRPONTSYD": {"name": "Reverse Repo der Fed (Volumen)", "unit": "pct", "release": (0, "13:15", NY)},
        "WTREGEN": {"name": "Treasury General Account", "unit": "pct", "release": H41, "freq": "w"},
        "WRESBAL": {"name": "Reserven der Banken bei der Fed", "unit": "pct", "release": H41, "freq": "w"},
        "WALCL": {"name": "Bilanzsumme der Fed (H.4.1)", "unit": "pct", "release": H41, "freq": "w"},
        "SOFR": {"name": "SOFR (Geldmarktzins)", "unit": "bp", "release": (1, "08:00", NY)},
        "STLFSI4": {"name": "St. Louis Fed Financial Stress Index", "unit": "bp", "release": (6, "10:00", CHI), "freq": "w",
                    "note": "Woche bis Freitag, veröffentlicht am folgenden Donnerstag; Index-Punkte (Änderung ×100 als 'Bp')"},
        "NFCI": {"name": "Chicago Fed National Financial Conditions Index", "unit": "bp", "release": (3, "08:30", CHI), "freq": "w",
                 "note": "Woche bis Freitag, veröffentlicht am folgenden Mittwoch; wird rückwirkend neu geschätzt (nicht point-in-time)"},
        "DTWEXBGS": {"name": "Dollar handelsgewichtet (breit)", "unit": "pct",
                     "note": "aus täglichen Devisenkursen; die Fed veröffentlicht wöchentlich, die Kurse selbst sind am Tag bekannt"},
        "THREEFYTP10": {"name": "Laufzeitprämie 10J (Kim-Wright)", "unit": "bp",
                        "note": "Modellschätzung, wird neu geschätzt – nicht point-in-time; nur als Beschreibung, nicht als Signal"},
        "BAMLH0A0HYM2": {"name": "Hochzins-Spread (ICE BofA)", "unit": "bp", "note": "auf FRED nur die letzten 3 Jahre (Lizenz)"},
        "BAMLC0A0CM": {"name": "Investment-Grade-Spread (ICE BofA)", "unit": "bp", "note": "auf FRED nur die letzten 3 Jahre (Lizenz)"},
        "BAA10Y": {"name": "Baa-Spread zu 10J-Treasury", "unit": "bp"},
    }

    def fetch(self, series: str) -> pd.DataFrame:
        # no custom User-Agent: FRED's CDN drops unknown browser-like agents
        r = http("https://fred.stlouisfed.org/graph/fredgraph.csv", {"id": series}, ua=None, timeout=90)
        df = pd.read_csv(io.StringIO(r.text))
        df.columns = ["date", "value"]
        df["date"] = pd.to_datetime(df["date"])
        df["value"] = pd.to_numeric(df["value"], errors="coerce")
        return df.dropna().set_index("date")
