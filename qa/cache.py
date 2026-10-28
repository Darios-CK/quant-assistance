"""Local cache: every download lands in data/ once and is read from disk afterwards."""

from __future__ import annotations

import re
import sys
import time
from pathlib import Path
from typing import Callable

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "data" / "cache"
RAW = ROOT / "data" / "raw"
UA = {"User-Agent": "Mozilla/5.0 (quant-analyst, personal research)"}


def _fresh(path: Path, max_age_h: float) -> bool:
    return path.exists() and (time.time() - path.stat().st_mtime) < max_age_h * 3600


def cached(key: str, fetch: Callable[[], pd.DataFrame], max_age_h: float = 24) -> pd.DataFrame:
    """Parquet cache.  When the download fails, an older copy is used (with a note on stderr)."""
    path = CACHE / f"{re.sub(r'[^A-Za-z0-9_.-]', '_', key)}.parquet"
    if _fresh(path, max_age_h):
        return pd.read_parquet(path)
    try:
        df = fetch()
    except Exception as exc:  # network down, source changed …
        if path.exists():
            print(f"Hinweis: {key} nicht aktualisiert ({exc}); nutze gespeicherten Stand.", file=sys.stderr)
            return pd.read_parquet(path)
        raise
    CACHE.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path)
    return df


def download(url: str, name: str, max_age_h: float = 24 * 30) -> Path:
    """Raw file (Excel etc.) into data/raw/, re-downloaded after max_age_h."""
    path = RAW / name
    if _fresh(path, max_age_h):
        return path
    try:
        r = requests.get(url, headers=UA, timeout=60)
        r.raise_for_status()
    except requests.RequestException as exc:
        if path.exists():
            print(f"Hinweis: {name} nicht aktualisiert ({exc}); nutze gespeicherten Stand.", file=sys.stderr)
            return path
        raise
    RAW.mkdir(parents=True, exist_ok=True)
    path.write_bytes(r.content)
    return path
