"""
Page-render test suite.

Runs every page through Streamlit's AppTest harness with synthetic price
data patched in, so page-level runtime errors surface without needing
network access to Yahoo Finance.

    python test_pages.py
"""

import sys

import numpy as np
import pandas as pd

import engine

# --- Patch in deterministic synthetic prices ------------------------------
_SEED = 42
np.random.seed(_SEED)
_N = 4600  # ~18 years of trading days, matching the real 2007-> window
_DATES = pd.bdate_range("2007-03-01", periods=_N)
_MU = {"SPY": 0.00035, "EEM": 0.00022, "TLT": 0.00012,
       "GLD": 0.00028, "XLE": 0.00025, "UUP": 0.00004}
_VOL = {"SPY": 0.0115, "EEM": 0.0145, "TLT": 0.0085,
        "GLD": 0.0098, "XLE": 0.0155, "UUP": 0.0048}
_PRICES = pd.DataFrame({
    t: 100 * (1 + pd.Series(np.random.normal(_MU[t], _VOL[t], _N), index=_DATES)).cumprod()
    for t in engine.TICKERS
})

engine.load_prices = lambda *a, **kw: _PRICES

from streamlit.testing.v1 import AppTest  # noqa: E402

PAGES = [
    "views/home.py",
    "views/build.py",
    "views/performance.py",
    "views/stress.py",
    "views/scenarios.py",
    "views/assets.py",
    "views/method.py",
    "views/data.py",
]

failures = []
print(f"Synthetic data: {len(_PRICES)} rows, "
      f"{_PRICES.index.min().date()} to {_PRICES.index.max().date()}\n")

for page in PAGES:
    at = AppTest.from_file(page, default_timeout=120)
    try:
        at.run()
    except Exception as e:  # harness-level failure
        failures.append((page, f"harness error: {type(e).__name__}: {e}"))
        print(f"  FAIL  {page}  (harness) {type(e).__name__}: {e}")
        continue

    if at.exception:
        for ex in at.exception:
            failures.append((page, f"{ex.type}: {ex.message}"))
            print(f"  FAIL  {page}  {ex.type}: {ex.message}")
    else:
        n_charts = 0
        try:
            n_charts = len(at.get("plotly_chart"))
        except Exception:
            pass
        print(f"  ok    {page}  "
              f"({len(at.markdown)} markdown, {len(at.metric)} metrics, {n_charts} charts)")

print()
if failures:
    print(f"{len(failures)} FAILURE(S)")
    sys.exit(1)
print("ALL PAGES RENDER CLEAN")
