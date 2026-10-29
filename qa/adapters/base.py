"""One interface for every data source: load (cached), update (force refresh), meta (unit, release time).

    adapter.load(series)   -> DataFrame, index = observation date, column 'value'
    adapter.update(series) -> the same, downloaded again
    adapter.meta(series)   -> {"name", "unit": "pct"|"bp", "release": …, "freq": "d"|"w"|"m", "note"}

'release' says when a value became public – the event time used by studies (no look-ahead):
    "markt"                      market-derived: known during the observation day (like a price)
    (days, "HH:MM", "tz")        published 'days' business days after the observation date at that local time

Network access goes through http(): per-host pause between requests, retry with exponential backoff on 429/5xx/timeouts.
A source without a free supply is a BlockedAdapter: same interface, load() explains why it is empty – a paid source can be
plugged in later by filling fetch().
"""

from __future__ import annotations

import os
import threading
import time
from datetime import datetime
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

import pandas as pd
import requests
from dotenv import load_dotenv

from qa.cache import ROOT, cached

BROWSER_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) quant-assistance research"
_last: dict[str, float] = {}
_lock = threading.Lock()


def http(url: str, params: dict | None = None, headers: dict | None = None, min_interval: float = 0.5, attempts: int = 4,
         timeout: float = 60, ua: str | None = BROWSER_UA) -> requests.Response:
    """GET with a pause per host and retries (1 s, 2 s, 4 s … ; honours Retry-After)."""
    host = urlparse(url).netloc
    h = dict(headers or {})
    if ua and "User-Agent" not in h:
        h["User-Agent"] = ua
    for attempt in range(attempts):
        with _lock:
            wait = _last.get(host, 0) + min_interval - time.time()
            if wait > 0:
                time.sleep(wait)
            _last[host] = time.time()
        try:
            r = requests.get(url, params=params, headers=h, timeout=timeout)
            if r.status_code == 429 or r.status_code >= 500:
                raise requests.HTTPError(f"{r.status_code} von {host}", response=r)
            r.raise_for_status()
            return r
        except requests.RequestException as exc:
            resp = getattr(exc, "response", None)
            if attempt == attempts - 1 or (resp is not None and 400 <= resp.status_code < 500 and resp.status_code != 429):
                raise
            retry_after = resp.headers.get("Retry-After") if resp is not None else None
            time.sleep(float(retry_after) if retry_after and retry_after.isdigit() else 2 ** attempt)
    raise RuntimeError("unreachable")


def env(name: str) -> str:
    load_dotenv(ROOT / ".env")
    return os.getenv(name, "").strip()


class Adapter:
    name = ""
    title = ""
    homepage = ""
    keys: tuple[str, ...] = ()          # environment variables that must be set
    blocked = ""                        # reason when there is no free source
    max_age_h = 12.0
    SERIES: dict[str, dict] = {}        # known series with their meta data

    def available(self) -> tuple[bool, str]:
        if self.blocked:
            return False, f"blockiert: {self.blocked}"
        missing = [k for k in self.keys if not env(k)]
        if missing:
            return False, f"Schlüssel fehlt: {', '.join(missing)} (in .env eintragen, siehe .env.example)"
        return True, ""

    def fetch(self, series: str) -> pd.DataFrame:
        raise NotImplementedError

    def load(self, series: str, max_age_h: float | None = None) -> pd.DataFrame:
        ok, why = self.available()
        if not ok:
            raise SystemExit(f"{self.title}: {why}")
        df = cached(f"{self.name}_{series}", lambda: self.fetch(series), self.max_age_h if max_age_h is None else max_age_h)
        df = df[["value"]].dropna()
        return df[~df.index.duplicated(keep="last")].sort_index()

    def update(self, series: str) -> pd.DataFrame:
        return self.load(series, max_age_h=0)

    def meta(self, series: str) -> dict:
        m = {"name": series, "unit": "pct", "release": "markt", "freq": "d", "market": "us", "note": ""}
        return m | self.SERIES.get(series, {})


class BlockedAdapter(Adapter):
    """Interface without data: fill fetch() and clear 'blocked' when a (paid) source is available."""

    def fetch(self, series: str) -> pd.DataFrame:
        raise SystemExit(f"{self.title}: blockiert – {self.blocked}")


def release_times(dates: pd.DatetimeIndex, release, market_tz: str = "America/New_York") -> pd.DatetimeIndex:
    """UTC time at which each observation became public."""
    if release == "markt":
        tz = ZoneInfo(market_tz)
        return pd.DatetimeIndex([datetime(d.year, d.month, d.day, 9, 30, tzinfo=tz) for d in dates]).tz_convert("UTC")
    days, hhmm, tzname = release
    hh, mm = (int(x) for x in hhmm.split(":"))
    tz = ZoneInfo(tzname)
    shifted = dates + pd.offsets.BDay(int(days)) if days else dates
    return pd.DatetimeIndex([datetime(d.year, d.month, d.day, hh, mm, tzinfo=tz) for d in shifted]).tz_convert("UTC")
