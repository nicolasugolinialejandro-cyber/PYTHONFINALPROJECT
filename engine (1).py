"""
engine.py — MacroTilt analytics core
-------------------------------------
Data + portfolio math for MacroTilt: a geopolitical-view-driven portfolio
allocator. No Streamlit imports here on purpose — this module is unit
testable and is reused by verify_calculations.py (the independent
verification script) without booting the UI.

Method summary (see README for the full writeup):
  1. Pull real daily prices for a fixed 6-asset macro universe.
  2. Compute the historical covariance matrix and reverse-optimize the
     "equilibrium" expected returns implied by the equal-weight portfolio
     (standard Black-Litterman starting point when no clean market-cap
     benchmark exists for the asset set).
  3. Let the user express geopolitical/macro views on a 0-10 conviction
     scale. Each view nudges one asset's expected return away from
     equilibrium, weighted by how confident the user is.
  4. Blend prior + views via the Black-Litterman posterior formula, then
     mean-variance optimize (max Sharpe) the posterior to get the final
     "Macro-Tilted" allocation.
  5. Compare against equal-weight (required baseline) and 100% SPY
     (the "boring" benchmark the whole product is pitched against).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import yfinance as yf
from scipy.optimize import minimize

# ---------------------------------------------------------------------------
# Universe & data provenance
# ---------------------------------------------------------------------------

TICKERS = ["SPY", "EEM", "TLT", "GLD", "XLE", "UUP"]

ASSET_LABELS = {
    "SPY": "US Equities (SPY)",
    "EEM": "Emerging Markets (EEM)",
    "TLT": "20+Y Treasuries (TLT)",
    "GLD": "Gold (GLD)",
    "XLE": "Energy Equities (XLE)",
    "UUP": "US Dollar Index (UUP)",
}

# ---------------------------------------------------------------------------
# Colour system (dark theme)
# ---------------------------------------------------------------------------
# Categorical hues occupy fixed palette slots 1-6, and CHART_ORDER below draws
# them in that same slot order. That pairing is the accessibility mechanism,
# not decoration: donut slices and grouped bars only ever place slot-adjacent
# hues next to each other, which is the pairlist the palette was validated on.
#
# Validated against the card surface #151a21 in dark mode:
#   lightness band PASS · chroma floor PASS · contrast >= 3:1 PASS
#   worst adjacent CVD dE 8.4 (yellow<->aqua, protan)
#   worst adjacent normal-vision dE 19.3 (magenta<->yellow)
#   ring wrap (green->blue) dE 29.9 normal / 27.3 deutan
#
# With six series, all-28-pairs separation is mathematically unreachable (a
# documented property of the palette, not a defect here), so every categorical
# chart also ships secondary encoding: direct labels on the donut, 2px surface
# gaps between fills, a legend, and a table view of the same numbers.
#
# DO NOT reorder these or hand-pick "nicer" hues without re-running
# scripts/validate_palette.js -- the ordering is load-bearing.

ASSET_COLORS = {
    "SPY": "#3987e5",   # slot 1  blue
    "XLE": "#d95926",   # slot 2  orange  -- reads naturally as energy/oil
    "EEM": "#199e70",   # slot 3  aqua
    "GLD": "#c98500",   # slot 4  yellow  -- reads naturally as gold
    "TLT": "#d55181",   # slot 5  magenta
    "UUP": "#008300",   # slot 6  green   -- reads naturally as dollar
}

# Draw order for every categorical chart. Matches palette slot order so
# neighbouring marks are always a validated adjacent pair.
CHART_ORDER = ["SPY", "XLE", "EEM", "GLD", "TLT", "UUP"]

BENCHMARK_COLOR = "#8b93a1"     # muted ink -- the "boring" 100%-SPY baseline
EQUAL_WEIGHT_COLOR = "#9085e9"  # slot 7 violet -- benchmark, never an asset

# Chrome. Dark-first surfaces; text steps chosen for >= 7:1 on the card.
COLOR_PAGE_BG = "#0a0e12"
COLOR_SURFACE = "#151a21"
COLOR_SURFACE_HI = "#1c232c"
COLOR_BORDER = "#252d38"
COLOR_TEXT = "#ffffff"
COLOR_TEXT_DIM = "#9aa4b2"
COLOR_TEXT_MUTED = "#6b7684"
COLOR_GRID = "#252d38"

# Status colours are reserved and never themed -- they never stand in for a
# series hue. Always paired with an arrow glyph so colour is not the only cue.
COLOR_UP = "#0ca30c"
COLOR_DOWN = "#d03b3b"

# We deliberately used an EQUITY energy ETF (XLE) instead of a futures-based
# commodity ETF (USO/BNO) for oil/energy exposure. Futures-based commodity
# ETFs suffer contango/roll-yield decay that distorts long-horizon
# buy-and-hold returns -- a real, disclosed modeling choice, not an
# oversight.

# UUP (US Dollar Index Bullish Fund) launched 2007-02-20 -- confirmed via
# web search (stockanalysis.com), not assumed -- and is the youngest fund
# in the universe, so it sets the floor on shared history. Starting a few
# days later avoids thin early-trading noise.
DATA_START = "2007-03-01"

RISK_FREE_RATE = 0.04  # disclosed assumption: approx. current short-term T-bill yield

STRESS_PERIODS = {
    "2008 Global Financial Crisis": ("2008-09-01", "2009-03-09"),
    "COVID Crash (Feb-Mar 2020)": ("2020-02-19", "2020-03-23"),
    "2022 Rate-Hike Bear Market": ("2022-01-03", "2022-10-12"),
    "2023 Banking Mini-Crisis (SVB)": ("2023-03-08", "2023-03-13"),
}

# ---------------------------------------------------------------------------
# Geopolitical / macro views
# ---------------------------------------------------------------------------
# Each view is a slider from 0-10 (default 5 = neutral / no view). The
# `direction` sign says which way a HIGH score pushes the target asset's
# expected return. `tilt_scale` is the max annualized expected-return nudge
# at full conviction (score = 0 or 10) -- a disclosed modeling assumption,
# not derived from an event-study regression (see README limitations).
#
# These questions are adapted from the kind of live geopolitical/macro
# event markets found on prediction platforms like Polymarket and Kalshi
# (e.g. Middle East de-escalation, Fed rate-cut count, WTI price levels,
# USD/MXN) -- MacroTilt does not pull live odds from those platforms; the
# user supplies their own conviction score. See README for why we scoped
# out a live prediction-market API integration for this deadline.

# Note on multiple views per asset: Black-Litterman explicitly supports more
# than one view touching the same asset (each becomes its own row of the P
# matrix, with its own confidence in Omega). Two views on XLE -- one about
# conflict, one about physical supply -- are economically distinct questions,
# and the model resolves them by confidence weighting rather than requiring
# us to pick one. This is standard, not a workaround.

VIEW_CATEGORIES = ["Geopolitics", "Monetary Policy", "Growth & Inflation"]

VIEWS_CONFIG = [
    # --- Geopolitics -------------------------------------------------------
    {
        "key": "mideast_deescalation",
        "category": "Geopolitics",
        "icon": "\U0001F54A️",
        "label": "Middle East De-escalation",
        "question": "How likely is it that Middle East conflict(s) meaningfully de-escalate by end of 2026?",
        "low_caption": "0 = Conflict escalates further",
        "high_caption": "10 = Lasting de-escalation",
        "rationale": "De-escalation removes the geopolitical risk premium embedded in "
                     "energy prices, so energy equities lose a tailwind.",
        "asset": "XLE",
        "direction": -1,  # high score (de-escalation likely) -> LOWER energy expected return
        "tilt_scale": 0.06,
    },
    {
        "key": "supply_disruption",
        "category": "Geopolitics",
        "icon": "\U0001F6E2️",
        "label": "Energy Supply Disruption",
        "question": "How likely is a physical oil supply disruption (shipping lanes, OPEC+ cuts, sanctions) in the next year?",
        "low_caption": "0 = Supply stays ample",
        "high_caption": "10 = Major disruption likely",
        "rationale": "A physical supply shock lifts crude and energy-equity earnings "
                     "regardless of whether conflict headlines are calming.",
        "asset": "XLE",
        "direction": +1,
        "tilt_scale": 0.05,
    },
    {
        "key": "trade_tensions",
        "category": "Geopolitics",
        "icon": "\U0001F6A2",
        "label": "Trade & Tariff Tensions",
        "question": "How likely are escalating trade barriers or tariffs between major economies?",
        "low_caption": "0 = Trade tensions ease",
        "high_caption": "10 = Tariffs escalate sharply",
        "rationale": "Export-driven emerging markets carry the most direct earnings "
                     "exposure to tariff escalation.",
        "asset": "EEM",
        "direction": -1,
        "tilt_scale": 0.05,
    },
    # --- Monetary Policy ---------------------------------------------------
    {
        "key": "fed_cuts",
        "category": "Monetary Policy",
        "icon": "\U0001F3E6",
        "label": "Fed Rate-Cut Pace",
        "question": "How likely are more Fed rate cuts in 2026 than the market currently prices in?",
        "low_caption": "0 = Fewer cuts, or hikes",
        "high_caption": "10 = Many more cuts than priced",
        "rationale": "Long-duration Treasuries gain the most when policy rates fall "
                     "faster than the curve already implies.",
        "asset": "TLT",
        "direction": +1,  # more cuts likely -> HIGHER long-duration Treasury expected return
        "tilt_scale": 0.06,
    },
    {
        "key": "dollar_strength",
        "category": "Monetary Policy",
        "icon": "\U0001F4B5",
        "label": "Dollar Strength",
        "question": "How likely is continued or renewed US dollar strength over the next year?",
        "low_caption": "0 = Dollar weakens",
        "high_caption": "10 = Dollar strengthens sharply",
        "rationale": "Safe-haven flows and rate differentials drive the dollar; a "
                     "stronger dollar is a direct headwind for non-US assets.",
        "asset": "UUP",
        "direction": +1,
        "tilt_scale": 0.05,
    },
    # --- Growth & Inflation ------------------------------------------------
    {
        "key": "recession_risk",
        "category": "Growth & Inflation",
        "icon": "\U0001F4C9",
        "label": "Recession Risk (12 months)",
        "question": "How likely is a US or global growth slowdown / recession in the next 12 months?",
        "low_caption": "0 = Growth stays solid",
        "high_caption": "10 = Recession very likely",
        "rationale": "Recession compresses corporate earnings, which hits broad US "
                     "equity expected returns first.",
        "asset": "SPY",
        "direction": -1,  # higher recession risk -> LOWER equity expected return
        "tilt_scale": 0.06,
    },
    {
        "key": "inflation_persistence",
        "category": "Growth & Inflation",
        "icon": "\U0001F525",
        "label": "Inflation Persistence",
        "question": "How likely is inflation to stay stubbornly above central-bank targets?",
        "low_caption": "0 = Inflation returns to target",
        "high_caption": "10 = Inflation stays sticky/high",
        "rationale": "Gold is the classic store-of-value hedge when real rates fall "
                     "and purchasing power erodes.",
        "asset": "GLD",
        "direction": +1,
        "tilt_scale": 0.05,
    },
    {
        "key": "em_growth",
        "category": "Growth & Inflation",
        "icon": "\U0001F30F",
        "label": "Emerging Market Growth",
        "question": "How likely is emerging-market growth (China in particular) to surprise to the upside?",
        "low_caption": "0 = EM growth disappoints",
        "high_caption": "10 = Strong EM upside surprise",
        "rationale": "EM equity earnings are highly geared to Chinese and broader "
                     "emerging-market demand growth.",
        "asset": "EEM",
        "direction": +1,
        "tilt_scale": 0.05,
    },
]


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_prices(start: str = DATA_START, end: str | None = None) -> pd.DataFrame:
    """Download daily adjusted close for the fixed 6-asset universe."""
    raw = yf.download(TICKERS, start=start, end=end, auto_adjust=True, progress=False)

    if raw is None or raw.empty:
        raise RuntimeError(
            "yfinance returned no data. Check your internet connection or "
            "try again in a few minutes (Yahoo Finance occasionally rate-limits)."
        )

    prices = raw["Close"] if isinstance(raw.columns, pd.MultiIndex) else raw
    prices = prices[TICKERS].dropna(how="all")

    prices = prices.ffill()
    missing_frac = prices.isna().mean()
    bad = missing_frac[missing_frac > 0.02]
    if not bad.empty:
        raise RuntimeError(
            f"More than 2% of rows missing for: {', '.join(bad.index)}. "
            "Data quality issue -- investigate before trusting the analysis."
        )

    return prices.dropna()


def daily_returns(prices: pd.DataFrame) -> pd.DataFrame:
    return prices.pct_change().dropna()


# ---------------------------------------------------------------------------
# Portfolio math (return/risk/drawdown/tracking-error) -- generic, works for
# any subset of TICKERS with a weight dict.
# ---------------------------------------------------------------------------

def portfolio_returns(returns: pd.DataFrame, weights: dict[str, float]) -> pd.Series:
    w = pd.Series(weights)[returns.columns]
    return returns.dot(w)


def cumulative_value(ret_series: pd.Series, start_value: float = 1.0) -> pd.Series:
    return start_value * (1 + ret_series).cumprod()


def max_drawdown(ret_series: pd.Series) -> float:
    curve = cumulative_value(ret_series)
    running_max = curve.cummax()
    drawdown = curve / running_max - 1.0
    return float(drawdown.min())


def drawdown_series(ret_series: pd.Series) -> pd.Series:
    curve = cumulative_value(ret_series)
    running_max = curve.cummax()
    return curve / running_max - 1.0


def annualized_return(ret_series: pd.Series) -> float:
    total_growth = (1 + ret_series).prod()
    years = len(ret_series) / 252.0
    return float(total_growth ** (1 / years) - 1) if years > 0 else float("nan")


def annualized_vol(ret_series: pd.Series) -> float:
    return float(ret_series.std() * np.sqrt(252))


def sharpe_ratio(ret_series: pd.Series, rf_annual: float = RISK_FREE_RATE) -> float:
    ann_ret = annualized_return(ret_series)
    ann_vol = annualized_vol(ret_series)
    return float((ann_ret - rf_annual) / ann_vol) if ann_vol > 0 else float("nan")


def tracking_error(ret_series: pd.Series, benchmark_series: pd.Series) -> float:
    a, b = ret_series.align(benchmark_series, join="inner")
    active = a - b
    return float(active.std() * np.sqrt(252))


def stress_period_drawdowns(returns: pd.DataFrame, weights: dict[str, float]) -> dict[str, float]:
    port_ret = portfolio_returns(returns, weights)
    results = {}
    for label, (start, end) in STRESS_PERIODS.items():
        window = port_ret.loc[(port_ret.index >= start) & (port_ret.index <= end)]
        results[label] = max_drawdown(window) if not window.empty else float("nan")
    return results


def equal_weight(cols: list[str]) -> dict[str, float]:
    n = len(cols)
    return {c: 1 / n for c in cols}


def recent_performance(prices: pd.DataFrame) -> pd.DataFrame:
    """Trailing price changes per asset over standard lookback windows.

    Powers the market-pulse strip. Windows are expressed in trading days
    (~21/month, ~252/year) rather than calendar dates so a market holiday
    never silently shifts a window; YTD is genuinely calendar-based and is
    computed from the last close of the prior year. Any window longer than
    the available history returns NaN rather than a misleading partial
    number.
    """
    out = {}
    last = prices.iloc[-1]

    windows = {"1D": 1, "1W": 5, "1M": 21, "1Y": 252}
    for label, lag in windows.items():
        if len(prices) > lag:
            out[label] = (last / prices.iloc[-1 - lag] - 1.0)
        else:
            out[label] = pd.Series(float("nan"), index=prices.columns)

    year_start = prices.index[-1].year
    prior = prices[prices.index.year < year_start]
    out["YTD"] = (last / prior.iloc[-1] - 1.0) if len(prior) else pd.Series(
        float("nan"), index=prices.columns
    )

    return pd.DataFrame(out)


def sparkline_data(prices: pd.DataFrame, days: int = 90) -> pd.DataFrame:
    """Recent price history rebased to 100, for inline sparklines."""
    window = prices.tail(days)
    return window / window.iloc[0] * 100.0


def rolling_metrics(ret_series: pd.Series, window: int = 252) -> pd.DataFrame:
    """Rolling annualized return and volatility -- shows whether headline
    full-sample numbers are stable or driven by one regime.
    """
    roll_vol = ret_series.rolling(window).std() * np.sqrt(252)
    roll_ret = (1 + ret_series).rolling(window).apply(lambda x: x.prod(), raw=True) - 1
    return pd.DataFrame({"Rolling return": roll_ret, "Rolling volatility": roll_vol}).dropna()


def asset_summary_table(returns: pd.DataFrame) -> pd.DataFrame:
    """Per-asset realized statistics over the full sample -- the raw
    building blocks every portfolio number in the app is derived from.
    Shown in the Asset Detail tab so the inputs can be audited directly
    rather than taken on faith.
    """
    rows = []
    for t in returns.columns:
        s = returns[t]
        rows.append({
            "Asset": ASSET_LABELS[t],
            "Ticker": t,
            "Ann. Return": annualized_return(s),
            "Ann. Volatility": annualized_vol(s),
            "Sharpe": sharpe_ratio(s),
            "Max Drawdown": max_drawdown(s),
        })
    return pd.DataFrame(rows).set_index("Ticker")


# ---------------------------------------------------------------------------
# Black-Litterman
# ---------------------------------------------------------------------------

def annualized_covariance(returns: pd.DataFrame) -> pd.DataFrame:
    return returns.cov() * 252


def implied_risk_aversion(ann_return: float, ann_vol: float, rf: float = RISK_FREE_RATE) -> float:
    """Standard reverse-optimization risk-aversion coefficient implied by a
    reference portfolio's realized Sharpe: delta = (E[r] - rf) / var(r).
    """
    var = ann_vol ** 2
    if var <= 0:
        return 2.5  # academic default fallback; shouldn't trigger on real data
    return max((ann_return - rf) / var, 0.5)  # floor to avoid a degenerate/negative delta


def equilibrium_returns(sigma: pd.DataFrame, w_eq: pd.Series, delta: float) -> pd.Series:
    """pi = delta * Sigma @ w_eq -- the Black-Litterman prior.

    IMPORTANT: because `delta` is computed from EXCESS return (ann_return -
    rf) over variance, this `pi` is itself already expressed in
    excess-return space (w_eq' @ pi == equal-weight portfolio's excess
    return over rf, by construction). Everything downstream (views,
    posterior, optimizer) stays in excess-return space -- rf is never
    subtracted a second time.
    """
    return delta * sigma.dot(w_eq)


def build_views(scores: dict[str, float], cols: list[str], sigma: pd.DataFrame, pi: pd.Series, tau: float):
    """Turn slider scores (0-10, 5=neutral) into (P, Q, Omega, active_labels).

    A view with score exactly 5 contributes nothing and is dropped entirely
    -- this is what makes the "all sliders neutral" edge case reduce
    exactly to the prior, with no view-related numerical noise.
    """
    rows_P, rows_Q, diag_omega, active_labels = [], [], [], []

    for cfg in VIEWS_CONFIG:
        score = scores.get(cfg["key"], 5.0)
        strength = (score - 5.0) / 5.0  # in [-1, 1], 0 = neutral
        if abs(strength) < 1e-9:
            continue

        asset = cfg["asset"]
        idx = cols.index(asset)
        p_row = np.zeros(len(cols))
        p_row[idx] = 1.0

        view_return = pi[asset] + cfg["direction"] * strength * cfg["tilt_scale"]
        confidence = abs(strength)  # 0 < confidence <= 1

        p_sigma_p = float(p_row @ sigma.values @ p_row)
        omega_ii = tau * p_sigma_p * (1.0 / confidence - 1.0 + 1e-6)

        rows_P.append(p_row)
        rows_Q.append(view_return)
        diag_omega.append(max(omega_ii, 1e-10))
        active_labels.append(f"{cfg['label']} (score {score:.0f}/10)")

    if not rows_P:
        return None, None, None, []

    P = np.array(rows_P)
    Q = np.array(rows_Q)
    Omega = np.diag(diag_omega)
    return P, Q, Omega, active_labels


def bl_posterior_returns(pi: pd.Series, sigma: pd.DataFrame, P, Q, Omega, tau: float) -> pd.Series:
    """Standard Black-Litterman posterior expected-return formula:

        pi_post = pi + tau*Sigma*P' * inv(P*tau*Sigma*P' + Omega) * (Q - P*pi)

    If there are no active views (P is None), the posterior is just the
    prior -- this is the identity the edge-case test in
    verify_calculations.py checks.
    """
    if P is None:
        return pi.copy()

    sigma_v = sigma.values
    pi_v = pi.values
    tau_sigma = tau * sigma_v

    middle = P @ tau_sigma @ P.T + Omega
    adjustment = tau_sigma @ P.T @ np.linalg.solve(middle, (Q - P @ pi_v))
    pi_post = pi_v + adjustment
    return pd.Series(pi_post, index=pi.index)


def optimize_max_sharpe(
    pi_post: pd.Series,
    sigma: pd.DataFrame,
    cols: list[str],
    max_position: float = 0.40,
) -> dict[str, float]:
    """Long-only mean-variance optimization: maximize Sharpe ratio using the
    Black-Litterman posterior expected EXCESS returns and the historical
    covariance matrix, capped at `max_position` per asset so no single macro
    bet can swamp the portfolio.

    `pi_post` is already excess return over the risk-free rate (see
    equilibrium_returns), so the objective does NOT subtract rf again --
    doing so would shift the optimizer's implied tangency direction away
    from Sigma^-1 @ pi and break the "neutral views -> recovers equal
    weight" identity that verify_calculations.py checks.
    """
    n = len(cols)
    sigma_v = sigma.values
    pi_v = pi_post.values
    x0 = np.repeat(1 / n, n)

    def neg_sharpe(w):
        ret = w @ pi_v
        vol = np.sqrt(max(w @ sigma_v @ w, 1e-12))
        return -ret / vol

    constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}]
    bounds = [(0.0, max_position)] * n

    result = minimize(
        neg_sharpe, x0, method="SLSQP", bounds=bounds, constraints=constraints,
        options={"maxiter": 500, "ftol": 1e-10},
    )

    if not result.success:
        weights = dict(zip(cols, x0))
        weights["_solver_warning"] = result.message
        return weights

    return dict(zip(cols, result.x))


def run_macrotilt(returns: pd.DataFrame, scores: dict[str, float], tau: float = 0.05) -> dict:
    """End-to-end pipeline: historical stats -> BL prior -> BL posterior (with
    user's geopolitical views) -> max-Sharpe optimization. Returns a dict
    with every intermediate object so the UI (and the verification script)
    can inspect each stage independently.
    """
    cols = list(returns.columns)
    sigma = annualized_covariance(returns)
    w_eq = pd.Series(equal_weight(cols))

    eq_port_ret = portfolio_returns(returns, equal_weight(cols))
    delta = implied_risk_aversion(annualized_return(eq_port_ret), annualized_vol(eq_port_ret))
    pi = equilibrium_returns(sigma, w_eq, delta)

    P, Q, Omega, active_labels = build_views(scores, cols, sigma, pi, tau)
    pi_post = bl_posterior_returns(pi, sigma, P, Q, Omega, tau)

    weights = optimize_max_sharpe(pi_post, sigma, cols)
    solver_warning = weights.pop("_solver_warning", None)

    return {
        "sigma": sigma,
        "w_eq": w_eq,
        "delta": delta,
        "pi": pi,
        "pi_post": pi_post,
        "active_views": active_labels,
        "weights": weights,
        "solver_warning": solver_warning,
    }
