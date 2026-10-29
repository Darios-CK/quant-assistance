"""Backtests of simple daily rules – built so that they are hard to fool yourself with.

Strategy file (JSON, strategies/*.json):
{
  "name": "Trendfolge DAX", "markt": "dax", "regel": "trend",
  "parameter": {"schnell": [20, 50, 100], "langsam": [150, 200, 300]},
  "short": false, "kosten_bp": 5, "holdout_ab": "2019-01-01", "warum": "Trends halten an, weil …"
}
Rules (few parameters on purpose):
  trend     long while the fast moving average is above the slow one              schnell, langsam
  momentum  long while the return over 'lookback' days (skipping the last 'skip') is positive   lookback, skip
  umkehr    long for 'halten' days after a fall of 'schwelle' standard deviations over 'tage' days   tage, schwelle, halten
  ereignis  after an event (ezb, fed, kurs:…, earnings:…) hold the market in the direction of the
            surprise (richtung = mit | gegen) for 'halten' days, only surprises above 'schwelle' σ      halten, schwelle

No look-ahead: a signal uses closes up to day t and earns from t+1; an event counts from the close of its
reaction day; thresholds and volatility only use the past.  Costs are charged on every change of position.
Parameters are chosen on the data before 'holdout_ab' only; the holdout is the test.  Every variant ever tested
for a market and rule is logged (data/trials.jsonl) and counted by the Deflated Sharpe Ratio.
"""

from __future__ import annotations

import hashlib
import itertools
import json
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from qa import metrics, quality, triggers
from qa.cache import ROOT
from qa.report import num
from qa.sources import prices
from qa.study import reaction_start

TRIALS = ROOT / "data" / "trials.jsonl"
MIN_TRAIN_YEARS = 5


# ---------------------------------------------------------------- rules: return the position HELD on each day
def _trend(c: pd.Series, p: dict, short: bool) -> pd.Series:
    fast, slow = c.rolling(int(p["schnell"])).mean(), c.rolling(int(p["langsam"])).mean()
    sig = pd.Series(np.where(fast > slow, 1.0, -1.0 if short else 0.0), index=c.index)
    sig[slow.isna()] = 0.0
    return sig.shift(1).fillna(0.0)


def _momentum(c: pd.Series, p: dict, short: bool) -> pd.Series:
    past = c.shift(int(p.get("skip", 0))) / c.shift(int(p["lookback"])) - 1
    sig = pd.Series(np.where(past > 0, 1.0, -1.0 if short else 0.0), index=c.index)
    sig[past.isna()] = 0.0
    return sig.shift(1).fillna(0.0)


def _reversal(c: pd.Series, p: dict, short: bool) -> pd.Series:
    days, hold = int(p["tage"]), int(p["halten"])
    r = c.pct_change()
    vol = r.rolling(250, min_periods=120).std().shift(1)          # volatility of the past year only
    z = (c / c.shift(days) - 1) / (vol * np.sqrt(days))
    held = np.zeros(len(c))
    for i in np.flatnonzero((z <= -float(p["schwelle"])).to_numpy()):
        held[i + 1:i + 1 + hold] = 1.0
    if short:
        for i in np.flatnonzero((z >= float(p["schwelle"])).to_numpy()):
            held[i + 1:i + 1 + hold] = np.where(held[i + 1:i + 1 + hold] == 0, -1.0, held[i + 1:i + 1 + hold])
    return pd.Series(held, index=c.index)


def _event(c: pd.Series, p: dict, short: bool, events: pd.DataFrame, market: str, direction: str) -> pd.Series:
    hold, threshold = int(p["halten"]), float(p.get("schwelle", 0))
    sign = 1.0 if direction == "mit" else -1.0
    held = np.zeros(len(c))
    past = []
    for ev in events.sort_values("ts").itertuples(index=False):
        sd = np.std(past, ddof=1) if len(past) >= 10 else np.nan     # size of a typical surprise, from earlier events only
        past.append(ev.surprise)
        if np.isnan(sd) or abs(ev.surprise) < threshold * sd or ev.surprise == 0:
            continue
        i = reaction_start(c.index, ev.ts, market)
        if i is None:
            continue
        side = sign * np.sign(ev.surprise)
        if side < 0 and not short:
            continue
        held[i + 1:i + 1 + hold] = side                                 # enter at the close of the reaction day
    return pd.Series(held, index=c.index)


