"""Performance and risk figures of a daily return series (simple returns, fractions: 0.01 = 1 %).

Sharpe ratios are without a risk-free rate (cash earned nothing) unless the caller subtracts one.
The Deflated Sharpe Ratio (Bailey & López de Prado 2014) asks: given how many variants were tried, how likely is
it that the true Sharpe of the best one is above zero?  PBO (Bailey, Borwein, López de Prado, Zhu 2017) asks: how
often does the variant that looked best in one half of the data end up below the median in the other half?
"""

from __future__ import annotations

from itertools import combinations

import numpy as np
import pandas as pd
from scipy import stats as st

DAYS = 252
EULER = 0.5772156649
STRESS = {  # periods every strategy is shown in
    "Dotcom-Crash 2000–2002": ("2000-03-24", "2002-10-09"),
    "Finanzkrise 2007–2009": ("2007-10-09", "2009-03-09"),
    "Corona-Crash 2020": ("2020-02-19", "2020-03-23"),
    "Zinswende 2022": ("2022-01-03", "2022-12-30"),
}


def equity(r: pd.Series) -> pd.Series:
    return (1 + r.fillna(0)).cumprod()


def max_drawdown(r: pd.Series) -> float:
    eq = equity(r)
    return float((eq / eq.cummax() - 1).min())


def sharpe(r: pd.Series | np.ndarray, annual: bool = True) -> float:
    r = np.asarray(r, float)
    r = r[~np.isnan(r)]
    if len(r) < 2 or np.std(r, ddof=1) == 0:
        return np.nan
    s = np.mean(r) / np.std(r, ddof=1)
    return float(s * np.sqrt(DAYS)) if annual else float(s)


def sortino(r: pd.Series) -> float:
    r = r.dropna()
    down = np.sqrt(np.mean(np.minimum(r, 0) ** 2))
    return float(r.mean() / down * np.sqrt(DAYS)) if down > 0 else np.nan


def psr(r: np.ndarray, sr0: float = 0.0) -> float:
    """Probability that the true (per-period) Sharpe exceeds sr0, allowing for skew and fat tails."""
    r = np.asarray(r, float)
    r = r[~np.isnan(r)]
    if len(r) < 10 or np.std(r) == 0:
        return np.nan
    sr = np.mean(r) / np.std(r, ddof=1)
    g3, g4 = st.skew(r), st.kurtosis(r, fisher=False)
    denom = np.sqrt(max(1e-12, 1 - g3 * sr + (g4 - 1) / 4 * sr ** 2))
    return float(st.norm.cdf((sr - sr0) * np.sqrt(len(r) - 1) / denom))


def expected_max_sharpe(trial_sharpes: list[float], n_trials: int) -> float:
    """Sharpe (per period) the best of n_trials pure-noise variants would show by luck."""
    if n_trials <= 1:
        return 0.0
    v = np.var([s for s in trial_sharpes if not np.isnan(s)], ddof=1) if len(trial_sharpes) > 1 else 0.0
    z1, z2 = st.norm.ppf(1 - 1 / n_trials), st.norm.ppf(1 - 1 / (n_trials * np.e))
    return float(np.sqrt(max(v, 0.0)) * ((1 - EULER) * z1 + EULER * z2))


def dsr(r: np.ndarray, trial_sharpes: list[float], n_trials: int) -> float:
    return psr(r, expected_max_sharpe(trial_sharpes, n_trials))


def pbo(matrix: np.ndarray, blocks: int = 8) -> float:
    """matrix: days × variants of returns.  Share of block splits in which the in-sample winner ranks in the
    lower half out of sample.  Around 0.5 or more: the selection is no better than chance."""
    t, n = matrix.shape
    if n < 2 or t < blocks * 20:
        return np.nan
    parts = np.array_split(np.arange(t), blocks)
    below, total = 0, 0
    for train in combinations(range(blocks), blocks // 2):
        tr = np.concatenate([parts[i] for i in train])
        te = np.concatenate([parts[i] for i in range(blocks) if i not in train])
        best = int(np.nanargmax([sharpe(matrix[tr, j], False) for j in range(n)]))
        oos = np.array([sharpe(matrix[te, j], False) for j in range(n)])
        rank = (np.sum(oos < oos[best]) + 0.5 * (np.sum(oos == oos[best]) - 1)) / (n - 1)
        below += rank < 0.5
        total += 1
    return below / total


def summary(r: pd.Series, pos: pd.Series | None = None, bench: pd.Series | None = None) -> dict:
    """All figures of one return series; pos (positions) for exposure and turnover, bench for beta/alpha."""
    r = r.dropna()
    years = len(r) / DAYS
    eq = equity(r)
    cagr = float(eq.iloc[-1] ** (1 / years) - 1) if years > 0 and eq.iloc[-1] > 0 else np.nan
    mdd = max_drawdown(r)
    active = r[pos.reindex(r.index).fillna(0) != 0] if pos is not None else r
    wins, losses = active[active > 0], active[active < 0]
    out = {
        "start": r.index[0], "end": r.index[-1], "days": len(r),
        "cagr": cagr, "vol": float(r.std(ddof=1) * np.sqrt(DAYS)), "sharpe": sharpe(r), "sortino": sortino(r),
        "mdd": mdd, "calmar": cagr / abs(mdd) if mdd < 0 and not np.isnan(cagr) else np.nan,
        "skew": float(st.skew(r)), "kurt": float(st.kurtosis(r)),          # kurtosis in excess of the normal (0)
        "hit": float((active > 0).mean()) if len(active) else np.nan,
        "win_loss": float(wins.mean() / -losses.mean()) if len(wins) and len(losses) else np.nan,
        "var95": float(np.quantile(r, 0.05)), "es95": float(r[r <= np.quantile(r, 0.05)].mean()),
        "psr": psr(r.to_numpy()),
    }
    if pos is not None:
        p = pos.reindex(r.index).fillna(0)
        out |= {"exposure": float((p != 0).mean()), "turnover": float(p.diff().abs().sum() / years) if years else np.nan}
    if bench is not None:
        b = bench.reindex(r.index)
        ok = ~b.isna()
        if ok.sum() > 20 and b[ok].var() > 0:
            beta = float(np.cov(r[ok], b[ok])[0, 1] / b[ok].var(ddof=1))
            out |= {"beta": beta, "alpha": float((r[ok] - beta * b[ok]).mean() * DAYS),
                    "corr_crisis": _crisis_corr(r[ok], b[ok])}
    out["stress"] = {name: float(equity(r[a:b]).iloc[-1] - 1) if len(r[a:b]) else np.nan for name, (a, b) in STRESS.items()}
    return out


def _crisis_corr(r: pd.Series, b: pd.Series) -> float:
    """Correlation with the benchmark on its worst 10 % of days – diversification that vanishes in a crash shows here."""
    worst = b <= b.quantile(0.10)
    return float(np.corrcoef(r[worst], b[worst])[0, 1]) if worst.sum() > 10 else np.nan
