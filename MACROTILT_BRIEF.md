# MacroTilt — Master Product & Build Brief

This is the full spec behind the app in this folder. It exists for three
reasons: (1) it's the source-of-truth your team should read before the
Q&A, since you'll be asked to defend these choices; (2) it's reusable
presentation content — the ethos/pitch section can go almost verbatim into
your slides; (3) if you want a second AI session (Opus or otherwise) to
extend or rebuild any piece of this, paste the relevant section in as
context — it's self-contained.

---

## 1. Ethos & pitch

**Problem.** The default portfolio — 60% stocks, 40% bonds, rebalance and
forget — was built for a market regime that assumed geopolitics was
background noise. It isn't anymore. The S&P 500 trades near all-time
highs. The 10-year yield sits near multi-decade highs, which is the same
fact stated as "bond prices got hit hard." Every major macro headline —
a ceasefire, a Fed pivot, a tanker attack in the Red Sea — reprices
markets within hours, and a static 60/40 has no mechanism to reflect an
investor's read on any of it.

**Positioning.** "It's like a prediction market for your portfolio, minus
the gambling." You're not betting real money on the outcome of a
geopolitical event (that's what Kalshi/Polymarket are for) — you're
stating your conviction about how the world is likely to go, and letting
that conviction mechanically tilt a real, diversified portfolio away from
a neutral baseline. Bounded, transparent, reversible.

**Tagline candidates:** "Your worldview, allocated." / "Trade your read on
the world, not just a ticker." / "Where geopolitics meets your portfolio."

**Name.** Built as **MacroTilt**. Alternates considered: MacroCompass,
Geopolitical Portfolio Navigator. "MacroTilt" won because it names the
actual mechanism (a *tilt* away from neutral, driven by *macro* views) —
easy to say once in a live demo and have the audience understand exactly
what the app does.

---

## 2. Investor & decision (required by the rubric — item 1)

**Investor:** a self-directed investor who thinks in macro/geopolitical
terms and wants a portfolio that reflects that view without hand-picking
individual trades.

**Decision:** "Given my read on a handful of live macro questions, what
allocation across US equities / EM equities / Treasuries / gold / energy
equities / the dollar reflects that view — and how would it have
performed through real historical stress events?"

---

## 3. Asset universe

| Ticker | What it is | Role |
|---|---|---|
| SPY | S&P 500 | Core US equity beta — the "boring baseline" the pitch is built against |
| EEM | Emerging-market equities | Diversifier, dollar-sensitive |
| TLT | 20+ Year US Treasuries | Duration / recession-hedge / Fed-policy proxy |
| GLD | Gold | Cross-regime hedge (inflation, geopolitics, monetary risk) |
| XLE | Energy-sector equities | Oil/energy geopolitical proxy — **equity-based on purpose** |
| UUP | US Dollar Index (bullish) | Direct USD-strength exposure, safe-haven flows |

**Why XLE and not USO/BNO for oil exposure.** The user's own instinct here
was correct and we followed it: futures-based commodity ETFs (USO, BNO)
hold rolling front-month futures contracts and bleed value to
contango/roll-yield over long holding periods, independent of what spot
oil actually does. That's a bad property for a buy-and-hold allocation
tool. XLE (equity-based, holds Exxon/Chevron/etc.) avoids that structural
decay at the cost of being an imperfect proxy — energy-equity beta to
crude isn't 1:1. We disclose this rather than hide it.

**Data start date: 2007-03-01.** UUP (Invesco DB US Dollar Index Bullish
Fund) launched **2007-02-20** — confirmed via web search, not assumed —
and is the youngest fund in the six-asset universe, so it sets the floor
on shared history. Starting there is actually a feature, not just a
constraint: it means the backtest spans the **2008 Global Financial
Crisis**, the 2020 COVID crash, the 2022 rate-hike bear market, and the
2023 regional-banking mini-crisis — four real stress events, not a
thin recent-history sample.

---

## 4. The geopolitical/macro questions (the "meaningful interaction")

Adapted from the kind of live event-contract questions found on
prediction markets like Polymarket and Kalshi (Middle East conflict
de-escalation, Fed rate-cut counts, WTI price levels, USD/MXN, etc.) —
**MacroTilt does not pull live odds from those platforms.** The user
supplies their own 0-10 conviction score for each question below. This
was a deliberate scope decision (see §6).

Eight sliders, grouped into three categories:

| Category | Slider | Primary asset | High score (10) means |
|---|---|---|---|
| Geopolitics | Middle East De-escalation | XLE (−) | De-escalation → risk premium fades → **reduce** energy |
| Geopolitics | Energy Supply Disruption | XLE (+) | Physical supply shock → **increase** energy |
| Geopolitics | Trade & Tariff Tensions | EEM (−) | Tariffs escalate → **reduce** emerging markets |
| Monetary Policy | Fed Rate-Cut Pace | TLT (+) | More cuts than priced → **increase** duration |
| Monetary Policy | Dollar Strength | UUP (+) | Dollar strengthens → **increase** dollar |
| Growth & Inflation | Recession Risk (12 months) | SPY (−) | Recession likely → **reduce** US equity |
| Growth & Inflation | Inflation Persistence | GLD (+) | Inflation stays sticky → **increase** gold |
| Growth & Inflation | Emerging Market Growth | EEM (+) | EM upside surprise → **increase** emerging markets |

Each slider maps to one asset's expected-return view, scaled by distance
from neutral (5 = no view). A slider left at 5 contributes nothing —
verified as a hard identity in `verify_calculations.py`.

**Two views can target the same asset** (XLE and EEM each have two), and
that's deliberate, not sloppy. Black-Litterman supports multiple views
natively: each becomes its own row of the P matrix with its own confidence
entry in Omega, and the model resolves them by confidence weighting.
Conflict de-escalation and physical supply disruption are economically
distinct questions — you can coherently believe conflict is calming *and*
that OPEC+ cuts are coming — so collapsing them into one slider would lose
real information. **Expect this in the Q&A:** if asked "what if two views
on the same asset contradict each other?", the answer is that BL nets them
out by confidence rather than picking a winner, and the resulting tilt is
smaller than either view alone would produce.

### Preset scenarios

Eight one-click presets, each setting all eight sliders to a coherent
narrative, and each shipping with a written explanation of why every
slider sits where it does:

| Preset | Narrative |
|---|---|
| \U0001F54A️ Peace Breaks Out | Conflicts wind down, inflation cools, growth holds |
| ⚔️ Conflict Escalates | Geopolitical shock: energy spikes, capital runs to safety |
| \U0001F525 Sticky Inflation | Stagflation — inflation persists, Fed boxed in |
| \U0001F680 Soft Landing Rally | Goldilocks — inflation beaten without recession |
| \U0001F9CA Hard Landing | Deflationary bust, aggressive cuts, duration wins |
| \U0001F6A2 Trade War | Tariffs escalate, supply chains fracture, EM hit hardest |
| \U0001F4B1 Dollar Doubt | De-dollarization — gold and EM benefit |
| \U0001F610 No View (Neutral) | Control case: pure equilibrium = equal weight |

These double as **demo-day scripts**. "Hard Landing" pushes Treasuries to
the 40% cap; "Trade War" pushes the dollar to the cap and EM to its floor;
"Dollar Doubt" zeroes the dollar out entirely. Picking two contrasting
presets live is a much stronger demo than dragging sliders one at a time.

**Original event-market research.** The team's initial research (via
Perplexity, sourcing live Polymarket/Kalshi-style contracts as of August
2026) explored a richer multi-asset mapping per event — e.g. an Iran/Egypt
escalation question tilting oil, gold, the dollar, *and* defense stocks
(ITA) simultaneously, with separate "reduce" and "increase" basket lists.
**MacroTilt v1 simplifies this to one view = one primary asset**, for two
reasons: (1) it keeps the Black-Litterman view specification (P, Q, Omega
matrices) simple enough for every team member to trace by hand, which
matters for the live Q&A; (2) multi-asset relative views are a legitimate
v2 extension, not a requirement — see §7.

