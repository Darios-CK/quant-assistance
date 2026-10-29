"""Command line:
    python -m qa ereignis ezb | fed | fred:<Reihe> | earnings:<Ticker> | kurs:<Symbol>  [options]
    python -m qa earnings NVDA,AMD,INTC  [--maerkte …]
    python -m qa kette chains/<datei>.json
    python -m qa backtest strategies/<datei>.json
    python -m qa maerkte
    python -m qa befehl "/overnight es" [--projekt start]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

import pandas as pd

from qa import assets as asset_loader
from qa import backtest, chain, regimes, triggers
from qa.cache import ROOT
from qa.report import render
from qa.sources import earnings, prices
from qa.sources.shocks import EventSet
from qa.study import HORIZONS, finish, pooled, study

DEFAULT_MARKETS = {
    "makro": "sp500,us2y,us10y,eurusd,gold,dax",
    "technik": "sp500,dax,us10y,eurusd,gold",
    "kalender": "sp500,dax,us10y,eurusd,gold,bitcoin",
    "wahl": "sp500,dax,us10y,eurusd,gold,dollar",
    "termine": "sp500,dax,us10y,eurusd,gold,oel,bitcoin",
    "split": "",
    "dividende": "",
    "ezb": "bund2j,bund10j,dax,stoxx50,banken_eu,immobilien_eu,eurusd,deutsche_bank,vonovia",
    "fed": "sp500,nasdaq100,us2y,us10y,eurusd,gold,dax",
    "fred": "sp500,us2y,us10y,eurusd,gold,dax",
    "kurs": "sp500,dax,us10y,eurusd,gold,bitcoin",
    "earnings": "sp500",
}
EARNINGS_HORIZONS = (0, 5, 20, 60)   # 60 days: does the price keep drifting after the surprise (post-earnings drift)?


def _bound(text: str | None, end: bool) -> pd.Timestamp | None:
    if not text:
        return None
    if re.fullmatch(r"\d{4}", text):
        text = f"{text}-12-31" if end else f"{text}-01-01"
    return pd.Timestamp(text, tz="UTC") + (pd.Timedelta(days=1) if end else pd.Timedelta(0))


def _filter(df: pd.DataFrame, args) -> tuple[pd.DataFrame, list[str]]:
    filters = []
    lo, hi = _bound(args.von, False), _bound(args.bis, True)
    if lo is not None:
        df = df[df["ts"] >= lo]
        filters.append(f"ab {args.von}")
    if hi is not None:
        df = df[df["ts"] < hi]
        filters.append(f"bis {args.bis}")
    if getattr(args, "art", "alle") != "alle":
        if "art" not in df:
            raise SystemExit("--art gibt es nur für ezb und fed")
        df = df[df["art"] == args.art]
        filters.append(args.art)
    if df.empty:
        raise SystemExit("Keine Ereignisse im gewählten Zeitraum.")
    return df, filters


def combine(df: pd.DataFrame, args) -> tuple[pd.DataFrame, list[str]]:
    """Market phases (--bedingung) and other events nearby (--zusammen-mit / --ohne, ±--fenster days)."""
    labels = []
    if getattr(args, "bedingung", None):
        df, names = regimes.filter_phases(df, [b.strip() for b in args.bedingung.split(",") if b.strip()])
        labels += [f"nur bei: {n}" for n in names]
    for flag, keep in (("zusammen_mit", True), ("ohne", False)):
        src = getattr(args, flag, None)
        if src:
            other = triggers.load(src).df
            # outside the other source's coverage "nearby" cannot be known: keep only the overlapping period
            lo, hi = other["ts"].min(), other["ts"].max()
            cut = (df["ts"] >= lo - pd.Timedelta(days=args.fenster)) & (df["ts"] <= hi + pd.Timedelta(days=args.fenster))
            if not cut.all():
                labels.append(f"nur {lo:%Y}–{hi:%Y}, soweit {src} Daten hat")
            df = df[cut]
            hit = regimes.near(df, other, args.fenster)
            df = df[hit if keep else ~hit]
            labels.append(f"{'mit' if keep else 'ohne'} {src} innerhalb ±{args.fenster} Tagen")
    if df.empty:
        raise SystemExit("Nach den Bedingungen bleiben keine Ereignisse übrig.")
    return df, labels


def _horizons(args, default) -> tuple[int, ...]:
    return tuple(int(h) for h in args.horizonte.split(",")) if args.horizonte else default


def _save(name: str, text: str, per_event: pd.DataFrame, fixed: str | None = None) -> None:
    """reports/<date>_<name>.md, or reports/auto/<fixed>.md for the daily routine (same file every day)."""
    out = ROOT / "reports" / ("auto" if fixed else "")
    out.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r'[^a-z0-9]+', '_', (fixed or name).lower()).strip('_')
    stem = out / (slug if fixed else f"{date.today():%Y-%m-%d}_{slug}")
    stem.with_suffix(".md").write_text(text, encoding="utf-8")
    per_event.to_csv(stem.with_suffix(".csv"), index=False)
    print(f"Gespeichert: {stem.with_suffix('.md')} (Bericht) und {stem.with_suffix('.csv')} (jedes Ereignis einzeln)", file=sys.stderr)


def _items(names: str, adjust: bool) -> list[dict]:
    return [{"symbol": n.strip(), "adjust": adjust} for n in names.split(",") if n.strip()]


def run_event(args) -> tuple[str, pd.DataFrame, str]:
    opts = {"mass": args.mass, "ausserplanmaessig": args.ausserplanmaessig, "methode": args.methode,
            "uhrzeit": args.uhrzeit, "schwelle": args.schwelle, "richtung": args.richtung}
    ev = triggers.load(args.quelle, **opts)
    df, filters = _filter(ev.df, args)
    df, more = combine(df, args)
    filters += more
    kind = args.quelle.split(":")[0].lower()
    default = DEFAULT_MARKETS[kind] or args.quelle.split(":", 1)[1]          # split/dividende: the stock itself
    loaded, notes = asset_loader.load(_items(args.maerkte or default, not args.ohne_bereinigung), (df["ts"].min(), df["ts"].max()))
    if not loaded:
        raise SystemExit("Keine Kursdaten verfügbar.")
    horizons = _horizons(args, HORIZONS)
    summary, per_event = study(df, loaded, horizons, one_sided=triggers.one_sided(args.quelle, **opts))
    text = render(ev, summary, df, filters, notes)
    parts = (args.quelle, args.mass or "", args.art, args.von or "", args.bis or "", args.bedingung or "",
             f"mit_{args.zusammen_mit}" if args.zusammen_mit else "", f"ohne_{args.ohne}" if args.ohne else "")
    return text, per_event, "_".join(x for x in parts if x and x != "alle")


def run_earnings(args) -> tuple[str, pd.DataFrame, str]:
    tickers = [t.strip().upper() for t in args.ticker.split(",") if t.strip()]
    horizons = _horizons(args, EARNINGS_HORIZONS)
    if len(tickers) == 1:
        # one company: how did the stock itself (and optionally other markets) react to its results?
        ev = earnings.events(tickers[0])
        df, filters = _filter(ev.df, args)
        names = tickers[0] + ("," + args.maerkte if args.maerkte else "")
        loaded, notes = asset_loader.load(_items(names, not args.ohne_bereinigung), (df["ts"].min(), df["ts"].max()))
        summary, per_event = study(df, loaded, horizons)
        text = render(ev, summary, df, filters, notes)
    else:
        # many companies: each stock against its own results, then all together
        rows, per_events, used, notes, filters = [], [], [], [], []
        for t in tickers:
            try:
                ev = earnings.events(t)
            except Exception as exc:
                notes.append(f"{t} übersprungen – keine Gewinntermine: {exc}")
                continue
            df, filters = _filter(ev.df, args)
            loaded, n = asset_loader.load(_items(t, not args.ohne_bereinigung), (df["ts"].min(), df["ts"].max()))
            notes += n
            if not loaded:
                continue
            summary, per_event = study(df, loaded, horizons)
            rows.append(summary)
            per_events.append(per_event)
            used.append(df)
        if not per_events:
            raise SystemExit("Für keine der Firmen gibt es Gewinntermine.")
        all_events = pd.concat(per_events, ignore_index=True)
        summary = finish(pd.concat([pooled(all_events, horizons, f"Alle {len(per_events)} Firmen zusammen")] + rows, ignore_index=True))
        ev = EventSet(f"Quartalszahlen von {len(per_events)} Firmen", "%", "Gewinn je Aktie gegenüber Analysten-Konsens in % (begrenzt auf ±100 %)",
                      "Yahoo Finance (Gewinntermine mit Konsens)", pd.concat(used, ignore_index=True),
                      ["Konsens laut Yahoo; ältere Quartale können lückenhaft sein.",
                       "Überraschung nur beim Gewinn je Aktie – Umsatz und Ausblick fehlen, bewegen den Kurs aber oft stärker.",
                       "Die Firmenauswahl besteht aus heute gelisteten Firmen: Pleiten und Übernahmen fehlen (Survivorship Bias)."])
        text = render(ev, summary, ev.df, filters, notes)
        per_event = all_events
    return text, per_event, f"earnings_{'_'.join(tickers)[:60]}_{args.von or ''}_{args.bis or ''}"


def run_chain(args) -> tuple[str, pd.DataFrame, str]:
    text, per_event = chain.run(Path(args.datei))
    return text, per_event, f"kette_{Path(args.datei).stem}"


def run_backtest(args) -> tuple[str, pd.DataFrame, str]:
    text, detail = backtest.run(Path(args.datei))
    return text, detail, f"backtest_{Path(args.datei).stem}"


def cmd_markets(_args) -> None:
    print("Kürzel           Symbol       Name")
    for alias, (symbol, name) in prices.ALIASES.items():
        print(f"{alias:16s} {symbol:12s} {name}")
    print("\nAußerdem jedes Yahoo-Symbol (z. B. SAP.DE, ^N225, JETS, GT) oder FRED:<Reihe> für Zinsreihen in Prozent (z. B. FRED:T10Y2Y).")


def _common(p: argparse.ArgumentParser) -> None:
    p.add_argument("--maerkte", help="Kommaliste, z. B. dax,banken_eu,SAP.DE,FRED:DGS2 (Liste: python -m qa maerkte)")
    p.add_argument("--von", help="Jahr oder Datum, z. B. 2008")
    p.add_argument("--bis", help="Jahr oder Datum, z. B. 2021")
    p.add_argument("--horizonte", help="Handelstage nach dem Reaktionstag, z. B. 0,5,20")
    p.add_argument("--ohne-bereinigung", action="store_true", help="Einzelaktien nicht um die Indexbewegung bereinigen")
    p.add_argument("--ablage", help="fester Name unter reports/auto/ (für den täglichen Lauf)")


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python -m qa", description="Quant-Analyst – Ereignis-Analysen auf freien Daten")
    sub = p.add_subparsers(dest="cmd", required=True)

    e = sub.add_parser("ereignis", help="Wie reagierten Märkte auf Ereignisse?")
    e.add_argument("quelle", help="ezb | fed | fred:<Reihe> | makro:<Name> | earnings:<Ticker> | kurs:<Symbol> | technik:<Symbol>:<Marke> | "
                                  "kalender:<Art> | wahl:<Art> | split:<Ticker> | dividende:<Ticker> | termine:<Datum,…>")
    e.add_argument("--mass", choices=["zins", "ausblick", "gesamt", "roh", "bereinigt"],
                   help="ezb zins|ausblick|gesamt (Standard gesamt), fed roh|bereinigt (Standard roh)")
    e.add_argument("--art", default="alle", choices=["alle", "zins-schock", "info-schock"], help="nur Zins- oder Informations-Schocks (ezb, fed)")
    e.add_argument("--methode", default="naiv", choices=["naiv", "veraenderung"], help="Überraschung bei FRED-Reihen")
    e.add_argument("--uhrzeit", default="08:30", help="Veröffentlichungszeit New York bei FRED-Reihen")
    e.add_argument("--schwelle", type=float, default=2.0, help="kurs: Schock ab so vielen Standardabweichungen (Standard 2)")
    e.add_argument("--richtung", default="beide", choices=["beide", "hoch", "runter"], help="kurs: nur Anstiege, nur Rückgänge oder beide")
    e.add_argument("--ausserplanmaessig", action="store_true", help="fed: auch außerplanmäßige Sitzungen")
    e.add_argument("--bedingung", help="nur Ereignisse in diesen Marktphasen (Kommaliste, alle müssen gelten): " + ", ".join(regimes.PHASES))
    e.add_argument("--zusammen-mit", dest="zusammen_mit", help="nur Ereignisse, bei denen eine andere Quelle in der Nähe lag, z. B. fed oder makro:nfp")
    e.add_argument("--ohne", help="nur Ereignisse OHNE eine andere Quelle in der Nähe")
    e.add_argument("--fenster", type=int, default=3, help="Abstand in Kalendertagen für --zusammen-mit/--ohne (Standard 3)")
    _common(e)
    e.set_defaults(func=run_event)

    g = sub.add_parser("earnings", help="Reaktion auf Quartalszahlen (eine Firma oder viele zusammen)")
    g.add_argument("ticker", help="ein Ticker (mit --maerkte: wer reagiert noch?) oder Kommaliste mehrerer Firmen")
    _common(g)
    g.set_defaults(func=run_earnings)

    k = sub.add_parser("kette", help="Kausalkette aus einer JSON-Datei Glied für Glied prüfen")
    k.add_argument("datei", help="z. B. chains/oel_transport.json")
    k.add_argument("--ablage", help="fester Name unter reports/auto/ (für den täglichen Lauf)")
    k.set_defaults(func=run_chain)

    b = sub.add_parser("backtest", help="Strategie aus einer JSON-Datei testen (Kosten, Testzeitraum, Walk-Forward, Deflated Sharpe, PBO)")
    b.add_argument("datei", help="z. B. strategies/trend_dax.json")
    b.add_argument("--ablage", help="fester Name unter reports/auto/ (für den täglichen Lauf)")
    b.set_defaults(func=run_backtest)

    m = sub.add_parser("maerkte", help="Kürzel für Märkte anzeigen")
    m.set_defaults(func=cmd_markets)

    c = sub.add_parser("chat", help="Freie Frage an den Copilot über die Claude-API (braucht ANTHROPIC_API_KEY, kostet je Frage Geld)")
    c.add_argument("frage", nargs="+")
    c.set_defaults(func=cmd_chat)

    k2 = sub.add_parser("katalog", help="welche Markttreiber mit freien Daten messbar sind")
    k2.set_defaults(func=cmd_catalog)

    b2 = sub.add_parser("befehl", help="Slash-Befehl ausführen, z. B. '/overnight es' oder '/commands'")
    b2.add_argument("zeile", nargs="+")
    b2.add_argument("--projekt", default=None)
    b2.set_defaults(func=cmd_command)

    r = sub.add_parser("routine", help="alle Analysen aus routine.json nach reports/auto/ rechnen (täglicher Lauf)")
    r.set_defaults(func=cmd_routine)
    return p


def cmd_chat(args) -> None:
    from qa import agent

    ok, why = agent.available()
    if not ok:
        raise SystemExit(why)
    step = lambda name, i, out, err: print(f"→ {name} {json.dumps(i, ensure_ascii=False)[:160]}{'  (Fehler)' if err else ''}", file=sys.stderr)  # noqa: E731
    text, _, usage = agent.ask(" ".join(args.frage), [], on_step=step)
    print(text)
    print(f"\n[{usage['steps']} Werkzeug-Aufrufe · {usage['input'] + usage['cache_read'] + usage['cache_write']} Eingabe- / {usage['output']} Ausgabe-Tokens · ca. {usage['cost_usd']:.2f} $]", file=sys.stderr)


def cmd_command(args) -> None:
    from qa import commands

    for res in commands.run(" ".join(args.zeile), commands.Ctx(args.projekt)):
        print(res.text)
        if res.artifact:
            print(f"(gespeichert: {args.projekt}/{res.artifact})", file=sys.stderr)


def cmd_catalog(_args) -> None:
    from qa import catalog

    print(catalog.as_markdown())


def cmd_routine(_args) -> int:
    from qa.routine import run_all

    return run_all()


def run(argv: list[str]) -> tuple[str, pd.DataFrame, str]:
    """Run one analysis without printing or saving – used by the web app and the daily routine."""
    args = parser().parse_args(argv)
    return args.func(args)


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.func in (cmd_markets, cmd_chat, cmd_catalog, cmd_command):
        args.func(args)
        return 0
    if args.func is cmd_routine:
        failed = cmd_routine(args)
        print(f"Routine fertig, {failed} Bericht(e) fehlgeschlagen. Übersicht: reports/auto/README.md", file=sys.stderr)
        return 0                                   # partial results are still published
    text, per_event, name = args.func(args)
    print(text)
    _save(name, text, per_event, getattr(args, "ablage", None))
    return 0


if __name__ == "__main__":
    sys.exit(main())
