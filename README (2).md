# MacroTilt — Your Worldview, Allocated

**IE New York College · Python for Finance · Final Project (Group ___)**

**Deployed app:** `<PASTE YOUR STREAMLIT COMMUNITY CLOUD URL HERE BEFORE SUBMITTING>`

## The pitch

The S&P 500 sits near all-time highs. Bond yields just hit multi-decade
highs, which is another way of saying bond prices took a hit. "Buy the
index and hold 60/40" was built for a world that didn't have to price a
ceasefire, a Fed pivot, or a shipping-lane attack into markets in real
time. **MacroTilt** asks an investor a handful of geopolitical/macro
questions on a 0-10 conviction scale — the same *kind* of question you'd
see phrased as a prediction-market contract on Polymarket or Kalshi — and
mechanically translates that stated worldview into a bounded portfolio
tilt across six liquid, real assets, benchmarked honestly against
equal-weight and a plain S&P 500 portfolio.

## Who this is for, and the decision it answers

**Investor:** a self-directed investor who thinks in macro/geopolitical
terms and wants their portfolio to reflect that view without hand-picking
individual trades.

**Decision:** "Given my read on eight live macro questions — Middle East
de-escalation, energy supply disruption, trade tensions, the Fed's
rate-cut path, dollar strength, recession risk, inflation persistence, and
EM growth — what allocation across US equities / EM equities / Treasuries
/ gold / energy equities / the dollar reflects that view, and how would it
have performed through real historical stress events?"

## Data provenance

