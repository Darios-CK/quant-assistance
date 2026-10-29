"""One way to name an event source, shared by the command line, chain files, backtests and the AI chat.

    ezb                         ECB meetings (EA-MPD)           options: mass = zins | ausblick | gesamt
    fed                         FOMC meetings (Bauer/Swanson)   options: mass = roh | bereinigt, ausserplanmaessig
    fred:<series>               macro release (ALFRED)          options: methode = naiv | veraenderung, uhrzeit
    makro:<name>                the same with a short name: cpi, kerninflation, pce, ppi, nfp, arbeitslosenquote,
                                erstantraege, bip, einzelhandel, industrieproduktion, verbrauchervertrauen,
                                handelsbilanz, geldmenge_m2, fed_bilanz, oel_lager, baubeginne
    earnings:<ticker>           company results vs consensus (Yahoo)
    kurs:<symbol>               price shocks                    options: schwelle (σ, default 2), richtung = hoch | runter | beide
    technik:<symbol>:<mark>     sma200_hoch | sma200_runter | hoch52 | tief52
    kalender:<kind>             optionsverfall | hexensabbat | monatsanfang | monatsende | januar | santa | montag … freitag
    wahl:<kind>                 us | us_zwischenwahl | de
    split:<ticker>              stock splits (Yahoo)
    dividende:<ticker>          dividend ex-dates, surprise = change of the dividend (Yahoo)
    termine:<date,date,…>       own list of dates (YYYY-MM-DD) for events without a free source
    faktor:<alias|A:quelle:reihe>  unusual change of a data series (epu, skew, vix_struktur, finanzstress, sofr …),
                                stamped with its publication time   options: schwelle, richtung
"""

from __future__ import annotations

from qa.sources import calendar, corporate, earnings, fred, moves, shocks
from qa.sources.shocks import EventSet

ONE_SIDED = ("kalender", "wahl", "technik", "split", "termine")


def load(source: str, **opt) -> EventSet:
    kind, _, arg = source.partition(":")
    kind = kind.lower()
    if kind == "ezb":
        return shocks.ecb(opt.get("mass") or "gesamt")
    if kind == "fed":
        return shocks.fed(opt.get("mass") or "roh", unscheduled=bool(opt.get("ausserplanmaessig")))
    if kind in ("fred", "makro"):
        return fred.macro(arg, opt.get("methode") or "naiv", opt.get("uhrzeit"))
    if kind == "earnings":
        return earnings.events(arg.upper())
    if kind == "kurs":
        return moves.events(arg, float(opt.get("schwelle") or 2.0), opt.get("richtung") or "beide")
    if kind == "technik":
        symbol, _, mark = arg.rpartition(":")
        if not symbol:
            raise SystemExit("technik braucht Symbol und Marke, z. B. technik:^GSPC:sma200_runter")
        return moves.technical(symbol, mark)
    if kind == "kalender":
        return calendar.calendar(arg.lower())
    if kind == "wahl":
        return calendar.election(arg.lower())
    if kind in ("split", "dividende"):
        return corporate.events(kind, arg)
    if kind == "termine":
        return calendar.custom(arg)
    if kind == "faktor":
        from qa.adapters import events as series_events

        return series_events.events(arg, float(opt.get("schwelle") or 2.0), opt.get("richtung") or "beide")
    raise SystemExit(f"Unbekannte Quelle '{source}'. Möglich: ezb, fed, fred:<Reihe>, makro:<Name>, earnings:<Ticker>, "
                     "kurs:<Symbol>, faktor:<Reihe>, technik:<Symbol>:<Marke>, kalender:<Art>, wahl:<Art>, split:<Ticker>, dividende:<Ticker>, termine:<Datum,…>")


def one_sided(source: str, **opt) -> bool:
    """All events point the same way: test the average reaction, not a slope."""
    kind = source.split(":")[0].lower()
    if kind in ONE_SIDED:
        return True
    return kind in ("kurs", "faktor") and (opt.get("richtung") or "beide") in ("hoch", "runter")
