"""One way to name an event source, shared by the command line and chain files.

    ezb                 ECB meetings (EA-MPD)           options: mass = zins | ausblick | gesamt
    fed                 FOMC meetings (Bauer/Swanson)   options: mass = roh | bereinigt, ausserplanmaessig
    fred:<series>       macro release (ALFRED)          options: methode = naiv | veraenderung, uhrzeit
    earnings:<ticker>   company results vs consensus (Yahoo)
    kurs:<symbol>       price shocks                    options: schwelle (σ, default 2), richtung = hoch | runter | beide
"""

from __future__ import annotations

from qa.sources import earnings, fred, moves, shocks
from qa.sources.shocks import EventSet


def load(source: str, **opt) -> EventSet:
    kind, _, arg = source.partition(":")
    kind = kind.lower()
    if kind == "ezb":
        return shocks.ecb(opt.get("mass") or "gesamt")
    if kind == "fed":
        return shocks.fed(opt.get("mass") or "roh", unscheduled=bool(opt.get("ausserplanmaessig")))
    if kind == "fred":
        return fred.macro(arg, opt.get("methode") or "naiv", opt.get("uhrzeit") or "08:30")
    if kind == "earnings":
        return earnings.events(arg.upper())
    if kind == "kurs":
        return moves.events(arg, float(opt.get("schwelle") or 2.0), opt.get("richtung") or "beide")
    raise SystemExit(f"Unbekannte Quelle '{source}'. Möglich: ezb, fed, fred:<Reihe>, earnings:<Ticker>, kurs:<Symbol>")


def one_sided(source: str, **opt) -> bool:
    """All events point the same way (only up- or only down-shocks): test the average reaction, not a slope."""
    return source.lower().startswith("kurs:") and (opt.get("richtung") or "beide") in ("hoch", "runter")