| | |
|---|---|
| Provider | Yahoo Finance, via the `yfinance` Python library |
| Instruments | SPY (US equities), EEM (EM equities), TLT (20+Y Treasuries), GLD (Gold), XLE (Energy equities), UUP (US Dollar Index) |
| Field | Daily adjusted close (`auto_adjust=True`) |
| Date range | 2007-03-01 (just after UUP's 2007-02-20 inception) through the current date, pulled live at runtime |
| Retrieval | Automatic — the app fetches fresh data on load (cached 12h in-app) |
| Risk-free rate | 4.0% annualized, a disclosed simplifying assumption (approx. current short T-bill yield), not fetched live |

UUP (the youngest fund in the universe) sets the floor on shared history;
starting there means the backtest spans the 2008 Global Financial Crisis,
the 2020 COVID crash, the 2022 rate-hike bear market, and the 2023
regional-banking mini-crisis — all four are used as stress-test windows.

**Design choice — no futures-based commodity ETFs.** We use XLE (an
equity-based energy sector ETF) rather than USO/BNO (futures-based oil
ETFs) for energy/oil exposure, because futures-based commodity ETFs suffer
contango/roll-yield decay that distorts long-horizon buy-and-hold returns.
The tradeoff: XLE is an imperfect (equity-beta) proxy for spot oil moves,
which we disclose rather than paper over.

**Design choice — no live prediction-market API.** MacroTilt's sliders are
inspired by the kind of live geopolitical/macro questions you'd find as
contracts on Polymarket or Kalshi (Middle East de-escalation, Fed cut
count, WTI price levels, USD/MXN, etc.), but the app does not pull live
odds from those platforms — the user supplies their own conviction score.
We scoped this out deliberately: it adds an external dependency,
authentication, and another point of failure, for a feature that doesn't
change the app's core defensibility.

## Method: Black-Litterman

1. **Historical stats.** Pull daily prices for the 6-asset universe, clean
   (forward-fill isolated gaps, hard-fail if any ticker is missing >2% of
   rows), compute daily returns and an annualized covariance matrix.
2. **Neutral baseline (the Black-Litterman prior).** Reverse-optimize: ask
   "what expected returns would make the equal-weight portfolio the
   mathematically optimal one?" That's `pi = delta * Sigma @ w_equal`,
   where `delta` (implied risk aversion) comes from the equal-weight
   portfolio's own realized Sharpe ratio. No opinion is baked in yet.
3. **User views.** Each of the eight sliders is a single-asset view: "I
   think this asset's expected return should be nudged up/down by up to a
   few percentage points, with conviction proportional to how far from
   neutral (5/10) I set the slider." A slider left at exactly 5
   contributes nothing. The eight views are grouped into three categories:

   | Category | Views | Target asset |
   |---|---|---|
   | Geopolitics | Middle East De-escalation | XLE (−) |
   | | Energy Supply Disruption | XLE (+) |
   | | Trade & Tariff Tensions | EEM (−) |
   | Monetary Policy | Fed Rate-Cut Pace | TLT (+) |
   | | Dollar Strength | UUP (+) |
   | Growth & Inflation | Recession Risk (12 months) | SPY (−) |
   | | Inflation Persistence | GLD (+) |
   | | Emerging Market Growth | EEM (+) |

   Two views may target the same asset (XLE and EEM each have two).
   Black-Litterman supports this natively — each view is its own row of
   the P matrix with its own confidence in Omega, and the model resolves
   them by confidence weighting. Conflict de-escalation and physical
   supply disruption are economically distinct questions that both move
   energy, so modeling them separately is more honest than collapsing
   them into one slider.
4. **Blend (Black-Litterman posterior).** Views and the neutral baseline
   are combined via the standard BL posterior-return formula, weighted by
   stated confidence.
5. **Re-optimize.** The blended expected returns feed a long-only,
   max-Sharpe mean-variance optimizer, capped at 40% per asset so no
   single macro bet can dominate.
6. **Compare.** Report the result against equal-weight (required baseline)
   and 100% SPY (the "boring" default the product is pitched against).

See the in-app "How This Works" tab for a plain-English walkthrough your
team can use live in the Q&A.

## Meaningful interaction

- **Eight geopolitical/macro sliders (0-10, default 5 = neutral):** each
  directly re-solves the Black-Litterman posterior and re-optimizes,
  grouped into Geopolitics / Monetary Policy / Growth & Inflation.
- **Eight one-click preset scenarios:** Peace Breaks Out, Conflict
  Escalates, Sticky Inflation, Soft Landing Rally, Hard Landing, Trade
  War, Dollar Doubt, and No View (Neutral). Each sets all eight sliders to
  a coherent macro narrative, and each ships with a plain-English
  explanation of *why* every slider sits where it does — a preset the user
  can't interrogate is just a magic button.
- **View-conviction weight (tau):** a standard BL tuning slider controlling
  how strongly stated views move the allocation versus the neutral
  baseline.

## App structure

MacroTilt is a **multi-page Streamlit app**. `app.py` is the entry point and
does nothing but route; each page is its own script in `views/`.

| Page | What it shows |
|---|---|
| 🏠 Overview | The pitch, a live market-pulse strip, and the current portfolio at a glance |
| 🎯 Build Portfolio | The allocation in percent *and* dollars, tilt-vs-equal-weight, CSV export |
| 📈 Performance | Growth of $1, drawdown, and rolling 1-year stability vs. both benchmarks |
| 🚨 Stress Tests | Drawdown inside each dated crisis, plus a day-by-day walk through any one of them |
| 🔬 Scenario Lab | All eight narratives solved and compared — heatmap, risk/return scatter, head-to-head |
| 🔍 Asset Explorer | Per-asset sparklines and stats, growth curves, correlation matrix, slider→asset map |
| 🧮 Methodology | Black-Litterman in plain English, the mechanism visualised, and the formulae |
| 📄 Data & Sources | Provenance table, cleaning rules, deliberate design choices, honest limitations |

The macro sliders live in the sidebar and render on **every** page, backed by
`st.session_state`. Move a slider anywhere and every page reflects it.

### Why the code is split this way

```
app.py             routing only — no logic, no layout
views/*.py         one file per page; presentation only
macrotilt_ui.py    shared theme, sidebar, cached data access, chart styling
engine.py          all financial mathematics — imports no Streamlit at all
```

`engine.py` having no Streamlit import is the load-bearing decision: it means
every calculation can be tested headlessly, which is what `verify_calculations.py`
and the test suite below actually do.

### Colour system

Chart colours are not chosen by eye. They come from a validated categorical
palette, assigned to fixed slots, and **drawn in slot order** (`engine.CHART_ORDER`)
so that neighbouring marks are always a validated adjacent pair. Validated in
dark mode against the card surface `#151a21`:

- lightness band, chroma floor, and ≥3:1 contrast: **pass** on all six
- worst adjacent colour-vision-deficiency ΔE: **8.4** (yellow↔aqua, protan)
- worst adjacent normal-vision ΔE: **19.3** (magenta↔yellow)
- donut ring wrap (green→blue): **29.9** normal / 27.3 deutan

With six series, all-28-pairs separation is mathematically unreachable, so
every categorical chart also carries secondary encoding: direct labels, 2px
surface gaps between fills, a legend, and a table view of the same numbers.
Up/down colours are the reserved status pair and always ship with a ▲/▼ glyph,
so colour never carries meaning alone.

## Testing

Three test scripts, all runnable without a browser:

```bash
python verify_calculations.py   # the required independent verification (live data)
python test_pages.py            # renders all 8 pages, asserts zero exceptions
python test_interactions.py     # asserts the controls actually drive the model
```

`test_pages.py` and `test_interactions.py` use Streamlit's `AppTest` harness with
synthetic price data patched in, so they run offline. Between them they check
that every page renders, every preset button sets all eight sliders correctly,
every view moves its target asset in the documented direction, and the weight
constraints (sum to 1, ≤40% per asset, non-negative) hold even under extreme
slider settings.

## Independent verification

`verify_calculations.py` is a standalone script (not imported by the app):

1. **Edge case:** with every slider at neutral (5/10), no views are active
   and the optimizer must recover equal weight almost exactly (max
   difference < 1e-6). This is a real mathematical identity of reverse
   optimization, not a tautology — an earlier draft of this app had a bug
   (the optimizer subtracted the risk-free rate a second time) that broke
   this exact identity while every individual function still "looked"
   correct. This check is what caught it.
2. **Independent recomputation:** the Black-Litterman posterior-return
   formula is recomputed via an explicit matrix inverse (`np.linalg.inv`),
   a different numerical path from the app's `np.linalg.solve`-based
   implementation, and the two are checked to agree to within 1e-8 on a
   real, non-neutral set of views.

Run it yourself:

```bash
python verify_calculations.py
```

## Known limitations (see also the in-app "Data & Limitations" tab)

- **Tilt magnitudes are a disclosed modeling assumption**, not derived
  from an event-study regression of historical geopolitical shocks.
- **No transaction costs, taxes, or rebalancing frictions** are modeled.
- **Historical covariance is assumed to approximate future covariance** —
  a standard but real mean-variance optimization assumption.
- **Long-only, static weights** for a single evaluation date — no
  shorting, no time-varying allocation.
- **XLE is an equity proxy for energy/oil exposure**, not a direct
  commodity position (see Design Choices above).

## Setup & running locally

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

Requires outbound internet access to Yahoo Finance (`yfinance`). If you're
behind a restrictive firewall/proxy, the data pull will fail with a clear
error message rather than crashing silently.

## Deploying to Streamlit Community Cloud

1. Push this folder to a GitHub repo (Streamlit Cloud can connect to
   private repos too).
2. Go to [share.streamlit.io](https://share.streamlit.io), sign in, click "New app."
3. Point it at this repo, branch `main`, main file `app.py`.
4. Deploy, wait for the build to finish, and paste the resulting URL at the
   top of this README **and** in the presentation PDF before submitting.

## Repository contents

```
app.py                    Entry point — st.navigation routing only
views/
  home.py                 Overview: pitch, market pulse, portfolio at a glance
  build.py                Build Portfolio: allocation in % and $, tilt, CSV export
  performance.py          Performance: growth, drawdown, rolling stability
  stress.py               Stress Tests: crisis-by-crisis drawdown and detail
  scenarios.py            Scenario Lab: all 8 narratives compared
  assets.py               Asset Explorer: sparklines, stats, correlations, view map
  method.py               Methodology: Black-Litterman explained and visualised
  data.py                 Data & Sources: provenance, design choices, limitations
macrotilt_ui.py           Shared theme, sidebar questionnaire, cached data, chart styling
engine.py                 Data loading, Black-Litterman, portfolio math (no Streamlit imports)
verify_calculations.py    Required independent verification (runs on live data)
test_pages.py             Renders all 8 pages headlessly, asserts no exceptions
test_interactions.py      Asserts sidebar controls actually drive the model
requirements.txt          Dependencies
.streamlit/config.toml    Dark theme configuration
README.md                 This file
AI_USE_DISCLOSURE.md      Required AI-use disclosure
MACROTILT_BRIEF.md        Full product/build spec — useful when writing the presentation
```

**Deployment note.** The entry point is deliberately still named `app.py`, so an
existing Streamlit Community Cloud deployment pointing at `app.py` keeps working
without changing its settings. Make sure the repository contains exactly one copy
of each file — GitHub's web uploader silently renames duplicates to `app (1).py`,
which produces a confusing `ModuleNotFoundError` on deploy because the
`requirements.txt` beside it never gets read.