def positions(c: pd.Series, spec: dict, params: dict, ctx: dict) -> pd.Series:
    rule, short = spec["regel"], bool(spec.get("short", False))
    if rule == "trend":
        return _trend(c, params, short)
    if rule == "momentum":
        return _momentum(c, params, short)
    if rule == "umkehr":
        return _reversal(c, params, short)
    if rule == "ereignis":
        return _event(c, params, short, ctx["events"], ctx["market"], spec.get("richtung", "mit"))
    raise SystemExit(f"Unbekannte Regel '{rule}'. Möglich: trend, momentum, umkehr, ereignis")


def strategy_returns(c: pd.Series, held: pd.Series, cost_bp: float) -> pd.Series:
    r = c.pct_change().fillna(0.0)
    return held * r - held.diff().abs().fillna(held.abs()) * cost_bp / 10000


# ---------------------------------------------------------------- trials log
def _variant_key(spec: dict, params: dict) -> str:
    return json.dumps({"markt": spec["markt"], "regel": spec["regel"], "short": bool(spec.get("short")),
                       "richtung": spec.get("richtung"), "quelle": spec.get("ausloeser", {}).get("quelle"),
                       "p": params}, sort_keys=True)


def log_trials(spec: dict, grid: list[dict], path: Path = TRIALS) -> int:
    """Record the variants and return how many distinct variants were ever tested for this market and rule."""
    family = f"{spec['markt']}|{spec['regel']}"
    keys = {hashlib.sha1(_variant_key(spec, g).encode()).hexdigest() for g in grid}
    seen = set()
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            if row["family"] == family:
                seen.add(row["key"])
    new = keys - seen
    if new:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            for k in sorted(new):
                f.write(json.dumps({"family": family, "key": k, "ts": datetime.now().isoformat(timespec="seconds")}) + "\n")
    return len(seen | keys)


# ---------------------------------------------------------------- run
def grid_of(spec: dict) -> list[dict]:
    params = spec.get("parameter", {})
    names = list(params)
    values = [v if isinstance(v, list) else [v] for v in params.values()]
    return [dict(zip(names, combo)) for combo in itertools.product(*values)] or [{}]


def _best(matrix: pd.DataFrame, mask: pd.Series) -> int:
    s = [metrics.sharpe(matrix.loc[mask, j]) for j in matrix.columns]
    return int(np.nanargmax(s)) if not all(np.isnan(s)) else 0


def walk_forward(matrix: pd.DataFrame, start_year: int) -> tuple[pd.Series, list[tuple[int, int]]]:
    """Each year: pick the variant with the best Sharpe on all years before it, trade it that year."""
    years = sorted(set(matrix.index.year))
    out, picks = [], []
    for y in years:
        if y < start_year + MIN_TRAIN_YEARS:
            continue
        k = _best(matrix, pd.Series(matrix.index.year < y, index=matrix.index))
        out.append(matrix.loc[matrix.index.year == y, k])
        picks.append((y, k))
    return (pd.concat(out) if out else pd.Series(dtype=float)), picks


