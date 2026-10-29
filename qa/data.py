"""Data API – the same functions for the website, the Copilot commands, MCP and your own Python scripts.

    from qa import data
    data.search("siemens")                 # symbols (aliases, futures, Yahoo search)
    data.resolve("es")                     # alias -> canonical symbol, source, unit, exchange
    data.coverage("ES=F")                  # which data and which period
    data.bars("NQ=F", "5m", days=5)        # candles from 1 minute to 1 month
    data.closes("dax")                     # daily closes (aliases work)
    data.option_chain("AAPL")              # today's option chain (no history)

Honest limits of free data (Yahoo): intraday candles only for recent days (1m: 30 days, ≤90m: 60 days, 1h: 730 days),
no single trades, no quotes, no order book, no option history; futures are front month without roll adjustment.
"""

from __future__ import annotations

import warnings
from datetime import datetime

import pandas as pd

from qa.cache import CACHE, RAW
from qa.sources import prices

# interval -> how many calendar days back Yahoo serves it (None = full history)
INTERVALS = {"1m": 30, "2m": 60, "5m": 60, "15m": 60, "30m": 60, "60m": 730, "90m": 60, "1h": 730,
             "1d": None, "5d": None, "1wk": None, "1mo": None, "3mo": None}
PREVIEW_MAX_BARS, PREVIEW_MAX_DAYS = 500, 31
KINDS = {"aktie": "EQUITY", "etf": "ETF", "index": "INDEX", "future": "FUTURE", "waehrung": "CURRENCY",
         "krypto": "CRYPTOCURRENCY", "fonds": "MUTUALFUND"}

SCHEMAS = {
    "kerzen": ("Kerzen (OHLCV) – `data.bars`, `/kerzen`", {
        "datum": "Beginn der Kerze (Börsenzeit; bei Tageskerzen nur das Datum)",
        "open / high / low / close": "Eröffnung, Hoch, Tief, Schluss – um Splits und Dividenden bereinigt",
        "volume": "gehandelte Stück/Kontrakte (bei Indizes und Devisen oft 0)"}),
    "schlusskurse": ("Tagesschlusskurse – `data.closes`", {
        "date": "Handelstag", "close": "Schlusskurs; bei FRED/Bundesbank/EZB-Zinsreihen der Zins in Prozent"}),
    "ereignisse": ("Ereignisse – Grundlage jeder Ereignis-Analyse", {
        "ts": "Zeitpunkt der Veröffentlichung (UTC)", "surprise": "Überraschung (Einheit je Quelle, z. B. Basispunkte)",
        "art": "nur EZB/Fed: zins-schock oder info-schock"}),
    "reaktionen": ("Reaktionen je Ereignis (CSV einer Ereignis-Analyse)", {
        "ts / datum": "Ereignis", "markt": "gemessener Markt", "h": "Horizont in Handelstagen",
        "reaktion": "Veränderung ab Schluss vor dem Ereignis (Prozent bzw. Basispunkte)",
        "bereinigt": "marktbereinigt (minus Beta × Index), falls Einzelwert"}),
    "backtest": ("Backtest-Detail (CSV)", {
        "datum": "Handelstag", "position": "gehaltene Position (1 long, 0 flach, -1 short)",
        "rendite_strategie": "Tagesrendite nach Kosten", "rendite_markt": "Tagesrendite Kaufen-und-Halten"}),
    "optionskette": ("Optionskette – `data.option_chain` (nur aktueller Stand)", {
        "contractSymbol": "Kontrakt", "strike": "Basispreis", "lastPrice / bid / ask": "letzter Preis, Geld, Brief",
        "volume / openInterest": "Umsatz heute, offene Kontrakte", "impliedVolatility": "implizite Volatilität",
        "inTheMoney": "im Geld"}),
    "trades": ("Eigene Trades (CSV zum Hochladen) – `/trades`", {
        "datum": "Einstiegstag (JJJJ-MM-TT), Pflicht", "symbol": "Markt (Kürzel oder Yahoo-Symbol), optional",
        "richtung": "long oder short, optional (Standard long)"}),
    "orderbuch": ("Orderbuch / einzelne Trades / Quotes", {
        "–": "gratis nicht verfügbar (QuantPad bezieht das von CME/Nasdaq/NYSE gegen Bezahlung)"}),
}


