"""
verify_calculations.py — independent verification for MacroTilt
------------------------------------------------------------------
Two checks, run with:  python verify_calculations.py

Check 1 (edge case): with every geopolitical slider left at neutral (5/10),
the Black-Litterman machinery should contribute ZERO active views, and the
resulting max-Sharpe-optimized portfolio should reduce to plain equal
weight. This is a real mathematical identity (reverse-optimizing pi from
w_eq, then re-optimizing on that same pi, must recover w_eq -- a known
property of Black-Litterman/reverse optimization), not a tautology of the
code: a bug in the view-weighting logic, the posterior formula, the
excess-return bookkeeping, or the optimizer's objective would very likely
break this identity even though each of those pieces "looks right" in
isolation. (An earlier version of this app had exactly such a bug: the
optimizer subtracted the risk-free rate a second time, which silently
shifted the "neutral" portfolio away from equal weight. This check exists
specifically because that class of bug is easy to introduce and easy to
miss by eyeballing code.)

Check 2 (independent recomputation): reimplements Black-Litterman's
posterior-return formula with a different linear-algebra path (explicit
matrix inverse instead of np.linalg.solve) and confirms it agrees with
engine.bl_posterior_returns() to within 1e-8 on a real, non-neutral set of
views.
"""

import numpy as np
import pandas as pd

import engine


def manual_bl_posterior(pi, sigma, P, Q, Omega, tau):
    """Same BL formula as engine.bl_posterior_returns(), but computed with
    an explicit matrix inverse (np.linalg.inv) instead of np.linalg.solve,
    as an independent numerical path.
    """
    sigma_v = sigma.values
    pi_v = pi.values
    tau_sigma = tau * sigma_v
    middle_inv = np.linalg.inv(P @ tau_sigma @ P.T + Omega)
    adjustment = tau_sigma @ P.T @ middle_inv @ (Q - P @ pi_v)
    return pd.Series(pi_v + adjustment, index=pi.index)


def main():
    print("Loading price data independently...")
    prices = engine.load_prices()
    returns = engine.daily_returns(prices)
    print(f"  {len(returns)} trading days, {returns.index.min().date()} to {returns.index.max().date()}\n")

    # --- Check 1: neutral views must recover equal weight -----------------
    print("Check 1 (edge case): all sliders neutral -> optimizer should recover equal weight")
    neutral_scores = {cfg["key"]: 5.0 for cfg in engine.VIEWS_CONFIG}
    result = engine.run_macrotilt(returns, neutral_scores)

    print(f"  active views (should be []): {result['active_views']}")
    assert result["active_views"] == [], "Neutral scores produced an active view -- bug in build_views()."

    w_opt = pd.Series(result["weights"])
    w_eq = result["w_eq"]
    max_diff = (w_opt[w_eq.index] - w_eq).abs().max()
    print(f"  optimized weights: { {k: round(v, 4) for k, v in w_opt.items()} }")
    print(f"  equal weights:     { {k: round(v, 4) for k, v in w_eq.items()} }")
    print(f"  max abs difference: {max_diff:.2e}")
    assert max_diff < 1e-6, "Neutral-view portfolio should equal equal-weight almost exactly."
    print("  PASS\n")

    # --- Check 2: independent recomputation of the BL posterior -----------
    print("Check 2: independent BL posterior recomputation (explicit inverse vs. linalg.solve)")
    test_scores = {"mideast_deescalation": 2, "fed_cuts": 8, "recession_risk": 7, "dollar_strength": 6}
    cols = list(returns.columns)
    sigma = engine.annualized_covariance(returns)
    w_eq_series = pd.Series(engine.equal_weight(cols))
    eq_ret = engine.portfolio_returns(returns, engine.equal_weight(cols))
    delta = engine.implied_risk_aversion(engine.annualized_return(eq_ret), engine.annualized_vol(eq_ret))
    pi = engine.equilibrium_returns(sigma, w_eq_series, delta)

    tau = 0.05
    P, Q, Omega, labels = engine.build_views(test_scores, cols, sigma, pi, tau)
    engine_posterior = engine.bl_posterior_returns(pi, sigma, P, Q, Omega, tau)
    manual_posterior = manual_bl_posterior(pi, sigma, P, Q, Omega, tau)

    diff = (engine_posterior - manual_posterior).abs().max()
    print(f"  active views: {labels}")
    print(f"  engine posterior: { {k: round(v, 5) for k, v in engine_posterior.items()} }")
    print(f"  manual posterior: { {k: round(v, 5) for k, v in manual_posterior.items()} }")
    print(f"  max abs difference: {diff:.2e}")
    assert diff < 1e-8, "Independent recomputation disagrees with engine.bl_posterior_returns()!"
    print("  PASS\n")

    print("Reliability caveat (see README / app Limitations tab for full discussion):")
    print(
        "  These checks confirm the ARITHMETIC and the model's internal consistency\n"
        "  (no views = no change). They do NOT confirm that the view->expected-return\n"
        "  tilt magnitudes (tilt_scale) are the 'correct' size, or that historical\n"
        "  covariance is a good estimate of future covariance. Treat MacroTilt's\n"
        "  output as a transparent, mechanical translation of a stated view into a\n"
        "  bounded allocation -- not a return forecast."
    )


if __name__ == "__main__":
    main()