def run(path: Path) -> tuple[str, pd.DataFrame]:
    spec = json.loads(Path(path).read_text(encoding="utf-8"))
    symbol, label = prices.resolve(spec["markt"])
    if prices.unit(symbol) != "pct":
        raise SystemExit(f"{label} ist eine Zinsreihe, kein handelbarer Kurs – bitte ein Instrument mit Preis wählen (z. B. ein Future oder ETF).")
    c = prices.closes(symbol)
    if spec.get("von"):
        c = c[c.index >= pd.Timestamp(str(spec["von"]))]
    ctx = {"market": prices.market(symbol)}
    if spec["regel"] == "ereignis":
        trig = spec["ausloeser"]
        ctx["events"] = triggers.load(trig["quelle"], **{k: v for k, v in trig.items() if k != "quelle"}).df
    grid = grid_of(spec)
    cost = float(spec.get("kosten_bp", 5))
    held = {k: positions(c, spec, g, ctx) for k, g in enumerate(grid)}
    matrix = pd.DataFrame({k: strategy_returns(c, h, cost) for k, h in held.items()}).iloc[1:]
    bench = c.pct_change().iloc[1:]

    holdout = pd.Timestamp(spec.get("holdout_ab") or matrix.index[int(len(matrix) * 0.7)])
    is_mask = pd.Series(matrix.index < holdout, index=matrix.index)
    k = _best(matrix, is_mask)
    chosen = grid[k]
    r_is, r_oos = matrix.loc[is_mask, k], matrix.loc[~is_mask, k]
    trial_sharpes = [metrics.sharpe(matrix.loc[is_mask, j], annual=False) for j in matrix.columns]
    n_trials = log_trials(spec, grid)
    m_is = metrics.summary(r_is, held[k], bench) | {"dsr": metrics.dsr(r_is.to_numpy(), trial_sharpes, n_trials)}
    m_oos = metrics.summary(r_oos, held[k], bench) if len(r_oos) > 20 else None
    m_bh = metrics.summary(bench[~is_mask]) if len(r_oos) > 20 else None
    p_bo = metrics.pbo(matrix.loc[is_mask].to_numpy())
    wf, picks = walk_forward(matrix, int(matrix.index[0].year))
    stress = {"strategie": metrics.summary(matrix[k])["stress"], "markt": metrics.summary(bench)["stress"]}
    m_wf = metrics.summary(wf) if len(wf) > 250 else None
    share_pos = float(np.mean([s > 0 for s in trial_sharpes if not np.isnan(s)])) if trial_sharpes else np.nan
    notes = quality.check(c, "pct", label)

    text = render(spec, label, chosen, len(grid), n_trials, share_pos, holdout, m_is, m_oos, m_bh, p_bo, m_wf, picks, grid, cost, notes, stress)
    detail = pd.DataFrame({"rendite_strategie": matrix[k], "position": held[k].reindex(matrix.index), "rendite_markt": bench})
    return text, detail.reset_index(names="datum")


# ---------------------------------------------------------------- report
def _pct(v, d=1):
    return num(v * 100, d, True, " %") if v is not None and not (isinstance(v, float) and np.isnan(v)) else "–"


def _row(name: str, m: dict | None) -> str:
    if m is None:
        return f"| {name} | – | – | – | – | – | – | – | – |"
    return (f"| {name} | {m['start']:%Y}–{m['end']:%Y} | {_pct(m['cagr'])} | {num(m['sharpe'], 2)} | {num(m['sortino'], 2)} | "
            f"{_pct(m['mdd'])} | {num(m['calmar'], 2)} | {_pct(m['vol'])} | {_pct(m.get('exposure'), 0) if 'exposure' in m else '–'} |")


def verdict(m_oos: dict | None, m_bh: dict | None, dsr: float, p_bo: float) -> str:
    if m_oos is None:
        return "⬜ zu wenig Daten nach dem Entwicklungszeitraum"
    checks = [m_oos["sharpe"] > 0, not np.isnan(dsr) and dsr > 0.95, np.isnan(p_bo) or p_bo < 0.5]
    beats = m_bh is not None and m_oos["sharpe"] > m_bh["sharpe"]
    if all(checks):
        return "✅ hält der Prüfung stand" + (" und schlägt Kaufen-und-Halten (Sharpe)" if beats else ", schlägt Kaufen-und-Halten aber nicht")
    failed = [t for t, ok in zip(["Sharpe im Testzeitraum ≤ 0", "Deflated Sharpe ≤ 0,95 (Glück nicht auszuschließen)",
                                  "PBO ≥ 0,5 (Auswahl nicht besser als Zufall)"], checks) if not ok]
    return "❌ hält nicht stand: " + "; ".join(failed)