def resolve(name: str) -> dict:
    """Alias or ticker -> canonical symbol with source, unit and where its daily value is set."""
    symbol, label = prices.resolve(name)
    s = symbol.upper()
    source = ("FRED" if s.startswith("FRED:") else "Bundesbank" if s.startswith("BBK:") else "EZB" if s.startswith("EZB:")
              else "Yahoo Finance")
    kind = ("Future" if s.endswith("=F") else "Devisen" if s.endswith("=X") else "Index" if s.startswith("^")
            else "Krypto" if s.endswith("-USD") else "Zinsreihe" if source != "Yahoo Finance" and prices.unit(symbol) == "bp"
            else "Aktie/ETF")
    return {"eingabe": name, "symbol": symbol, "name": label, "quelle": source, "art": kind,
            "einheit": "Basispunkte" if prices.unit(symbol) == "bp" else "Prozent",
            "boerse": {"eu": "Frankfurt 17:30", "us": "New York 16:00", "crypto": "UTC Mitternacht",
                       "ecb_fix": "EZB-Fixing 14:15"}[prices.market(symbol)],
            "vergleichsindex": prices.default_bench(symbol) or "–"}


def search(query: str, kind: str = "", limit: int = 15) -> list[dict]:
    """Aliases and futures first, then Yahoo's symbol search.  kind: aktie, etf, index, future, waehrung, krypto, fonds."""
    q = query.strip().lower()
    want = KINDS.get(kind.lower(), "") if kind else ""
    out = []
    for alias, (symbol, label) in prices.ALIASES.items():
        typ = "FUTURE" if symbol.endswith("=F") else "INDEX" if symbol.startswith("^") else ""
        if (q in alias or q in label.lower() or q == symbol.lower()) and (not want or want == typ):
            out.append({"symbol": symbol, "name": label, "art": typ.lower() or "kürzel", "kuerzel": alias, "boerse": ""})
    try:
        import yfinance as yf

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            quotes = yf.Search(query, max_results=limit, news_count=0).quotes
        for r in quotes:
            if want and r.get("quoteType") != want:
                continue
            out.append({"symbol": r.get("symbol", ""), "name": r.get("shortname") or r.get("longname") or "",
                        "art": str(r.get("quoteType", "")).lower(), "kuerzel": "", "boerse": r.get("exchDisp", r.get("exchange", ""))})
    except Exception as exc:
        out.append({"symbol": "", "name": f"Yahoo-Suche nicht erreichbar: {exc}", "art": "", "kuerzel": "", "boerse": ""})
    seen, unique = set(), []
    for r in out:
        if r["symbol"] not in seen or not r["symbol"]:
            seen.add(r["symbol"])
            unique.append(r)
    return unique[:limit]


def closes(name: str) -> pd.Series:
    return prices.closes(prices.resolve(name)[0])


