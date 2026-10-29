"""All data adapters and the short names under which their series can be used as markets and event sources.

    A:<adapter>:<series>    as a market (chains, studies) or in kurs:/faktor: triggers, e.g. A:cboe:SKEW
    <short name>            the same via an alias, e.g. epu, skew, vix_struktur
"""

from __future__ import annotations

from qa.adapters.base import Adapter
from qa.adapters.blocked import BLOCKED
from qa.adapters.cboe import Cboe
from qa.adapters.fred import Fred

REGISTRY: dict[str, Adapter] = {a.name: a for a in [Fred(), Cboe(), *BLOCKED]}

# short name -> (symbol, display name); merged into prices.ALIASES
ALIASES = {
    "epu": ("A:fred:USEPUINDXD", "Economic Policy Uncertainty (USA)"),
    "breakeven5j": ("A:fred:T5YIE", "Breakeven-Inflation 5J"),
    "breakeven10j": ("A:fred:T10YIE", "Breakeven-Inflation 10J"),
    "inflation5j5j": ("A:fred:T5YIFR", "Inflationserwartung 5J in 5J"),
    "realzins5j": ("A:fred:DFII5", "Realzins 5J (TIPS)"),
    "realzins10j": ("A:fred:DFII10", "Realzins 10J (TIPS)"),
    "reverse_repo": ("A:fred:RRPONTSYD", "Reverse Repo der Fed"),
    "tga": ("A:fred:WTREGEN", "Treasury General Account"),
    "bankreserven": ("A:fred:WRESBAL", "Reserven der Banken"),
    "fed_bilanz_h41": ("A:fred:WALCL", "Bilanzsumme der Fed"),
    "sofr": ("A:fred:SOFR", "SOFR"),
    "finanzstress": ("A:fred:STLFSI4", "St. Louis Fed Financial Stress Index"),
    "nfci": ("A:fred:NFCI", "Chicago Fed NFCI"),
    "dollar_breit": ("A:fred:DTWEXBGS", "Dollar handelsgewichtet"),
    "laufzeitpraemie": ("A:fred:THREEFYTP10", "Laufzeitprämie 10J (Kim-Wright)"),
    "hy_spread": ("A:fred:BAMLH0A0HYM2", "Hochzins-Spread"),
    "ig_spread": ("A:fred:BAMLC0A0CM", "Investment-Grade-Spread"),
    "baa_spread": ("A:fred:BAA10Y", "Baa-Spread"),
    "vix_cboe": ("A:cboe:VIX", "VIX (Cboe)"),
    "vix3m": ("A:cboe:VIX3M", "VIX 3 Monate"),
    "vix9d": ("A:cboe:VIX9D", "VIX 9 Tage"),
    "vix6m": ("A:cboe:VIX6M", "VIX 6 Monate"),
    "vix_struktur": ("A:cboe:VIX_VIX3M", "VIX-Laufzeitstruktur (VIX/VIX3M)"),
    "skew": ("A:cboe:SKEW", "Cboe SKEW"),
    "putcall": ("A:cboe:TOTALPC", "Put/Call-Ratio gesamt (bis 2019)"),
    "putcall_aktien": ("A:cboe:EQUITYPC", "Put/Call-Ratio Aktien (bis 2019)"),
}


def split(symbol: str) -> tuple[Adapter, str]:
    """'A:fred:T10YIE' -> (adapter, 'T10YIE')."""
    _, name, series = symbol.split(":", 2)
    if name.lower() not in REGISTRY:
        raise SystemExit(f"Unbekannte Datenquelle '{name}'. Vorhanden: {', '.join(REGISTRY)}")
    return REGISTRY[name.lower()], series