---

## 5. Method: Black-Litterman (the "portfolio construction method your team can defend")

Plain-English version (also in the app's "How This Works" tab):

1. **Neutral baseline.** Reverse-optimize: what expected returns would
   make the *equal-weight* portfolio the mathematically optimal one, given
   the assets' historical risk and correlations? That's the Black-Litterman
   "prior" (`pi = delta * Sigma @ w_equal`). No opinion is baked in.
2. **Your views.** Each slider is a statement like "I think XLE's expected
   return should be nudged by up to ~6 percentage points annualized,
   relative to that neutral baseline," with strength proportional to
   distance from neutral.
3. **Blend.** The Black-Litterman posterior formula combines the neutral
   baseline and your views, weighted by stated confidence.
4. **Re-optimize.** The blended expected returns feed a long-only,
   max-Sharpe mean-variance optimizer, capped at 40% per asset.
5. **Compare.** Against equal-weight (rubric-required) and 100% SPY (the
   product's own "boring baseline" pitch).

**Why Black-Litterman specifically, and not just a rules table (`if
view==yes: allocate 35% oil`).** A hard-coded allocation table (like the
one in the team's original Perplexity research) is easy to build but hard
to defend quantitatively — "why 35%, why not 30%?" has no principled
answer. Black-Litterman gives every tilt a mathematical justification tied
to the actual historical covariance structure of the specific six assets
chosen, and it degrades gracefully: a small view produces a small tilt, a
strong view produces a strong one, and no view produces no change at all.
That last property is provable and is exactly what the independent
verification check tests.

---

## 6. Scope decisions made under the 2-day deadline

| Considered | Decision | Why |
|---|---|---|
| Live Polymarket/Kalshi API for odds | **Cut.** Sliders are user-input only. | New auth/API surface, external dependency, doesn't change core defensibility of the method. Good stretch goal, not core. |
| LLM-generated narrative recommendation | **Cut** in favor of a deterministic, rule-based narrative. | The rubric gives an LLM feature *no credit for existing* — it has to demonstrably improve usefulness. A deterministic narrative is fully explainable in Q&A; an LLM-generated one adds a failure mode (hallucinated claims) for a 2-day build. Reconsider as a stretch goal only if time allows and you can bound its outputs. |
| Multi-asset views (one event → several assets) | **Simplified** to one view = one asset. | Keeps the view-specification matrices small enough for every teammate to trace by hand. |
| Futures-based oil ETF (USO/BNO) | **Cut** in favor of XLE (equity-based). | Roll-yield decay distorts long-horizon backtests; disclosed as a proxy tradeoff instead. |

---

## 7. Stretch goals (only if time remains after the core is solid)

- Live Kalshi public API pull as a *suggested default* for each slider
  (Kalshi's API doesn't require paid auth for public market data) — keep
  the user's manual override as the actual input to the model.
  Requires validating Kalshi's real rate limits/auth flow before demo day.
- Multi-asset views (relative views: "energy outperforms EM by X%").
- Calibrate `tilt_scale` per view from an actual historical event-study
  (e.g., measure XLE's realized move in the 30 days after past Middle
  East escalation headlines) instead of a disclosed flat assumption.
- Optional LLM feature: a bounded, template-constrained summary that can
  only reference numbers already computed by the app (never free-generate
  a return forecast) — satisfies "avoid unsupported financial claims."

**Do not add these under time pressure if it risks the core app breaking
before Thursday.** A smaller, fully-working, fully-understood app beats a
bigger one nobody on the team can defend — this is stated explicitly in
the syllabus rubric.

---

## 7b. App structure (what the grader actually clicks through)

Eight pages, routed by `app.py` via `st.navigation`. The macro sliders live
in the sidebar and render on every page, so state follows the user around.

| Page | Purpose in the demo |
|---|---|
| 🏠 Overview | The pitch + live market pulse. **Open here.** |
| 🎯 Build Portfolio | The core answer: allocation in % and $. **Spend most of the demo here.** |
| 📈 Performance | Growth, drawdown, rolling stability — the backtest evidence |
| 🚨 Stress Tests | 2008 / COVID / 2022 / 2023, plus a day-by-day walk through one |
| 🔬 Scenario Lab | All 8 narratives compared — **the single most impressive screen** |
| 🔍 Asset Explorer | The raw inputs, for anyone who wants to audit them |
| 🧮 Methodology | Black-Litterman explained + the formulae, for the Q&A |
| 📄 Data & Sources | Provenance and limitations, for the "is this honest?" question |

**Suggested 10-minute demo path:** Overview (30s, the pitch) → sidebar, hit
*Conflict Escalates* (1 min, watch the allocation move) → Build Portfolio
(3 min, the recommendation and dollar sizing) → Stress Tests (2 min, how it
held up in 2008 and COVID) → Scenario Lab (2 min, the comparison) →
Methodology (1 min, why Black-Litterman and not a lookup table). Do not click
through every page.

### Code architecture (for the "code quality" 20%)

```
app.py            routing only
views/*.py        one file per page, presentation only
macrotilt_ui.py   shared theme, sidebar, cached data, chart styling
engine.py         all financial maths — imports no Streamlit
```

`engine.py` importing no Streamlit is the point: it makes every calculation
testable headlessly, which is exactly what `verify_calculations.py`,
`test_pages.py` and `test_interactions.py` do.

---

## 8. Deliverables checklist (mapped from `Final_Project_Python.pdf`)

- [x] Working Streamlit app, deployable to Streamlit Community Cloud
- [x] ≥4 instruments (six: SPY, EEM, TLT, GLD, XLE, UUP)
- [x] Real external data with provenance (yfinance, documented in README)
- [x] Return/risk/correlation analysis + a defensible construction method
      (Black-Litterman)
- [x] Comparison against equal-weight
- [x] Independent verification of an important calculation
      (`verify_calculations.py`, two checks)
- [x] Meaningful interaction (8 macro sliders + 8 preset scenarios + tau
      slider + portfolio-value input, persisting across all 8 pages)
- [x] Clear investor-facing narrative + visuals (validated colour system,
      direct labels, table views alongside every chart)
- [x] Code quality: 4-layer separation, no Streamlit import in `engine.py`,
      3 runnable test scripts
- [ ] **Team to do:** deploy to Streamlit Community Cloud, paste URL into
      README + presentation PDF
- [ ] **Team to do:** fill in AI-Use Disclosure names + manual spot-check
- [ ] **Team to do:** build the presentation PDF (`Group_X.pdf`) — this
      brief's §1 and §5 are close to slide-ready
- [ ] **Team to do:** rehearse the live demo — walk through one concrete
      investor scenario (e.g. "I think the Middle East de-escalates,
      recession risk is low, and the Fed keeps cutting — show me the
      allocation") rather than clicking through every tab
