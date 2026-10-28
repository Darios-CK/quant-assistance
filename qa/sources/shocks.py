"""Central bank surprises, measured by markets in a narrow window around the announcement (free academic data).

ECB – EA-MPD (Altavilla, Brugnolini, Gürkaynak, Motto, Ragusa 2019, updated by the ECB): changes of OIS rates,
Bund yields, Euro Stoxx 50, banks and FX around every Governing Council decision since 1999, split into the press
release window and the press conference window.

Fed – Bauer & Swanson (2023), SF Fed: first principal component of 30-minute money-market futures moves around
every FOMC announcement since 1988, raw and "orthogonalised" (cleaned of what was predictable beforehand).
The public update currently ends in December 2023.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from qa.cache import download

ECB_URL = "https://www.ecb.europa.eu/pub/pdf/annex/Dataset_EA-MPD.xlsx"
FED_URL = "https://www.frbsf.org/wp-content/uploads/monetary-policy-surprises-data.xlsx"
BERLIN, NEW_YORK = ZoneInfo("Europe/Berlin"), ZoneInfo("America/New_York")


@dataclass
class EventSet:
    """One kind of event: ts (UTC) and surprise per row, plus what the surprise means."""
    name: str
    unit: str
    measure: str
    source: str
    df: pd.DataFrame
    notes: list[str] = field(default_factory=list)


def _ecb_date(v) -> pd.Timestamp:
    # most rows are real dates; rows added since late 2023 are text in day/month/year order
    return pd.Timestamp(v) if not isinstance(v, str) else pd.to_datetime(v.strip(), format="%d/%m/%Y")


def _ecb_sheet(sheet: str) -> pd.DataFrame:
    df = pd.read_excel(download(ECB_URL, "ea_mpd.xlsx"), sheet_name=sheet)
    df["date"] = df["date"].map(_ecb_date)
    return df.set_index("date").sort_index()


ECB_MEASURES = {
    # key: (sheet, column, description)
    "zins": ("Press Release Window", "OIS_1M",
             "Zins-Überraschung: Änderung des 1-Monats-OIS-Satzes rund um die Pressemitteilung (Bp)"),
    "ausblick": ("Press Conference Window", "DE2Y",
                 "Ausblick-Überraschung: Änderung der 2-jährigen Bund-Rendite während der Pressekonferenz (Bp)"),
    "gesamt": ("Monetary Event Window", "DE2Y",
               "Gesamt-Überraschung: Änderung der 2-jährigen Bund-Rendite von vor der Mitteilung bis nach der Pressekonferenz (Bp)"),
}


def classify(rate_move: pd.Series, stock_move: pd.Series) -> pd.Series:
    """Jarociński–Karadi sign rule: rates and stocks in opposite directions = policy shock,
    same direction = information shock (the central bank revealed news about the economy)."""
    prod = np.sign(rate_move) * np.sign(stock_move)
    return pd.Series(np.where(prod < 0, "zins-schock", np.where(prod > 0, "info-schock", "unklar")), index=rate_move.index)


def ecb(measure: str = "gesamt") -> EventSet:
    sheet, col, desc = ECB_MEASURES[measure]
    df = _ecb_sheet(sheet)
    full = _ecb_sheet("Monetary Event Window")
    surprise = df[col].fillna(df["OIS_3M"]) if col == "OIS_1M" else df[col]
    art = classify(full["DE2Y"], full["STOXX50"]).reindex(df.index)
    # decision published 13:45 (until 2021) or 14:15 (since 2022) Frankfurt time – both before the European close
    ts = [datetime(d.year, d.month, d.day, 14, 15, tzinfo=BERLIN) for d in df.index]
    out = pd.DataFrame({"ts": pd.to_datetime(ts, utc=True), "surprise": surprise.to_numpy(float), "art": art.to_numpy()})
    out = out.dropna(subset=["surprise"]).reset_index(drop=True)
    return EventSet("EZB-Sitzungen", "Bp", desc, "EA-MPD (EZB), " + ECB_URL, out,
                    ["Art: Zins-Schock = Renditen und Aktien gegenläufig, Info-Schock = gleichläufig (Jarociński/Karadi)."])


def _fed_time(d: pd.Timestamp, t) -> datetime:
    try:
        clock = datetime.strptime(str(t).strip().lower().replace(" ", ""), "%I:%M%p")
        hour, minute = clock.hour, clock.minute
    except ValueError:
        hour, minute = 14, 0
    return datetime(d.year, d.month, d.day, hour, minute, tzinfo=NEW_YORK)


def fed(measure: str = "roh", unscheduled: bool = False) -> EventSet:
    df = pd.read_excel(download(FED_URL, "sffed_mps.xlsx"), sheet_name="FOMC (update 2023)")
    if not unscheduled:
        df = df[df["Unscheduled"] == 0]
    col = {"roh": "MPS", "bereinigt": "MPS_ORTH"}[measure]
    stocks = df["SP500"].fillna(df["SP500 emini"])
    out = pd.DataFrame({
        "ts": pd.to_datetime([_fed_time(pd.Timestamp(d), t) for d, t in zip(df["Date"], df["Time"])], utc=True),
        "surprise": df[col].to_numpy(float) * 100,   # percentage points -> basis points
        "art": classify(df["MPS"], stocks).to_numpy(),
    }).dropna(subset=["surprise"]).reset_index(drop=True)
    desc = {"roh": "Fed-Zins-Überraschung: Bewegung der Geldmarkt-Futures 30 Minuten um die Bekanntgabe (Bp)",
            "bereinigt": "Fed-Zins-Überraschung, bereinigt um vorher Vorhersehbares (Bauer/Swanson, Bp)"}[measure]
    notes = ["Öffentliches Update endet im Dezember 2023."]
    if not unscheduled:
        notes.append("Nur planmäßige Sitzungen (außerplanmäßige mit --ausserplanmaessig).")
    return EventSet("Fed-Sitzungen", "Bp", desc, "Bauer & Swanson (2023), SF Fed, " + FED_URL, out, notes)
