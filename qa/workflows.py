"""Research workflows from the start page: overnight vs. session, P&L by market phase, what the market did before your
own entries, rolling walk-forward, a /review of common mistakes and /goal (search a parameter grid until a target is met).

Same rules as everywhere: only information known at the time, every variant counts, the test period is used once.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from qa import backtest, metrics, regimes
from qa.report import num
from qa.sources import prices

DAYS = 252


def _pct(v, d=2, sign=True) -> str:
    return "–" if v is None or (isinstance(v, float) and np.isnan(v)) else num(v * 100, d, sign, " %")


def _t(r: pd.Series) -> tuple[float, float]:
    r = r.dropna()
    if len(r) < 20 or r.std() == 0:
        return np.nan, np.nan
    t, p = stats.ttest_1samp(r, 0.0)
    return float(t), float(p)


# ---------------------------------------------------------------- overnight vs. regular session
def split_sessions(df: pd.DataFrame) -> pd.DataFrame:
    """Overnight = open / previous close − 1, session = close / open − 1.  Drops the stretch where the source carries
    no real opening price (open equals close or the previous close on most days – common in old Yahoo index data)."""
    d = df[["open", "close"]].dropna()
    d = d[(d["open"] > 0) & (d["close"] > 0)]
    prev = d["close"].shift(1)
    fake = (d["open"] == d["close"]) | (d["open"] == prev)
    share = fake.groupby(d.index.year).mean()
    bad = share[share > 0.5]
    if len(bad):
        d, prev = d[d.index.year > bad.index.max()], prev[d.index.year > bad.index.max()]
    out = pd.DataFrame({"overnight": d["open"] / prev - 1, "handelszeit": d["close"] / d["open"] - 1}).dropna()
    out["gesamt"] = (1 + out["overnight"]) * (1 + out["handelszeit"]) - 1
    return out


def overnight(name: str, von: str | None = None) -> tuple[str, pd.DataFrame]:
    symbol, label = prices.resolve(name)
    if symbol.upper().startswith(prices.OFFICIAL):
        raise SystemExit(f"{label} hat keine Eröffnungskurse (nur Tageswerte)")
    s = split_sessions(prices.ohlc(symbol))
    if von:
        s = s[s.index >= pd.Timestamp(von)]
    if len(s) < 250:
        raise SystemExit(f"Zu wenige Tage mit echten Eröffnungskursen für {label} ({len(s)})")
    rows = ["| Teil | Ø je Tag | p. a. (Summe) | Sharpe | Anteil ↑ | t | p | Gesamt (verkettet) |", "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for col, title in (("overnight", "Über Nacht (Schluss → Eröffnung)"), ("handelszeit", "Handelszeit (Eröffnung → Schluss)"), ("gesamt", "Ganzer Tag")):
        r = s[col]
        t, p = _t(r)
        rows.append(f"| {title} | {_pct(r.mean(), 3)} | {_pct(r.mean() * DAYS, 1)} | {num(metrics.sharpe(r), 2)} | "
                    f"{_pct((r > 0).mean(), 0, False)} | {num(t, 1)} | {num(p, 3)} | {_pct(metrics.equity(r).iloc[-1] - 1, 0)} |")
    years = s.groupby(s.index.year)[["overnight", "handelszeit"]].apply(lambda g: (1 + g).prod() - 1)
    share_on = float((years["overnight"] > years["handelszeit"]).mean())
    half = s.index[len(s) // 2]
    halves = [(f"{a:%Y}–{b:%Y}", s.loc[a:b]) for a, b in ((s.index[0], half), (half, s.index[-1]))]
    lines = [f"# Über Nacht vs. Handelszeit: {label}", "",
             f"- **Zeitraum:** {s.index[0]:%d.%m.%Y} – {s.index[-1]:%d.%m.%Y} ({len(s):,} Handelstage)".replace(",", "."),
             f"- **In {share_on:.0%} der Jahre** brachte die Nacht mehr als die Handelszeit.", "", *rows, "",
             "## Hälften (Stabilität)", "", "| Zeitraum | Über Nacht Ø | Handelszeit Ø |", "|---|---:|---:|"]
    lines += [f"| {n} | {_pct(g['overnight'].mean(), 3)} | {_pct(g['handelszeit'].mean(), 3)} |" for n, g in halves]
    lines += ["", "## Hinweise", "",
              "- Eröffnungs- und Schlusskurse von Yahoo (um Dividenden bereinigt; die Bereinigung verteilt sich nicht exakt auf Nacht und Tag).",
              "- Jahre ohne echte Eröffnungskurse (Eröffnung = Schluss) sind ausgeschlossen.",
              "- Keine Kosten: wer jede Nacht hält, zahlt zweimal täglich Spread und Gebühren.",
              "- Futures handeln fast rund um die Uhr; ihre „Nacht“ ist die Zeit zwischen den Tageskerzen von Yahoo."]
    chart = pd.DataFrame({"Über Nacht": metrics.equity(s["overnight"]), "Handelszeit": metrics.equity(s["handelszeit"])})
    return "\n".join(lines) + "\n", chart


# ---------------------------------------------------------------- P&L by market phase
def phase_pnl(r: pd.Series, bench: pd.Series, phases: list[str] | None = None) -> list[dict]:
    """Daily strategy returns grouped by the phase known at the PREVIOUS close (the day the position was set)."""
    out = []
    for name in phases or list(regimes.PHASES):
        try:
            s = regimes.state(name)
        except Exception as exc:
            out.append({"phase": name, "fehler": str(exc)})
            continue
        known = s.reindex(s.index.union(r.index)).ffill().shift(1).reindex(r.index)   # state at the close before
        on = known.fillna(False).astype(bool)
        a, b = r[on], bench.reindex(r.index)[on]
        out.append({"phase": name, "beschreibung": regimes.PHASES[name][0], "tage": int(on.sum()), "anteil": float(on.mean()),
                    "strategie": float(a.mean() * DAYS) if len(a) else np.nan,
                    "sharpe": metrics.sharpe(a) if len(a) > 20 else np.nan,
                    "markt": float(b.mean() * DAYS) if len(b) else np.nan})
    return out


def regime_pnl(spec_path) -> tuple[str, pd.DataFrame]:
    spec = backtest.load_spec(spec_path)
    p = backtest.prepare(spec)
    k = backtest._best(p["matrix"], p["is_mask"])
    r = p["matrix"][k]
    rows = phase_pnl(r, p["bench"])
    lines = [f"# Gewinn und Verlust nach Marktphase: {spec.get('name', '')}", "",
             f"- **Markt:** {p['label']} · **Parameter:** {json.dumps(p['grid'][k], ensure_ascii=False)} (gewählt vor {p['holdout']:%d.%m.%Y})",
             f"- **Zeitraum:** {r.index[0]:%d.%m.%Y} – {r.index[-1]:%d.%m.%Y}", "",
             "| Phase | Bedeutung | Tage | Anteil | Strategie p. a. | Sharpe | Kaufen-und-Halten p. a. |", "|---|---|---:|---:|---:|---:|---:|"]
    for x in rows:
        if "fehler" in x:
            lines.append(f"| {x['phase']} | keine Daten: {x['fehler']} | | | | | |")
            continue
        few = " ⚠️" if x["tage"] < 250 else ""
        lines.append(f"| {x['phase']} | {x['beschreibung']} | {x['tage']}{few} | {_pct(x['anteil'], 0, False)} | {_pct(x['strategie'], 1)} | "
                     f"{num(x['sharpe'], 2)} | {_pct(x['markt'], 1)} |")
    lines += ["", "## Hinweise", "",
              "- Phase = Stand am Schluss des Vortags (bekannt, als die Position gehalten wurde).",
              "- Ganzer Zeitraum inkl. Entwicklungsdaten; Tage mit ⚠️ (unter einem Jahr) sind kaum aussagekräftig.",
              "- Mehrere Phasen gleichzeitig möglich; die Zeilen überschneiden sich. Rendite p. a. = Ø Tagesrendite × 252."]
    detail = pd.DataFrame([x for x in rows if "fehler" not in x])
    return "\n".join(lines) + "\n", detail


# ---------------------------------------------------------------- own trades: what did the market do before each entry?
def read_trades(text: str) -> pd.DataFrame:
    from io import StringIO

    df = pd.read_csv(StringIO(text), sep=None, engine="python")
    df.columns = [c.strip().lower() for c in df.columns]
    col = next((c for c in df.columns if c in ("datum", "date", "einstieg", "entry", "zeit", "time")), None)
    if col is None:
        raise SystemExit("Die CSV braucht eine Spalte 'datum' (Einstiegstag)")
    df["datum"] = pd.to_datetime(df[col], errors="coerce", dayfirst=not re.match(r"^\d{4}", str(df[col].iloc[0]) if len(df) else ""))
    df = df.dropna(subset=["datum"])
    if df.empty:
        raise SystemExit("Die Datei enthält noch keine Trades. Eine Zeile je Einstieg eintragen (datum,symbol,richtung, z. B. "
                         "2024-03-15,dax,long) oder die eigene CSV unter Projekte → Dateien hochladen.")
    df["richtung"] = df.get("richtung", df.get("side", "long"))
    df["richtung"] = df["richtung"].fillna("long").astype(str).str.lower().map(lambda s: -1 if s.startswith(("s", "-", "sell", "verk")) else 1)
    return df


def before_entries(c: pd.Series, entries: pd.Series, lookbacks=(1, 5, 20), ahead=(1, 5, 20)) -> pd.DataFrame:
    """Return of the market over the days before each entry day (up to the previous close) and after it (from the
    previous close), compared with all days."""
    idx = c.index
    rows = []
    for d in entries:
        i = idx.searchsorted(pd.Timestamp(d).normalize())          # first trading day on/after the entry date
        if i <= max(lookbacks) or i >= len(idx):
            continue
        row = {"datum": idx[i]}
        for n in lookbacks:
            row[f"vorher_{n}T"] = c.iloc[i - 1] / c.iloc[i - 1 - n] - 1
        for n in ahead:
            row[f"danach_{n}T"] = c.iloc[min(i - 1 + n, len(c) - 1)] / c.iloc[i - 1] - 1 if i - 1 + n < len(c) else np.nan
        rows.append(row)
    return pd.DataFrame(rows)


def trades(text: str, default_market: str = "sp500") -> tuple[str, pd.DataFrame]:
    df = read_trades(text)
    if "symbol" not in df:
        df["symbol"] = default_market
    df["symbol"] = df["symbol"].fillna(default_market).astype(str)
    lines = ["# Was machte der Markt vor deinen Einstiegen?", "",
             f"- **Trades:** {len(df)} · {df['datum'].min():%d.%m.%Y} – {df['datum'].max():%d.%m.%Y}", ""]
    all_rows = []
    for sym, g in df.groupby("symbol"):
        symbol, label = prices.resolve(sym)
        try:
            c = prices.closes(symbol)
        except Exception as exc:
            lines.append(f"- {label}: keine Kurse ({exc})")
            continue
        got = before_entries(c, g["datum"])
        if got.empty:
            lines.append(f"- {label}: keine Einstiege im Kursverlauf")
            continue
        got["symbol"] = label
        got["richtung"] = g["richtung"].to_numpy()[:len(got)]
        base = before_entries(c, c.index[30:-21:5])                  # every 5th day = "a normal day"
        lines += [f"## {label} ({len(got)} Einstiege)", "",
                  "| | Deine Einstiege Ø | Anteil ↑ | Normale Tage Ø | Unterschied p |", "|---|---:|---:|---:|---:|"]
        for col in [c_ for c_ in got.columns if c_.startswith(("vorher", "danach"))]:
            a, b = got[col].dropna(), base[col].dropna()
            p = stats.ttest_ind(a, b, equal_var=False).pvalue if len(a) >= 5 else np.nan
            lines.append(f"| {col.replace('_', ' ')} | {_pct(a.mean())} | {_pct((a > 0).mean(), 0, False)} | {_pct(b.mean())} | {num(p, 3)} |")
        lines.append("")
        try:
            phases = {n: regimes.known_before(regimes.state(n), pd.Series(pd.to_datetime(got["datum"]).dt.tz_localize("America/New_York")))
                      for n in ("vix_hoch", "vix_niedrig", "trend_auf", "trend_ab")}
            lines.append("Marktphase beim Einstieg: " + " · ".join(f"{n} {float(np.mean(v)):.0%}" for n, v in phases.items()))
            lines.append("")
        except Exception:
            pass
        all_rows.append(got)
    lines += ["## Hinweise", "",
              "- „vorher“ = Veränderung bis zum Schluss vor dem Einstiegstag; „danach“ = ab diesem Schluss. Tagesdaten: "
              "was innerhalb des Einstiegstags passierte (Orderflow, Minuten), sehen Tageskerzen nicht.",
              "- „Normale Tage“ = jeder 5. Handelstag der ganzen Historie. p < 0,05 heißt: deine Einstiege folgen einem anderen Muster.",
              "- Richtung (long/short) ist in der Tabelle nicht eingerechnet; die Spalte steht in der CSV."]
    return "\n".join(lines) + "\n", (pd.concat(all_rows) if all_rows else pd.DataFrame())


# ---------------------------------------------------------------- rolling walk-forward
def rolling_walk_forward(matrix: pd.DataFrame, is_months: int, oos_months: int, step_months: int) -> tuple[pd.Series, list[dict]]:
    """Choose the best variant on the last is_months, trade it for the next oos_months, move on by step_months.
    Overlapping test windows (step < oos) are cut so that every day is traded once."""
    start = matrix.index[0] + pd.DateOffset(months=is_months)
    pieces, rows, cursor = [], [], start
    while cursor < matrix.index[-1]:
        train = (matrix.index >= cursor - pd.DateOffset(months=is_months)) & (matrix.index < cursor)
        test_end = min(cursor + pd.DateOffset(months=step_months), cursor + pd.DateOffset(months=oos_months))
        test = (matrix.index >= cursor) & (matrix.index < test_end)
        if train.sum() > 60 and test.sum() > 0:
            k = backtest._best(matrix, pd.Series(train, index=matrix.index))
            r_test = matrix.loc[test, k]
            rows.append({"ab": cursor, "variante": k, "sharpe_entwicklung": metrics.sharpe(matrix.loc[train, k]),
                         "sharpe_test": metrics.sharpe(r_test) if len(r_test) > 20 else np.nan, "rendite_test": float(metrics.equity(r_test).iloc[-1] - 1)})
            pieces.append(r_test)
        cursor = cursor + pd.DateOffset(months=step_months)
    return (pd.concat(pieces) if pieces else pd.Series(dtype=float)), rows


def walk_forward_report(spec_path, is_months: int = 24, oos_months: int = 6, step_months: int = 3) -> tuple[str, pd.DataFrame]:
    spec = backtest.load_spec(spec_path)
    p = backtest.prepare(spec)
    wf, rows = rolling_walk_forward(p["matrix"], is_months, oos_months, step_months)
    if len(wf) < 250:
        raise SystemExit("Zu wenig Daten für diesen Walk-Forward")
    m, bh = metrics.summary(wf), metrics.summary(p["bench"].reindex(wf.index))
    is_s = np.array([r["sharpe_entwicklung"] for r in rows], float)
    oos_s = np.array([r["sharpe_test"] for r in rows], float)
    ok = ~np.isnan(is_s) & ~np.isnan(oos_s)
    decay = float(np.mean(oos_s[ok]) / np.mean(is_s[ok]) - 1) if ok.any() and np.mean(is_s[ok]) > 0 else np.nan
    corr = float(np.corrcoef(is_s[ok], oos_s[ok])[0, 1]) if ok.sum() > 3 else np.nan
    lines = [f"# Walk-Forward: {spec.get('name', '')}", "",
             f"- **Markt:** {p['label']} · **Varianten:** {len(p['grid'])} · **Kosten:** {num(p['cost'], 1)} Bp",
             f"- **Schema:** {is_months} Monate Entwicklung → {oos_months} Monate Test, alle {step_months} Monate neu gewählt ({len(rows)} Fenster)", "",
             "| | Zeitraum | Rendite p. a. | Sharpe | Max Drawdown |", "|---|---|---:|---:|---:|",
             f"| Walk-Forward (nur Test-Fenster aneinander) | {m['start']:%Y}–{m['end']:%Y} | {_pct(m['cagr'], 1)} | {num(m['sharpe'], 2)} | {_pct(m['mdd'], 1)} |",
             f"| Kaufen-und-Halten gleiche Tage | | {_pct(bh['cagr'], 1)} | {num(bh['sharpe'], 2)} | {_pct(bh['mdd'], 1)} |", "",
             f"- **Sharpe-Verfall Entwicklung → Test:** Ø {num(np.nanmean(is_s), 2)} → Ø {num(np.nanmean(oos_s), 2)}"
             + (f" ({num(decay * 100, 0, True, ' %')})" if not np.isnan(decay) else ""),
             f"- **Hängt der Test-Sharpe am Entwicklungs-Sharpe?** Korrelation {num(corr, 2)} (nahe 0 oder negativ: die Auswahl hilft nicht)",
             f"- **Variantenwechsel:** {sum(1 for a, b in zip(rows, rows[1:]) if a['variante'] != b['variante'])} von {max(len(rows) - 1, 0)} Fenstern", "",
             "## Fenster", "", "| ab | Variante | Sharpe Entwicklung | Sharpe Test | Rendite Test |", "|---|---|---:|---:|---:|"]
    lines += [f"| {r['ab']:%m/%Y} | {json.dumps(p['grid'][r['variante']], ensure_ascii=False)} | {num(r['sharpe_entwicklung'], 2)} | "
              f"{num(r['sharpe_test'], 2)} | {_pct(r['rendite_test'], 1)} |" for r in rows]
    lines += ["", "Sharpe je Testfenster bei kurzen Fenstern stark schwankend; aussagekräftig ist vor allem die Gesamtzeile."]
    chart = pd.DataFrame({"Walk-Forward": metrics.equity(wf), "Kaufen-und-Halten": metrics.equity(p["bench"].reindex(wf.index).fillna(0))})
    return "\n".join(lines) + "\n", chart


# ---------------------------------------------------------------- /review: the mistakes that most often invalidate research
def review_spec(spec: dict) -> list[tuple[str, str]]:
    """Static checks of a strategy or chain file: (status ✅/⚠️/❌, text)."""
    out = []
    if "glieder" in spec:                                            # chain
        links = spec.get("glieder", [])
        out.append(("✅" if len(links) >= 5 else "⚠️", f"{len(links)} Kettenglieder" + ("" if len(links) >= 5 else " – Ketten über mehrere Ebenen brauchen meist mehr")))
        no_why = [g.get("id", "?") for g in links if not str(g.get("warum", "")).strip()]
        out.append(("❌" if no_why else "✅", "Begründung fehlt bei: " + ", ".join(no_why) if no_why else "Jedes Glied hat eine Begründung"))
        no_dir = [g.get("id", "?") for g in links if g.get("erwartung") not in ("+", "-")]
        out.append(("⚠️" if no_dir else "✅", "Ohne erwartete Richtung (nicht widerlegbar): " + ", ".join(no_dir) if no_dir else "Jedes Glied hat eine erwartete Richtung"))
        out.append(("✅" if spec.get("von") or spec.get("bis") else "⚠️", "Zeitraum eingegrenzt" if spec.get("von") or spec.get("bis") else
                    "Kein Teilzeitraum – Ergebnis zusätzlich für zwei Hälften prüfen (Regimewechsel)"))
        return out
    grid = backtest.grid_of(spec)
    out.append(("✅" if spec.get("holdout_ab") else "❌", f"Testzeitraum ab {spec['holdout_ab']}" if spec.get("holdout_ab") else
                "Kein holdout_ab: Parameter würden auf denselben Daten gewählt und bewertet"))
    if spec.get("holdout_ab"):
        years = (pd.Timestamp.now() - pd.Timestamp(spec["holdout_ab"])).days / 365.25
        out.append(("✅" if years >= 3 else "⚠️", f"Testzeitraum {years:.1f} Jahre" + ("" if years >= 3 else " – unter 3 Jahren ist ein Sharpe kaum zu unterscheiden von Glück")))
    cost = float(spec.get("kosten_bp", 5))
    out.append(("❌" if cost <= 0 else "⚠️" if cost < 2 else "✅", f"Kosten {num(cost, 1)} Bp je Wechsel" + (" – ohne Kosten ist jeder Backtest geschönt" if cost <= 0 else " – sehr niedrig angesetzt" if cost < 2 else "")))
    out.append(("✅" if len(grid) <= 20 else "⚠️", f"{len(grid)} Varianten im Gitter" + ("" if len(grid) <= 20 else " – viele Varianten: Deflated Sharpe beachten")))
    out.append(("✅" if str(spec.get("warum", "")).strip() else "⚠️", "Ökonomische Begründung vorhanden" if str(spec.get("warum", "")).strip() else
                "Keine Begründung ('warum'): ohne Grund ist ein Muster eher Zufall"))
    symbol = prices.resolve(spec.get("markt", ""))[0]
    if symbol.endswith("=F"):
        out.append(("⚠️", "Future ohne Roll-Bereinigung: Rolltage erzeugen falsche Sprünge – besser Index/ETF"))
    elif prices.default_bench(symbol):
        out.append(("⚠️", "Einzelwert/ETF von Yahoo: delistete Firmen fehlen (Survivorship) – Ergebnis nicht auf Aktienauswahl übertragen"))
    if spec.get("short"):
        out.append(("⚠️", "Short-Seite ohne Leihkosten gerechnet"))
    return out


def review(spec_path, run_test: bool = True) -> str:
    spec = backtest.load_spec(spec_path)
    checks = review_spec(spec)
    if run_test and "glieder" not in spec:
        p = backtest.prepare(spec)
        k = backtest._best(p["matrix"], p["is_mask"])
        r_is, r_oos = p["matrix"].loc[p["is_mask"], k], p["matrix"].loc[~p["is_mask"], k]
        held = p["held"][k]
        trades_n = int((held.diff().abs() > 0).sum())
        checks.append(("✅" if trades_n >= 30 else "⚠️", f"{trades_n} Positionswechsel" + ("" if trades_n >= 30 else " – wenige Trades, Ergebnis hängt an Einzelfällen")))
        s_is, s_oos = metrics.sharpe(r_is), metrics.sharpe(r_oos) if len(r_oos) > 20 else np.nan
        if not np.isnan(s_oos):
            drop = s_oos < 0.5 * s_is if s_is > 0 else s_oos < 0
            checks.append(("⚠️" if drop else "✅", f"Sharpe Entwicklung {num(s_is, 2)} → Test {num(s_oos, 2)}" + (" – starker Verfall, Hinweis auf Überanpassung" if drop else "")))
        sharpes = [metrics.sharpe(p["matrix"].loc[p["is_mask"], j]) for j in p["matrix"].columns]
        best = max((s for s in sharpes if not np.isnan(s)), default=np.nan)
        median = float(np.nanmedian(sharpes)) if sharpes else np.nan
        if len(sharpes) > 2 and not np.isnan(best):
            lonely = best > 0 and median < 0.5 * best
            checks.append(("⚠️" if lonely else "✅", f"Beste Variante Sharpe {num(best, 2)}, Median aller {num(median, 2)}" +
                           (" – nur die beste funktioniert, die Nachbarn nicht (Parameter-Insel)" if lonely else " – Nachbarvarianten ähnlich (robust)")))
        n_years = (p["matrix"].index[-1] - p["matrix"].index[0]).days / 365.25
        checks.append(("✅" if n_years >= 10 else "⚠️", f"{n_years:.0f} Jahre Daten" + ("" if n_years >= 10 else " – wenige Jahre, kaum verschiedene Marktphasen")))
    bad, warn = sum(1 for s, _ in checks if s == "❌"), sum(1 for s, _ in checks if s == "⚠️")
    head = "❌ grundlegende Fehler" if bad else "⚠️ prüfen" if warn else "✅ keine typischen Fehler gefunden"
    return "\n".join([f"# Review: {spec.get('name', Path(str(spec_path)).name)}", "", f"## Ergebnis: {head}", ""] +
                     [f"- {s} {t}" for s, t in checks] +
                     ["", "Geprüft: Testzeitraum, Kosten, Zahl der Varianten, Begründung, Datenfallen (Futures-Roll, Survivorship), "
                      "Zahl der Trades, Verfall Entwicklung → Test, Parameter-Inseln, Länge der Historie. Look-ahead ist in den "
                      "eingebauten Regeln ausgeschlossen (Signal bis t, Ertrag ab t+1); eigene Skripte prüft das nicht."]) + "\n"


# ---------------------------------------------------------------- /goal: search a grid until a target is met
GOAL = re.compile(r"^(sharpe|cagr|mdd|calmar|sortino)\s*(>=|<=|>|<)\s*(-?[\d.,]+)%?$")
OPS = {">=": np.greater_equal, "<=": np.less_equal, ">": np.greater, "<": np.less}


def parse_goal(text: str) -> tuple[str, str, float]:
    m = GOAL.match(text.replace(" ", "").lower())
    if not m:
        raise SystemExit("Ziel z. B. sharpe>=0.8, cagr>5%, mdd>-20% (Kennzahlen: sharpe, cagr, mdd, calmar, sortino)")
    value = float(m.group(3).replace(",", "."))
    if m.group(1) in ("cagr", "mdd") and abs(value) > 1:
        value /= 100
    return m.group(1), m.group(2), value


def goal_step(state: dict, spec: dict, batch: int = 3) -> dict:
    """Evaluate the next variants on the DEVELOPMENT data only.  When one meets the target, test it once on the holdout."""
    metric, op, value = parse_goal(state["ziel"])
    p = backtest.prepare(spec)
    grid = p["grid"]
    todo = [k for k in range(len(grid)) if k not in state["geprueft"]][:batch]
    for k in todo:
        m = metrics.summary(p["matrix"].loc[p["is_mask"], k])
        v = float(m[metric])
        state["geprueft"].append(k)
        state["verlauf"].append({"variante": grid[k], metric: v})
        if not np.isnan(v) and OPS[op](v, value):
            r_oos = p["matrix"].loc[~p["is_mask"], k]
            mo = metrics.summary(r_oos) if len(r_oos) > 20 else None
            state |= {"status": "erreicht", "treffer": grid[k], "wert": v,
                      "test": {metric: float(mo[metric]), "sharpe": float(mo["sharpe"])} if mo else None}
            break
    else:
        if len(state["geprueft"]) >= len(grid):
            state["status"] = "nicht erreicht"
    backtest.log_trials(spec, [grid[k] for k in todo])
    state["versuche"] = len(state["geprueft"])
    return state


def goal_text(state: dict) -> str:
    lines = [f"# Ziel: {state['ziel']} – {state['datei']}", "", f"**Status:** {state['status']} · {state['versuche']} Varianten geprüft "
             "(jede zählt im Versuchsprotokoll)", ""]
    for h in state["verlauf"][-10:]:
        lines.append("- " + ", ".join(f"{k}: {num(v, 3) if isinstance(v, float) else json.dumps(v, ensure_ascii=False)}" for k, v in h.items()))
    if state["status"] == "erreicht":
        t = state.get("test")
        lines += ["", f"**Treffer auf den Entwicklungsdaten:** {json.dumps(state['treffer'], ensure_ascii=False)}",
                  "**Einmaliger Test danach:** " + (", ".join(f"{k} {num(v, 3)}" for k, v in t.items()) if t else "zu wenig Testdaten"),
                  "", "Ein Ziel nach mehreren Versuchen zu erreichen ist kein Beleg – maßgeblich ist der Test und der Deflated Sharpe "
                  "im vollständigen Backtest (`/backtest`)."]
    elif state["status"] == "läuft":
        lines += ["", "Weiter mit `/goal weiter`, anhalten mit `/goal pause`, beenden mit `/goal stopp`."]
    return "\n".join(lines) + "\n"