def render(spec, label, chosen, n_grid, n_trials, share_pos, holdout, m_is, m_oos, m_bh, p_bo, m_wf, picks, grid, cost, notes, stress) -> str:
    lines = [f"# Backtest: {spec.get('name', '')}", ""]
    if spec.get("warum"):
        lines += [f"> Begründung: {spec['warum']}", ""]
    lines += [
        f"- **Markt:** {label} · **Regel:** {spec['regel']}{' (auch short)' if spec.get('short') else ' (nur long)'} · **Kosten:** {num(cost, 1)} Bp je Positionswechsel",
        f"- **Gewählte Parameter:** {json.dumps(chosen, ensure_ascii=False)} – ausgewählt nur auf Daten vor {holdout:%d.%m.%Y}",
        f"- **Getestete Varianten:** {n_grid} in diesem Lauf, {n_trials} insgesamt für {spec['markt']}/{spec['regel']} (Versuchsprotokoll) · "
        f"{_pct(share_pos, 0).replace('+', '')} der Varianten mit positivem Sharpe vor dem Testzeitraum",
        f"- **Erstellt:** {datetime.now():%d.%m.%Y %H:%M}",
        "",
        f"## Einordnung: {verdict(m_oos, m_bh, m_is['dsr'], p_bo)}",
        "",
        *([f"- **Sharpe Entwicklung → Test:** {num(m_is['sharpe'], 2)} → {num(m_oos['sharpe'], 2)}"
           + (f" ({num((m_oos['sharpe'] / m_is['sharpe'] - 1) * 100, 0, True, ' %')})" if m_is['sharpe'] and m_is['sharpe'] > 0 else "")
           + (f" · Kaufen-und-Halten im Test: {num(m_bh['sharpe'], 2)}" if m_bh else "")] if m_oos else []),
        f"- **Deflated Sharpe** (Entwicklungsdaten, {n_trials} Versuche berücksichtigt): {num(m_is['dsr'], 2)} – Wahrscheinlichkeit, dass der echte Sharpe über 0 liegt (Ziel > 0,95)",
        f"- **PBO** (Entwicklungsdaten, 8 Blöcke): {num(p_bo, 2)} – Anteil der Aufteilungen, in denen die beste Variante danach unter dem Median lag (Ziel < 0,5)",
        "",
        "## Ergebnisse nach Kosten",
        "",
        "| Zeitraum | Jahre | Rendite p. a. | Sharpe | Sortino | Max Drawdown | Calmar | Volatilität | Investiert |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
        _row("Entwicklung (Parameterwahl)", m_is),
        _row("**Test (nie zur Wahl genutzt)**", m_oos),
        _row("Kaufen-und-Halten im Test", m_bh),
        _row("Walk-Forward (jährlich neu gewählt)", m_wf),
        "",
    ]
    if m_oos:
        lines += [
            "## Risiko im Testzeitraum",
            "",
            f"Schiefe {num(m_oos['skew'], 2)} · Kurtosis (Überschuss) {num(m_oos['kurt'], 1)} · Trefferquote {_pct(m_oos['hit'], 0).replace('+', '')} · "
            f"Gewinn/Verlust-Verhältnis {num(m_oos['win_loss'], 2)} · VaR 95 % (1 Tag) {_pct(m_oos['var95'], 2)} · Expected Shortfall 95 % {_pct(m_oos['es95'], 2)} · "
            f"Turnover {num(m_oos.get('turnover', np.nan), 1)} Wechsel p. a. · Beta {num(m_oos.get('beta', np.nan), 2)} · Alpha p. a. {_pct(m_oos.get('alpha'))} · "
            f"Korrelation an den 10 % schlechtesten Markttagen {num(m_oos.get('corr_crisis', np.nan), 2)}",
            "",
        ]
    lines += ["## Stresstests (gewählte Parameter, Gesamtrendite in der Phase)", "",
              "| Phase | Strategie | Kaufen-und-Halten |", "|---|---:|---:|"]
    for name in metrics.STRESS:
        lines.append(f"| {name} | {_pct(stress['strategie'][name])} | {_pct(stress['markt'][name])} |")
    if picks:
        lines += ["", "## Walk-Forward: gewählte Variante je Jahr", "",
                  ", ".join(f"{y}: {json.dumps(grid[k], ensure_ascii=False)}" for y, k in picks)]
    lines += ["", "## Hinweise", ""] + [f"- {n}" for n in notes] + [
        "- Signal aus Schlusskursen bis Tag t, Ertrag ab Tag t+1; Ereignisse ab Schluss des Reaktionstags. Keine Zinsen auf Cash, keine Steuern, Slippage nur über die Kostenannahme.",
        "- Yahoo: Kurse bereinigt um Splits/Dividenden; Futures ohne Roll-Bereinigung; delistete Werte fehlen.",
        "- Stresstests nur, soweit die Strategie in der Phase Daten hat. Vergangene Ergebnisse sind keine Vorhersage und keine Empfehlung.",
    ]
    return "\n".join(lines) + "\n"