def bars(name: str, interval: str = "1d", days: int | None = None, start: str | None = None, end: str | None = None) -> pd.DataFrame:
    """OHLCV candles.  Daily and longer: full history (cached).  Intraday: only as far back as Yahoo serves it."""
    if interval not in INTERVALS:
        raise SystemExit(f"Unbekanntes Intervall '{interval}'. Möglich: {', '.join(INTERVALS)}")
    symbol = prices.resolve(name)[0]
    if symbol.upper().startswith(prices.OFFICIAL):
        if interval != "1d":
            raise SystemExit(f"{symbol} gibt es nur als Tageswerte")
        c = prices.closes(symbol)
        df = pd.DataFrame({"open": c, "high": c, "low": c, "close": c, "volume": 0.0})
    elif interval == "1d":
        df = prices.ohlc(symbol)
    else:
        import yfinance as yf

        limit = INTERVALS[interval]
        lo = pd.Timestamp(start) if start else pd.Timestamp.now() - pd.Timedelta(days=days or (limit or 365))
        if limit and lo < pd.Timestamp.now() - pd.Timedelta(days=limit - 1):
            raise SystemExit(f"Yahoo liefert {interval}-Kerzen nur für die letzten {limit} Tage")
        kw = {"interval": interval, "start": lo.strftime("%Y-%m-%d"), "auto_adjust": True}
        if end:
            kw["end"] = end
        if interval == "1m":                         # Yahoo serves 1-minute candles in pieces of at most 7 days
            parts, a = [], lo
            stop = pd.Timestamp(end) if end else pd.Timestamp.now() + pd.Timedelta(days=1)
            while a < stop:
                b = min(a + pd.Timedelta(days=7), stop)
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    parts.append(yf.Ticker(symbol).history(interval="1m", start=a.strftime("%Y-%m-%d"), end=b.strftime("%Y-%m-%d"), auto_adjust=True))
                a = b
            h = pd.concat([p for p in parts if not p.empty]) if any(not p.empty for p in parts) else pd.DataFrame()
        else:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                h = yf.Ticker(symbol).history(**kw)
        if h.empty:
            raise SystemExit(f"Yahoo liefert keine {interval}-Kerzen für {symbol}")
        df = h[["Open", "High", "Low", "Close", "Volume"]].astype(float)
        df.columns = ["open", "high", "low", "close", "volume"]
        df.index = df.index.rename("datum")
        return df
    if interval in ("5d", "1wk", "1mo", "3mo"):
        rule = {"5d": "5B", "1wk": "W-FRI", "1mo": "ME", "3mo": "QE"}[interval]
        df = df.resample(rule).agg({"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}).dropna()
    if start:
        df = df[df.index >= pd.Timestamp(start)]
    if end:
        df = df[df.index <= pd.Timestamp(end)]
    if days and not start:
        df = df[df.index >= df.index[-1] - pd.Timedelta(days=days)]
    return df.rename_axis("datum")


def preview_bars(name: str, interval: str = "1d", days: int = 31) -> pd.DataFrame:
    """At most 500 candles over at most 31 days – for a quick look; for more use data.bars in a script."""
    df = bars(name, interval, days=min(int(days), PREVIEW_MAX_DAYS))
    return df.tail(PREVIEW_MAX_BARS)


def coverage(name: str) -> dict:
    info = resolve(name)
    symbol = info["symbol"]
    out = info | {"tageswerte": "–", "intraday": "–", "optionen": "–"}
    try:
        c = prices.closes(symbol)
        out["tageswerte"] = f"{c.index[0]:%d.%m.%Y} – {c.index[-1]:%d.%m.%Y} ({len(c):,} Tage)".replace(",", ".")
    except Exception as exc:
        out["tageswerte"] = f"keine: {exc}"
    if info["quelle"] == "Yahoo Finance":
        out["intraday"] = "1m: 30 Tage · 2m–90m: 60 Tage · 1h: 730 Tage (Yahoo-Grenze, rückwirkend ab heute)"
        try:
            import yfinance as yf

            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                exp = yf.Ticker(symbol).options
            out["optionen"] = f"{len(exp)} Verfallstermine, nur aktueller Stand (keine Historie)" if exp else "keine"
        except Exception:
            out["optionen"] = "keine"
    else:
        out["intraday"] = "keine (nur Tageswerte)"
    return out


def option_chain(name: str, expiry: str | None = None) -> tuple[str, pd.DataFrame, pd.DataFrame, list[str]]:
    import yfinance as yf

    symbol = prices.resolve(name)[0]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        t = yf.Ticker(symbol)
        expiries = list(t.options)
        if not expiries:
            raise SystemExit(f"Yahoo hat keine Optionen für {symbol}")
        exp = expiry if expiry in expiries else expiries[0]
        ch = t.option_chain(exp)
    cols = ["contractSymbol", "strike", "lastPrice", "bid", "ask", "volume", "openInterest", "impliedVolatility", "inTheMoney"]
    return exp, ch.calls[cols], ch.puts[cols], expiries


def usage() -> dict:
    """What this installation has loaded and stored."""
    files = list(CACHE.glob("*.parquet")) + (list(RAW.glob("*")) if RAW.exists() else [])
    by_source: dict[str, int] = {}
    for f in files:
        src = f.name.split("_")[0]
        by_source[src] = by_source.get(src, 0) + 1
    newest = max((f.stat().st_mtime for f in files), default=None)
    return {"dateien": len(files), "groesse_mb": round(sum(f.stat().st_size for f in files) / 1e6, 1),
            "je_quelle": dict(sorted(by_source.items())),
            "zuletzt": datetime.fromtimestamp(newest).strftime("%d.%m.%Y %H:%M") if newest else "–"}


GUIDE = f"""# Daten-Anleitung

**Kerzen:** `/kerzen <symbol> [intervall] [tage]` zeigt eine Vorschau (höchstens {PREVIEW_MAX_BARS} Kerzen über {PREVIEW_MAX_DAYS} Tage).
Für mehr in einem Python-Skript im Projekt: `from qa import data; df = data.bars("NQ=F", "5m", days=30)`.
Intervalle: {", ".join(INTERVALS)}. Yahoo-Grenzen: 1m nur 30 Tage, 2m–90m 60 Tage, 1h 730 Tage, Tag und länger die ganze Historie.

**Futures:** Kürzel wie bei der CME (`es`, `nq`, `zn`, `cl`, `gc`, `6e` …, Liste unter Daten). Yahoo liefert den vordersten
Kontrakt ohne Roll-Bereinigung: an Rolltagen springt der Kurs. Für lange Backtests besser ETFs/Indizes oder Renditen ohne Rolltage.

**Ticks, Quotes, Orderbuch:** gratis nicht verfügbar. Nächstbester Ersatz: 1-Minuten-Kerzen der letzten 30 Tage.

**Optionen:** `/optionen <symbol> [verfall]` zeigt die aktuelle Kette (Yahoo). Eine Historie von Optionspreisen gibt es gratis nicht.

**Große Abfragen:** Tagesdaten werden einmal geladen und 12 Stunden zwischengespeichert (`data/cache`). Intraday wird
nicht gespeichert – im Skript selbst sichern, z. B. `df.to_parquet("nq_5m.parquet")`.

**Weitere Quellen:** `FRED:<Reihe>` (US-Zinsen, Spreads), `BBK:<flow>/<key>` (Bundesbank), `EZB:<flow>/<key>` (EZB),
Makro-Erstveröffentlichungen über `makro:<name>` (braucht FRED-Schlüssel).
"""


def table(rows: list[dict]) -> str:
    if not rows:
        return "_keine Treffer_"
    keys = list(rows[0])
    return "\n".join(["| " + " | ".join(keys) + " |", "|" + "---|" * len(keys)] +
                     ["| " + " | ".join(str(r.get(k, "")) for k in keys) + " |" for r in rows])


def frame_md(df: pd.DataFrame, digits: int = 4) -> str:
    """Markdown table of a frame with a date index; one number format per column."""
    def fmt_i(i):
        return i.strftime("%d.%m.%Y %H:%M") if (getattr(i, "hour", 0) or getattr(i, "minute", 0)) else i.strftime("%d.%m.%Y")

    def fmt_col(col: pd.Series) -> list[str]:
        v = col.to_numpy()
        if col.dtype.kind not in "fi":
            return [str(x) for x in v]
        finite = v[~pd.isna(v)]
        if len(finite) and (finite == finite.round()).all():
            d = 0
        else:
            d = 2 if len(finite) and abs(finite).max() >= 100 else digits
        return ["–" if pd.isna(x) else f"{x:,.{d}f}".replace(",", " ") for x in v]

    cols = [fmt_col(df[c]) for c in df.columns]
    head = "| datum | " + " | ".join(map(str, df.columns)) + " |"
    rows = [f"| {fmt_i(i)} | " + " | ".join(c[k] for c in cols) + " |" for k, i in enumerate(df.index)]
    return "\n".join([head, "|---" * (len(df.columns) + 1) + "|"] + rows)
