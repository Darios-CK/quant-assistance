"""Daily closes from Yahoo Finance (yfinance) and official free sources (no keys needed).

A symbol is
  a Yahoo ticker                 ^GDAXI, EURUSD=X, DBK.DE …
  FRED:<id>                      FRED rate series in percent, e.g. FRED:DGS10 (US 10-year yield)
  BBK:<flow>/<key>               Bundesbank time series, e.g. Bund yields from the term structure
  EZB:<flow>/<key>               ECB Data Portal, e.g. EZB:EXR/D.USD.EUR.SP00.A (reference rate, fixed 14:15 Frankfurt)
or one of the aliases below.

Limits worth knowing: Yahoo is unofficial and for personal use only; companies that were delisted are
missing (survivorship bias); futures such as CL=F are the front month without roll adjustment.
"""

from __future__ import annotations

import io
import time
import warnings

import pandas as pd
import requests

from qa.cache import cached

# alias -> (symbol, display name)
ALIASES = {
    "dax": ("^GDAXI", "DAX"),
    "sp500": ("^GSPC", "S&P 500"),
    "nasdaq100": ("^NDX", "Nasdaq 100"),
    "stoxx50": ("^STOXX50E", "Euro Stoxx 50"),
    "eurusd": ("EURUSD=X", "EUR/USD"),
    "gold": ("GC=F", "Gold"),
    "oel": ("CL=F", "Öl (WTI)"),
    "vix": ("^VIX", "VIX"),
    "us2y": ("FRED:DGS2", "US-Rendite 2J"),
    "us10y": ("FRED:DGS10", "US-Rendite 10J"),
    "banken_eu": ("EXV1.DE", "Banken Europa (ETF)"),
    "immobilien_eu": ("EXI5.DE", "Immobilien Europa (ETF)"),
    "bau_eu": ("EXV8.DE", "Bau Europa (ETF)"),
    "nahrung_eu": ("EXH3.DE", "Nahrungsmittel Europa (ETF)"),
    "deutsche_bank": ("DBK.DE", "Deutsche Bank"),
    "vonovia": ("VNA.DE", "Vonovia"),
    "basf": ("BAS.DE", "BASF"),
    "lufthansa": ("LHA.DE", "Lufthansa"),
    "bitcoin": ("BTC-USD", "Bitcoin"),
    "ethereum": ("ETH-USD", "Ethereum"),
    "usdjpy": ("JPY=X", "USD/JPY"),
    "usdcad": ("CAD=X", "USD/CAD"),
    "dollar": ("DX-Y.NYB", "Dollar-Index"),
    "bund2j": ("BBK:BBSIS/D.I.ZAR.ZI.EUR.S1311.B.A604.R02XX.R.A.A._Z._Z.A", "Bund-Rendite 2J"),
    "bund10j": ("BBK:BBSIS/D.I.ZAR.ZI.EUR.S1311.B.A604.R10XX.R.A.A._Z._Z.A", "Bund-Rendite 10J"),
    "euro_aaa_10j": ("EZB:YC/B.U2.EUR.4F.G_N_A.SV_C_YM.SR_10Y", "Euro-AAA-Rendite 10J (EZB)"),
    "eurusd_ezb": ("EZB:EXR/D.USD.EUR.SP00.A", "EUR/USD Referenzkurs (EZB)"),
}
OFFICIAL = ("FRED:", "BBK:", "EZB:")

EU_SUFFIXES = (".DE", ".F", ".PA", ".AS", ".MI", ".MC", ".SW", ".L")
EU_INDICES = ("^GDAXI", "^STOXX50E", "^FCHI", "^FTSE", "^SSMI", "^AEX", "FTSEMIB.MI")


def resolve(name: str) -> tuple[str, str]:
    """(symbol, display name) for an alias or a raw symbol."""
    key = name.strip()
    if key.lower() in ALIASES:
        return ALIASES[key.lower()]
    return key, key


def unit(symbol: str) -> str:
    """'bp' for rate series (change in basis points), 'pct' for prices (change in percent)."""
    s = symbol.upper()
    if s.startswith("EZB:EXR/"):
        return "pct"
    return "bp" if s.startswith(OFFICIAL) else "pct"


def market(symbol: str) -> str:
    """Where the daily value is set: 'eu' (17:30 Frankfurt; also Bundesbank and ECB yields), 'ecb_fix' (ECB reference
    rates, 14:15 Frankfurt), 'crypto' (midnight UTC) or 'us' (16:00 New York; also FX, futures, FRED)."""
    s = symbol.upper()
    if s.startswith("EZB:EXR/"):
        return "ecb_fix"
    if s.startswith(("BBK:", "EZB:")):
        return "eu"
    if s.endswith(("-USD", "-EUR", "-USDT")):
        return "crypto"
    return "eu" if s in EU_INDICES or s.endswith(EU_SUFFIXES) else "us"


