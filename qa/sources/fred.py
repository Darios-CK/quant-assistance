"""Macro releases from ALFRED: every value as it was first published, with the day it was published.

Without consensus forecasts the "surprise" is a stand-in, built only from what was known on release day:
  naiv          change minus the average change of the previous 12 releases (default)
  veraenderung  the change itself
Changes are computed between consecutive first-release levels, so a revision of the previous month is ignored.
"""

from __future__ import annotations

import os
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import requests
from dotenv import load_dotenv

from qa.cache import ROOT, cached
from qa.sources.shocks import EventSet

API = "https://api.stlouisfed.org/fred"
NEW_YORK = ZoneInfo("America/New_York")
# ALFRED stamps values older than its vintage archive with the archive start; such dates are no release dates
MAX_DELAY_DAYS = {"m": 75, "q": 120, "w": 14}


# short names for common releases: (FRED series, release time New York)
MACRO = {
    "cpi": ("CPIAUCSL", "08:30"), "kerninflation": ("CPILFESL", "08:30"), "pce": ("PCEPI", "08:30"),
    "ppi": ("PPIFIS", "08:30"), "nfp": ("PAYEMS", "08:30"), "arbeitslosenquote": ("UNRATE", "08:30"),
    "erstantraege": ("ICSA", "08:30"), "bip": ("GDPC1", "08:30"), "einzelhandel": ("RSAFS", "08:30"),
    "industrieproduktion": ("INDPRO", "09:15"), "verbrauchervertrauen": ("UMCSENT", "10:00"),
    "handelsbilanz": ("BOPGSTB", "08:30"), "geldmenge_m2": ("M2SL", "13:00"), "fed_bilanz": ("WALCL", "16:30"),
    "oel_lager": ("WCESTUS1", "10:30"), "baubeginne": ("HOUST", "08:30"),
}


def _key() -> str:
    load_dotenv(ROOT / ".env")
    key = os.getenv("FRED_API_KEY", "").strip()
    if not key:
        raise SystemExit("FRED_API_KEY fehlt. Kostenlos unter https://fred.stlouisfed.org/docs/api/api_key.html "
                         "anlegen und in quant-analyst/.env eintragen (Vorlage: .env.example).")
    return key


def _get(path: str, **params) -> dict:
    r = requests.get(f"{API}/{path}", params={**params, "api_key": _key(), "file_type": "json"}, timeout=60)
    r.raise_for_status()
    return r.json()


def _first_releases(series: str) -> pd.DataFrame:
    data = _get("series/observations", series_id=series, output_type=4,
                realtime_start="1776-07-04", realtime_end="9999-12-31")
    rows = [(o["date"], o["realtime_start"], o["value"]) for o in data.get("observations", [])]
    df = pd.DataFrame(rows, columns=["period", "released", "value"])
    df["period"] = pd.to_datetime(df["period"])
    df["released"] = pd.to_datetime(df["released"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    return df.dropna()


def _info(series: str) -> pd.DataFrame:
    s = _get("series", series_id=series)["seriess"][0]
    return pd.DataFrame([{k: s.get(k, "") for k in ("title", "units", "frequency_short")}])


def surprises(first: pd.DataFrame, method: str = "naiv", window: int = 12, freq: str = "m", rate: bool = False) -> pd.DataFrame:
    """Release table -> (released, value, change, surprise), only rows with a plausible release date.
    rate: the series is itself a rate in percent (unemployment rate) – change in percentage points, not percent."""
    df = first.sort_values("period").reset_index(drop=True)
    df["change"] = df["value"].diff() if rate else df["value"].pct_change() * 100
    if method == "naiv":
        # only past releases enter the expectation (shift(1)): nothing from the future
        expected = df["change"].shift(1).rolling(window, min_periods=window).mean()
        df["surprise"] = df["change"] - expected
    elif method == "veraenderung":
        df["surprise"] = df["change"]
    else:
        raise ValueError(f"unbekannte Methode {method}")
    delay = (df["released"] - df["period"]).dt.days
    df = df[(delay > 0) & (delay <= MAX_DELAY_DAYS.get(freq, 75))]
    return df.dropna(subset=["surprise"]).reset_index(drop=True)


def macro(series: str, method: str = "naiv", release_time: str | None = None) -> EventSet:
    if series.lower() in MACRO:
        series, default_time = MACRO[series.lower()]
        release_time = release_time or default_time
    release_time = release_time or "08:30"
    series = series.upper()
    first = cached(f"alfred_first_{series}", lambda: _first_releases(series), max_age_h=24)
    info = cached(f"fred_info_{series}", lambda: _info(series), max_age_h=24 * 30).iloc[0]
    freq = str(info["frequency_short"]).lower()[:1] or "m"
    units = str(info["units"])
    rate = units.startswith("Percent") and "Change" not in units
    df = surprises(first, method, freq=freq, rate=rate)
    hh, mm = (int(x) for x in release_time.split(":"))
    ts = [datetime(d.year, d.month, d.day, hh, mm, tzinfo=NEW_YORK) for d in df["released"]]
    out = pd.DataFrame({"ts": pd.to_datetime(ts, utc=True), "surprise": df["surprise"].to_numpy(float),
                        "change": df["change"].round(3).to_numpy(), "period": df["period"].dt.strftime("%Y-%m").to_numpy()})
    desc = {"naiv": "Veränderung zum Vorwert minus Durchschnitt der letzten 12 Veränderungen (Ersatz für Konsens, %-Punkte)",
            "veraenderung": "Veränderung zum Vorwert laut Erstveröffentlichung (%)"}[method]
    notes = [f"{info['title']} ({info['units']}), Erstveröffentlichung laut ALFRED.",
             f"Uhrzeit der Veröffentlichung angenommen: {release_time} New York (änderbar mit --uhrzeit).",
             "Kein Konsens: Der Markt reagiert auf die Abweichung von der Erwartung, die hier nur angenähert wird."]
    return EventSet(f"{series}-Veröffentlichungen", "%-Pkt", desc,
                    f"ALFRED, https://alfred.stlouisfed.org/series?seid={series}", out, notes)
