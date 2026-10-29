"""Calendar events (option expiry, quarter-end expiry, month turn, January, year-end rally) and elections.

Calendar dates follow fixed rules on weekdays; exchange holidays are not removed – a date on a holiday counts from
the next trading day.  All events point the same way (surprise = 1), so the test is the average reaction.
Elections: only dates that are certain; results arrive after the close, so the reaction counts from the next day.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pandas as pd

from qa.sources.shocks import EventSet

NEW_YORK, BERLIN = ZoneInfo("America/New_York"), ZoneInfo("Europe/Berlin")
FIRST_YEAR = 1990

ELECTIONS = {
    "us": ("US-Präsidentschaftswahlen", NEW_YORK, ["2000-11-07", "2004-11-02", "2008-11-04", "2012-11-06", "2016-11-08", "2020-11-03", "2024-11-05"]),
    "us_zwischenwahl": ("US-Zwischenwahlen (Kongress)", NEW_YORK, ["2002-11-05", "2006-11-07", "2010-11-02", "2014-11-04", "2018-11-06", "2022-11-08"]),
    "de": ("Bundestagswahlen", BERLIN, ["2002-09-22", "2005-09-18", "2009-09-27", "2013-09-22", "2017-09-24", "2021-09-26", "2025-02-23"]),
}

CALENDAR = {
    "optionsverfall": "Monatlicher Optionsverfall (3. Freitag im Monat)",
    "hexensabbat": "Großer Verfall / Index-Rebalancing (3. Freitag im März, Juni, September, Dezember)",
    "monatsanfang": "Erster Wochentag des Monats",
    "monatsende": "Letzter Wochentag des Monats",
    "januar": "Erster Wochentag im Januar (Januar-Effekt)",
    "santa": "Fünftletzter Wochentag des Jahres (Beginn der Santa-Claus-Rally)",
}
WEEKDAYS = {"montag": 0, "dienstag": 1, "mittwoch": 2, "donnerstag": 3, "freitag": 4}


def _third_friday(y: int, m: int) -> date:
    d = date(y, m, 15)
    return d + timedelta(days=(4 - d.weekday()) % 7)


def _first_weekday(y: int, m: int) -> date:
    d = date(y, m, 1)
    while d.weekday() > 4:
        d += timedelta(days=1)
    return d


def _last_weekday(y: int, m: int) -> date:
    d = (date(y + (m == 12), m % 12 + 1, 1) - timedelta(days=1))
    while d.weekday() > 4:
        d -= timedelta(days=1)
    return d


def dates(kind: str, until: date | None = None) -> list[date]:
    until = until or date.today()
    years = range(FIRST_YEAR, until.year + 1)
    months = [(y, m) for y in years for m in range(1, 13)]
    if kind == "optionsverfall":
        out = [_third_friday(y, m) for y, m in months]
    elif kind == "hexensabbat":
        out = [_third_friday(y, m) for y, m in months if m in (3, 6, 9, 12)]
    elif kind == "monatsanfang":
        out = [_first_weekday(y, m) for y, m in months]
    elif kind == "monatsende":
        out = [_last_weekday(y, m) for y, m in months]
    elif kind == "januar":
        out = [_first_weekday(y, 1) for y in years]
    elif kind == "santa":
        out = []
        for y in years:
            d, n = date(y, 12, 31), 0
            while True:
                if d.weekday() <= 4 and d.day != 25:          # Christmas Day: every exchange is closed
                    n += 1
                    if n == 5:
                        break
                d -= timedelta(days=1)
            out.append(d)
    elif kind in WEEKDAYS:
        d = date(FIRST_YEAR, 1, 1)
        d += timedelta(days=(WEEKDAYS[kind] - d.weekday()) % 7)
        out = []
        while d <= until:
            out.append(d)
            d += timedelta(days=7)
    else:
        raise SystemExit(f"Unbekanntes Kalender-Ereignis '{kind}'. Möglich: {', '.join(list(CALENDAR) + list(WEEKDAYS))}")
    return [d for d in out if d <= until]


def calendar(kind: str) -> EventSet:
    days = dates(kind)
    # 09:30 New York: before every close, so each market counts the day itself from its previous close
    ts = pd.to_datetime([datetime(d.year, d.month, d.day, 9, 30, tzinfo=NEW_YORK) for d in days], utc=True)
    name = CALENDAR.get(kind) or f"Jeder {kind.capitalize()}"
    return EventSet(name, "–", "Kalendertermin (alle Ereignisse gleich, getestet wird die Ø Reaktion)", "Kalenderregel",
                    pd.DataFrame({"ts": ts, "surprise": 1.0}),
                    ["Termine nach fester Regel; Börsenfeiertage nicht entfernt – fällt ein Termin auf einen Feiertag, zählt der nächste Handelstag."])


def election(kind: str) -> EventSet:
    if kind not in ELECTIONS:
        raise SystemExit(f"Unbekannte Wahl '{kind}'. Möglich: {', '.join(ELECTIONS)}")
    name, tz, days = ELECTIONS[kind]
    # results come in after the close (US) or on a Sunday (Germany): the reaction counts from the next trading day
    ts = pd.to_datetime([datetime(*map(int, d.split("-")), 20, 0, tzinfo=tz) for d in days], utc=True)
    return EventSet(name, "–", "Wahltermin (getestet wird die Ø Reaktion ab dem Handelstag nach der Wahl)", "Wahltermine (fest hinterlegt)",
                    pd.DataFrame({"ts": ts, "surprise": 1.0}),
                    [f"Nur {len(days)} Wahlen – für belastbare Aussagen sind das wenige Fälle; Ergebnis eher als Fallsammlung lesen."])


def custom(spec: str) -> EventSet:
    """Own list of dates, e.g. "2018-03-01,2019-05-05" – for events without a free data source (tariff announcements,
    product launches, scandals …).  Without a time the day counts from the previous close."""
    days = []
    for part in [x.strip() for x in spec.split(",") if x.strip()]:
        try:
            days.append(date.fromisoformat(part))
        except ValueError:
            raise SystemExit(f"Ungültiges Datum '{part}' – Format JJJJ-MM-TT, mehrere mit Komma.")
    if not days:
        raise SystemExit("termine braucht mindestens ein Datum, z. B. termine:2018-03-01,2019-05-05")
    ts = pd.to_datetime([datetime(d.year, d.month, d.day, 9, 30, tzinfo=NEW_YORK) for d in sorted(days)], utc=True)
    return EventSet("Eigene Termine", "–", "eigene Datumsliste (alle Ereignisse gleich, getestet wird die Ø Reaktion)", "eigene Liste",
                    pd.DataFrame({"ts": ts, "surprise": 1.0}),
                    ["Die Termine stammen nicht aus einer Datenquelle, sondern wurden vorgegeben – vor der Analyse auf Richtigkeit prüfen.",
                     "Ohne Uhrzeit zählt der Tag ab dem Vortagesschluss; kam die Nachricht nach Börsenschluss, liegt die Reaktion am Folgetag."])