def default_bench(symbol: str) -> str | None:
    """Market index a single stock or sector ETF is adjusted for; None for indices, rates, FX, futures, crypto."""
    s = symbol.upper()
    if s.startswith(OFFICIAL + ("^",)) or s.endswith(("=X", "=F", ".NYB")) or market(s) == "crypto":
        return None
    return "^GDAXI" if market(s) == "eu" else "^GSPC"


def _yahoo(symbol: str) -> pd.DataFrame:
    import yfinance as yf

    with warnings.catch_warnings():         # yfinance still uses pandas calls deprecated in pandas 3
        warnings.simplefilter("ignore")
        h = yf.Ticker(symbol).history(period="max", auto_adjust=True)
    if h.empty:
        raise ValueError(f"Yahoo liefert keine Daten für {symbol}")
    idx = h.index.tz_localize(None) if h.index.tz is not None else h.index
    return pd.DataFrame({"close": h["Close"].to_numpy(float)}, index=idx.normalize().rename("date"))


def _fred_daily(series: str, attempts: int = 3) -> pd.DataFrame:
    for attempt in range(attempts):     # FRED's CDN is sometimes slow to answer the first request
        try:
            # no custom User-Agent: FRED's CDN drops requests with unknown browser-like agents
            r = requests.get("https://fred.stlouisfed.org/graph/fredgraph.csv", params={"id": series}, timeout=90)
            r.raise_for_status()
            break
        except requests.RequestException:
            if attempt == attempts - 1:
                raise
            time.sleep(3 * (attempt + 1))
    df = pd.read_csv(io.StringIO(r.text))
    df.columns = ["date", "close"]
    df["date"] = pd.to_datetime(df["date"])
    df["close"] = pd.to_numeric(df["close"], errors="coerce")
    return df.dropna().set_index("date")


def _bbk(path: str) -> pd.DataFrame:
    flow, key = path.split("/", 1)
    r = requests.get(f"https://api.statistiken.bundesbank.de/rest/data/{flow}/{key}", params={"format": "csv", "lang": "de"}, timeout=90)
    r.raise_for_status()
    rows = []
    for line in r.text.splitlines():          # header lines first, then "YYYY-MM-DD;value;flag" with decimal comma
        parts = line.split(";")
        if len(parts) >= 2 and len(parts[0]) == 10 and parts[0][4] == "-" and parts[1] not in ("", "."):
            rows.append((parts[0], float(parts[1].replace(",", "."))))
    if not rows:
        raise ValueError(f"Bundesbank liefert keine Werte für {path}")
    df = pd.DataFrame(rows, columns=["date", "close"])
    df["date"] = pd.to_datetime(df["date"])
    # The Bundesbank dates each value one trading day late: the value dated t is built from the prices of t-1
    # (checked against ECB surprises: the reaction shows up in the value dated the day after the meeting, r = 0.77).
    # Each value is moved to the day its prices are from.
    df["close"] = df["close"].shift(-1)
    return df.dropna().set_index("date")


def _ecb(path: str) -> pd.DataFrame:
    flow, key = path.split("/", 1)
    r = requests.get(f"https://data-api.ecb.europa.eu/service/data/{flow}/{key}", params={"format": "csvdata"}, timeout=90)
    r.raise_for_status()
    df = pd.read_csv(io.StringIO(r.text), usecols=["TIME_PERIOD", "OBS_VALUE"])
    df.columns = ["date", "close"]
    df["date"] = pd.to_datetime(df["date"])
    df["close"] = pd.to_numeric(df["close"], errors="coerce")
    return df.dropna().set_index("date")


def closes(symbol: str) -> pd.Series:
    """Daily closes, oldest first, index = trading dates (no time of day)."""
    head, _, rest = symbol.partition(":")
    if head.upper() == "FRED":
        sid = rest.upper()
        df = cached(f"fred_daily_{sid}", lambda: _fred_daily(sid), max_age_h=12)
    elif head.upper() == "BBK":
        df = cached(f"bbk_{rest}", lambda: _bbk(rest), max_age_h=12)
    elif head.upper() == "EZB":
        df = cached(f"ezb_{rest}", lambda: _ecb(rest), max_age_h=12)
    else:
        df = cached(f"yahoo_{symbol}", lambda: _yahoo(symbol), max_age_h=12)
    s = df["close"].dropna()
    return s[~s.index.duplicated(keep="last")].sort_index()
