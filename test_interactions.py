"""
Interaction test suite.

Verifies that the sidebar controls actually drive the model: preset buttons
must move the sliders, sliders must move the allocation, and neutral must
return equal weight. Run with:  python test_interactions.py
"""

import sys

import numpy as np
import pandas as pd

import engine

np.random.seed(42)
_N = 4600
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

import macrotilt_ui as ui  # noqa: E402

failures = []


def check(label, condition, detail=""):
    if condition:
        print(f"  ok    {label}")
    else:
        print(f"  FAIL  {label}  {detail}")
        failures.append(label)


# --- 1. Entry point routes without error ---------------------------------
print("Navigation")
at = AppTest.from_file("app.py", default_timeout=180)
at.run()
check("app.py runs st.navigation without exception",
      not at.exception,
      "; ".join(f"{e.type}: {e.message}" for e in at.exception) if at.exception else "")

# --- 2. Sliders exist and default to neutral -----------------------------
print("\nSidebar state")
at = AppTest.from_file("views/build.py", default_timeout=180)
at.run()

slider_keys = [f"slider_{c['key']}" for c in engine.VIEWS_CONFIG]
found = [s.key for s in at.sidebar.slider]
check(f"all {len(slider_keys)} view sliders render",
      all(k in found for k in slider_keys),
      f"missing {[k for k in slider_keys if k not in found]}")
check("all sliders default to neutral (5)",
      all(at.session_state[k] == 5 for k in slider_keys))

n_buttons = len(at.sidebar.button)
check(f"all {len(ui.PRESET_SCENARIOS)} preset buttons render",
      n_buttons == len(ui.PRESET_SCENARIOS), f"found {n_buttons}")

# --- 3. Neutral -> equal weight ------------------------------------------
print("\nNeutral identity (through the UI, not just the engine)")
returns = engine.daily_returns(_PRICES)
neutral = engine.run_macrotilt(returns, {c["key"]: 5 for c in engine.VIEWS_CONFIG}, tau=0.05)
w = pd.Series(neutral["weights"])
check("neutral sliders produce equal weight",
      (w - 1 / len(w)).abs().max() < 1e-6,
      f"max deviation {(w - 1/len(w)).abs().max():.2e}")
check("neutral sliders produce zero active views", neutral["active_views"] == [])

# --- 4. Each preset button moves the sliders -----------------------------
# Buttons are laid out in two columns, so DOM order interleaves the presets
# (column 0 holds the even indices, column 1 the odd ones). Match on the
# button's own label rather than its position -- indexing by position tests
# the layout, not the behaviour.
print("\nPreset buttons")
for name, preset in ui.PRESET_SCENARIOS.items():
    at = AppTest.from_file("views/build.py", default_timeout=180)
    at.run()

    target = [b for b in at.sidebar.button if b.label.endswith(name)]
    if len(target) != 1:
        check(f"'{name}' button is uniquely identifiable", False,
              f"matched {len(target)} buttons")
        continue

    target[0].click().run()

    got = {c["key"]: at.session_state[f"slider_{c['key']}"] for c in engine.VIEWS_CONFIG}
    check(f"'{name}' sets all sliders correctly", got == preset["scores"],
          f"expected {preset['scores']} got {got}")
    if at.exception:
        check(f"'{name}' renders without exception", False,
              "; ".join(f"{e.type}: {e.message}" for e in at.exception))

# --- 5. Moving a slider changes the allocation ---------------------------
print("\nSlider responsiveness")
at = AppTest.from_file("views/build.py", default_timeout=180)
at.run()
before = engine.run_macrotilt(returns, {c["key"]: 5 for c in engine.VIEWS_CONFIG}, tau=0.05)["weights"]

at.sidebar.slider("slider_recession_risk").set_value(9).run()
check("slider value persists in session state",
      at.session_state["slider_recession_risk"] == 9)
check("page re-renders without exception after slider move",
      not at.exception,
      "; ".join(f"{e.type}: {e.message}" for e in at.exception) if at.exception else "")

after_scores = {c["key"]: 5 for c in engine.VIEWS_CONFIG}
after_scores["recession_risk"] = 9
after = engine.run_macrotilt(returns, after_scores, tau=0.05)["weights"]
check("high recession risk reduces the SPY weight",
      after["SPY"] < before["SPY"],
      f"SPY {before['SPY']:.3f} -> {after['SPY']:.3f}")

after_scores["recession_risk"] = 1
low = engine.run_macrotilt(returns, after_scores, tau=0.05)["weights"]
check("low recession risk increases the SPY weight",
      low["SPY"] > before["SPY"],
      f"SPY {before['SPY']:.3f} -> {low['SPY']:.3f}")

# --- 6. Directional sanity across every view -----------------------------
print("\nDirectional sanity for every view")
for cfg in engine.VIEWS_CONFIG:
    base = {c["key"]: 5 for c in engine.VIEWS_CONFIG}
    hi, lo = dict(base), dict(base)
    hi[cfg["key"]], lo[cfg["key"]] = 10, 0
    w_hi = engine.run_macrotilt(returns, hi, tau=0.05)["weights"][cfg["asset"]]
    w_lo = engine.run_macrotilt(returns, lo, tau=0.05)["weights"][cfg["asset"]]
    ok = (w_hi > w_lo) if cfg["direction"] > 0 else (w_hi < w_lo)
    arrow = "raises" if cfg["direction"] > 0 else "lowers"
    check(f"'{cfg['label']}' at 10 {arrow} {cfg['asset']}", ok,
          f"lo {w_lo:.3f} hi {w_hi:.3f}")

# --- 7. Constraints hold under extreme input -----------------------------
print("\nConstraints under extreme inputs")
for label, val in [("all sliders at 0", 0), ("all sliders at 10", 10)]:
    extreme = {c["key"]: val for c in engine.VIEWS_CONFIG}
    r = engine.run_macrotilt(returns, extreme, tau=0.20)
    ws = r["weights"]
    check(f"{label}: weights sum to 1", abs(sum(ws.values()) - 1) < 1e-6)
    check(f"{label}: 40% cap respected", max(ws.values()) <= 0.40 + 1e-6,
          f"max {max(ws.values()):.3f}")
    check(f"{label}: no negative weights", min(ws.values()) >= -1e-9)

print()
if failures:
    print(f"{len(failures)} FAILURE(S): {failures}")
    sys.exit(1)
print("ALL INTERACTION TESTS PASS")
