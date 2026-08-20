"""
macrotilt_ui.py — shared presentation layer
--------------------------------------------
Everything the multi-page app needs in common: the dark theme, the sidebar
questionnaire, cached data loading, and Plotly styling helpers.

Why this module exists: with seven pages, the macro sliders have to appear
and behave identically everywhere, and every chart has to share one visual
system. Putting that in one importable module means a page file contains
only what makes that page different.

Design note: `engine.py` still knows nothing about Streamlit. This module is
the only place the two worlds meet.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import engine

# ---------------------------------------------------------------------------
# Preset scenarios
# ---------------------------------------------------------------------------
# Each preset is a coherent macro narrative -- a set of views a real investor
# might hold together -- plus a plain-English explanation of why each slider
# sits where it does. The explanation matters: a preset the user cannot
# interrogate is just a magic button.
# ---------------------------------------------------------------------------

PRESET_SCENARIOS = {
    "Peace Breaks Out": {
        "icon": "\U0001F54A️",
        "summary": "Conflicts wind down, inflation cools, growth holds up.",
        "detail": (
            "The optimistic case. Middle East tensions resolve and supply lines normalise, "
            "so the geopolitical premium in energy deflates. With inflation cooling, the Fed "
            "has room to keep cutting, and growth avoids a hard stop — a supportive backdrop "
            "for risk assets and a mild headwind for the safe-haven dollar."
        ),
        "scores": {
            "mideast_deescalation": 9, "supply_disruption": 2, "trade_tensions": 3,
            "fed_cuts": 7, "dollar_strength": 3,
            "recession_risk": 2, "inflation_persistence": 2, "em_growth": 7,
        },
    },
    "Conflict Escalates": {
        "icon": "⚔️",
        "summary": "Geopolitical shock: energy spikes, capital runs to safety.",
        "detail": (
            "The tail-risk case. Regional conflict widens and shipping lanes are threatened, "
            "pushing crude and energy equities higher. Capital flees to the dollar and gold, "
            "trade routes get disrupted, and the growth outlook deteriorates as an energy price "
            "shock feeds through to the real economy."
        ),
        "scores": {
            "mideast_deescalation": 1, "supply_disruption": 9, "trade_tensions": 7,
            "fed_cuts": 6, "dollar_strength": 8,
            "recession_risk": 7, "inflation_persistence": 7, "em_growth": 2,
        },
    },
    "Sticky Inflation": {
        "icon": "\U0001F525",
        "summary": "Inflation won't die, the Fed can't cut, growth stalls.",
        "detail": (
            "The stagflation case — the hardest regime for a traditional 60/40. Inflation stays "
            "above target, so the Fed is boxed in and cuts fewer times than markets hope. Real "
            "assets like gold and energy hold value while both stocks and long bonds struggle, "
            "and a high-rate dollar stays firm."
        ),
        "scores": {
            "mideast_deescalation": 4, "supply_disruption": 6, "trade_tensions": 6,
            "fed_cuts": 1, "dollar_strength": 7,
            "recession_risk": 7, "inflation_persistence": 9, "em_growth": 3,
        },
    },
    "Soft Landing Rally": {
        "icon": "\U0001F680",
        "summary": "Inflation beaten without a recession — risk assets rip.",
        "detail": (
            "The goldilocks case. Inflation returns to target without breaking the labour market, "
            "so the Fed cuts into a still-growing economy. Risk appetite broadens out beyond US "
            "large caps into emerging markets, the safe-haven dollar bid fades, and defensive "
            "hedges underperform."
        ),
        "scores": {
            "mideast_deescalation": 7, "supply_disruption": 3, "trade_tensions": 3,
            "fed_cuts": 8, "dollar_strength": 2,
            "recession_risk": 1, "inflation_persistence": 2, "em_growth": 8,
        },
    },
    "Hard Landing": {
        "icon": "\U0001F9CA",
        "summary": "Recession hits, the Fed slashes rates, duration wins.",
        "detail": (
            "The deflationary bust case. Growth rolls over decisively, forcing the Fed into "
            "aggressive cuts — the single best environment for long-duration Treasuries. "
            "Earnings contract, demand destruction pulls energy down with it, and the dollar "
            "catches a defensive bid as global growth disappoints."
        ),
        "scores": {
            "mideast_deescalation": 5, "supply_disruption": 3, "trade_tensions": 5,
            "fed_cuts": 9, "dollar_strength": 7,
            "recession_risk": 9, "inflation_persistence": 2, "em_growth": 2,
        },
    },
    "Trade War": {
        "icon": "\U0001F6A2",
        "summary": "Tariffs escalate, supply chains fracture, EM takes the hit.",
        "detail": (
            "The fragmentation case. Tariff escalation between major economies hits "
            "export-driven emerging markets hardest while re-routing supply chains raises "
            "costs everywhere. Inflation is stickier than it would otherwise be, growth is "
            "slower, and the dollar benefits from both safe-haven demand and relative US insulation."
        ),
        "scores": {
            "mideast_deescalation": 5, "supply_disruption": 6, "trade_tensions": 9,
            "fed_cuts": 4, "dollar_strength": 8,
            "recession_risk": 6, "inflation_persistence": 7, "em_growth": 1,
        },
    },
    "Dollar Doubt": {
        "icon": "\U0001F4B1",
        "summary": "Confidence in the dollar erodes — gold and EM benefit.",
        "detail": (
            "The de-dollarisation case. Fiscal concerns and reserve diversification weigh on the "
            "dollar. Gold is the primary beneficiary as a non-sovereign store of value, and a "
            "weaker dollar mechanically eases financial conditions for emerging markets, which "
            "borrow and trade heavily in USD."
        ),
        "scores": {
            "mideast_deescalation": 5, "supply_disruption": 5, "trade_tensions": 5,
            "fed_cuts": 7, "dollar_strength": 1,
            "recession_risk": 4, "inflation_persistence": 7, "em_growth": 7,
        },
    },
    "No View (Neutral)": {
        "icon": "\U0001F610",
        "summary": "Reset every slider — see the pure equilibrium baseline.",
        "detail": (
            "Every slider at 5 means you are expressing no opinion at all. The model falls back to "
            "the historical-equilibrium allocation, which is mathematically identical to equal "
            "weight. This is the control case, and it is checked as a hard identity in "
            "verify_calculations.py — if this ever stopped equalling equal weight, something in "
            "the model is broken."
        ),
        "scores": {cfg["key"]: 5 for cfg in engine.VIEWS_CONFIG},
    },
}


# ---------------------------------------------------------------------------
# Theme
# ---------------------------------------------------------------------------

_CSS = f"""
<style>
/* ---------- Global surfaces ---------- */
.stApp {{ background: {engine.COLOR_PAGE_BG}; }}
.block-container {{ padding-top: 2.4rem; padding-bottom: 4rem; max-width: 1480px; }}
[data-testid="stHeader"] {{ background: transparent; }}
#MainMenu, footer {{ visibility: hidden; }}

html, body, [class*="css"] {{ color: {engine.COLOR_TEXT}; }}
[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] li {{ color: {engine.COLOR_TEXT_DIM}; }}
[data-testid="stMarkdownContainer"] strong {{ color: {engine.COLOR_TEXT}; }}
h1, h2, h3, h4, h5 {{ color: {engine.COLOR_TEXT}; letter-spacing: -0.4px; }}

/* ---------- Hero ---------- */
.mt-hero {{
    background:
      radial-gradient(1200px 320px at 12% -40%, rgba(57,135,229,0.28), transparent 62%),
      linear-gradient(125deg, #101822 0%, #16202c 52%, #101822 100%);
    border: 1px solid {engine.COLOR_BORDER};
    border-radius: 18px;
    padding: 38px 42px 34px 42px;
    margin-bottom: 26px;
}}
.mt-hero h1 {{
    margin: 0 0 12px 0; font-size: 2.6rem; font-weight: 750;
    color: #ffffff; letter-spacing: -1.2px;
}}
.mt-hero .mt-tagline {{
    font-size: 1.14rem; font-weight: 620; color: #6fa8e8;
    margin-bottom: 16px; letter-spacing: 0.2px;
}}
.mt-hero .mt-copy {{
    font-size: 1.0rem; color: {engine.COLOR_TEXT_DIM};
    max-width: 900px; line-height: 1.68; margin: 0;
}}

/* ---------- Page headers ---------- */
.mt-eyebrow {{
    font-size: 0.74rem; font-weight: 800; color: #6fa8e8;
    text-transform: uppercase; letter-spacing: 1.6px; margin-bottom: 8px;
}}
.mt-page-title {{
    font-size: 2.0rem; font-weight: 730; color: {engine.COLOR_TEXT};
    letter-spacing: -0.9px; margin: 0 0 8px 0;
}}
.mt-page-sub {{
    font-size: 0.97rem; color: {engine.COLOR_TEXT_DIM};
    max-width: 900px; line-height: 1.6; margin: 0 0 26px 0;
}}
.mt-section {{
    font-size: 1.22rem; font-weight: 700; color: {engine.COLOR_TEXT};
    margin: 34px 0 6px 0; padding-bottom: 10px;
    border-bottom: 1px solid {engine.COLOR_BORDER};
}}
.mt-section-sub {{
    font-size: 0.9rem; color: {engine.COLOR_TEXT_MUTED};
    margin: 8px 0 18px 0; line-height: 1.55;
}}

/* ---------- KPI tiles ---------- */
[data-testid="stMetric"] {{
    background: {engine.COLOR_SURFACE};
    border: 1px solid {engine.COLOR_BORDER};
    border-radius: 14px;
    padding: 18px 20px 15px 20px;
    transition: border-color 140ms ease, transform 140ms ease;
}}
[data-testid="stMetric"]:hover {{
    border-color: #38506b; transform: translateY(-2px);
}}
[data-testid="stMetricLabel"] {{
    font-weight: 600; color: {engine.COLOR_TEXT_MUTED};
    font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.9px;
}}
[data-testid="stMetricValue"] {{
    font-size: 1.95rem; color: {engine.COLOR_TEXT}; letter-spacing: -1px;
}}

/* ---------- Cards ---------- */
.mt-card {{
    background: {engine.COLOR_SURFACE};
    border: 1px solid {engine.COLOR_BORDER};
    border-radius: 14px;
    padding: 20px 22px;
    margin-bottom: 14px;
}}
.mt-card-title {{
    font-size: 0.78rem; font-weight: 750; color: {engine.COLOR_TEXT_MUTED};
    text-transform: uppercase; letter-spacing: 1.1px; margin-bottom: 12px;
}}

/* ---------- Market pulse strip ---------- */
.mt-pulse {{
    display: flex; gap: 10px; flex-wrap: wrap; margin: 4px 0 8px 0;
}}
.mt-tick {{
    flex: 1 1 150px; background: {engine.COLOR_SURFACE};
    border: 1px solid {engine.COLOR_BORDER};
    border-radius: 12px; padding: 13px 15px;
    transition: border-color 140ms ease;
}}
.mt-tick:hover {{ border-color: #38506b; }}
.mt-tick-top {{ display: flex; align-items: center; gap: 7px; margin-bottom: 5px; }}
.mt-dot {{ width: 9px; height: 9px; border-radius: 50%; flex: 0 0 9px; }}
.mt-tick-sym {{ font-size: 0.92rem; font-weight: 750; color: {engine.COLOR_TEXT}; }}
.mt-tick-name {{ font-size: 0.71rem; color: {engine.COLOR_TEXT_MUTED}; margin-bottom: 7px; }}
.mt-tick-val {{ font-size: 1.24rem; font-weight: 700; letter-spacing: -0.5px; }}
.mt-tick-win {{ font-size: 0.68rem; color: {engine.COLOR_TEXT_MUTED}; margin-top: 2px; }}

/* ---------- Recommendation ---------- */
.mt-reco {{
    background: linear-gradient(135deg, rgba(57,135,229,0.10), rgba(57,135,229,0.03));
    border: 1px solid rgba(57,135,229,0.30);
    border-left: 4px solid #3987e5;
    border-radius: 14px;
    padding: 24px 28px; margin: 24px 0 10px 0;
    line-height: 1.78; font-size: 1.0rem; color: {engine.COLOR_TEXT_DIM};
}}
.mt-reco b {{ color: {engine.COLOR_TEXT}; }}
.mt-reco-head {{
    font-weight: 780; font-size: 0.76rem; color: #6fa8e8;
    text-transform: uppercase; letter-spacing: 1.4px;
    display: block; margin-bottom: 10px;
}}

/* ---------- Badges / pills ---------- */
.mt-badge {{
    display: inline-block; background: rgba(57,135,229,0.14); color: #6fa8e8;
    border: 1px solid rgba(57,135,229,0.34);
    border-radius: 999px; padding: 5px 14px;
    font-size: 0.8rem; font-weight: 650; margin: 14px 0 6px 0;
}}
.mt-badge-neutral {{
    background: rgba(155,164,178,0.10); color: {engine.COLOR_TEXT_MUTED};
    border-color: {engine.COLOR_BORDER};
}}
.mt-chip {{
    display: inline-block; border-radius: 8px; padding: 4px 11px;
    font-size: 0.79rem; font-weight: 640; margin: 3px 5px 3px 0;
    background: rgba(57,135,229,0.12); color: #6fa8e8;
    border: 1px solid rgba(57,135,229,0.3);
}}

/* ---------- Sidebar ---------- */
section[data-testid="stSidebar"] {{
    background: #0d1218; border-right: 1px solid {engine.COLOR_BORDER};
}}
section[data-testid="stSidebar"] .block-container {{ padding-top: 1.2rem; }}
.mt-sb-title {{
    font-size: 1.06rem; font-weight: 760; color: {engine.COLOR_TEXT}; margin-bottom: 4px;
}}
.mt-sb-group {{
    font-size: 0.7rem; font-weight: 800; color: #6fa8e8;
    text-transform: uppercase; letter-spacing: 1.3px;
    margin: 22px 0 4px 0; padding-bottom: 7px;
    border-bottom: 1px solid {engine.COLOR_BORDER};
}}
section[data-testid="stSidebar"] [data-testid="stSlider"] {{ padding-top: 6px; }}
section[data-testid="stSidebar"] [data-testid="stSlider"] label {{
    font-size: 0.9rem; font-weight: 620; color: {engine.COLOR_TEXT};
}}
section[data-testid="stSidebar"] [data-testid="stCaptionContainer"] {{
    margin-top: -6px; margin-bottom: 12px;
}}
section[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p {{
    font-size: 0.73rem; color: {engine.COLOR_TEXT_MUTED};
}}
section[data-testid="stSidebar"] button {{
    font-size: 0.79rem !important; padding: 6px 8px !important;
    line-height: 1.25 !important; min-height: 48px;
    background: {engine.COLOR_SURFACE} !important;
    border: 1px solid {engine.COLOR_BORDER} !important;
    color: {engine.COLOR_TEXT_DIM} !important;
}}
section[data-testid="stSidebar"] button:hover {{
    border-color: #3987e5 !important; color: #ffffff !important;
}}

/* ---------- Tables ---------- */
[data-testid="stDataFrame"] {{ border-radius: 12px; overflow: hidden; }}

/* ---------- Tabs ---------- */
.stTabs [data-baseweb="tab-list"] {{ gap: 4px; border-bottom: 1px solid {engine.COLOR_BORDER}; }}
.stTabs [data-baseweb="tab"] {{
    height: 44px; padding: 0 18px; background: transparent;
    color: {engine.COLOR_TEXT_MUTED}; font-weight: 620; font-size: 0.9rem;
}}
.stTabs [aria-selected="true"] {{ color: #ffffff !important; }}

/* ---------- Expander ---------- */
[data-testid="stExpander"] {{
    border: 1px solid {engine.COLOR_BORDER}; border-radius: 12px;
    background: {engine.COLOR_SURFACE};
}}
</style>
"""


def boot(page_title: str, icon: str = "\U0001F30D") -> None:
    """Standard page setup: config + theme. Call first on every page."""
    st.set_page_config(
        page_title=f"{page_title} · MacroTilt",
        page_icon=icon,
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(_CSS, unsafe_allow_html=True)


def page_header(eyebrow: str, title: str, subtitle: str) -> None:
    st.markdown(
        f'<div class="mt-eyebrow">{eyebrow}</div>'
        f'<div class="mt-page-title">{title}</div>'
        f'<div class="mt-page-sub">{subtitle}</div>',
        unsafe_allow_html=True,
    )


def section(title: str, sub: str = "") -> None:
    html = f'<div class="mt-section">{title}</div>'
    if sub:
        html += f'<div class="mt-section-sub">{sub}</div>'
    st.markdown(html, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Data + model
# ---------------------------------------------------------------------------

@st.cache_data(ttl=60 * 60 * 12, show_spinner="Loading market data (SPY · XLE · EEM · GLD · TLT · UUP)…")
def load_market_data():
    """Cached price pull. Cached across pages, so navigation is instant and
    yfinance is hit once per session rather than once per page view.
    """
    prices = engine.load_prices()
    return prices, engine.daily_returns(prices)


def get_data():
    """Returns (prices, returns), or halts the page with a readable error."""
    try:
        return load_market_data()
    except RuntimeError as e:
        st.error(f"**Data load failed.** {e}")
        st.info(
            "This app pulls live data from Yahoo Finance at startup. If you are running "
            "behind a restrictive network, or Yahoo is rate-limiting, wait a minute and "
            "refresh the page."
        )
        st.stop()


def current_scores() -> dict[str, int]:
    """Slider values from session state, defaulting to neutral."""
    return {cfg["key"]: st.session_state.get(f"slider_{cfg['key']}", 5) for cfg in engine.VIEWS_CONFIG}


def current_tau() -> float:
    return st.session_state.get("tau", 0.05)


def run_model(returns: pd.DataFrame):
    """Run Black-Litterman with whatever the sliders currently say."""
    return engine.run_macrotilt(returns, current_scores(), tau=current_tau())


def portfolio_set(returns: pd.DataFrame, tilt_weights: dict) -> dict:
    """The three portfolios every page compares: the user's tilt, the
    required equal-weight baseline, and the 'boring' 100% SPY benchmark.
    """
    cols = list(returns.columns)
    return {
        "MacroTilt (your view)": tilt_weights,
        "Equal-Weight": engine.equal_weight(cols),
        "100% SPY": {t: (1.0 if t == "SPY" else 0.0) for t in cols},
    }


def metrics_frame(returns: pd.DataFrame, portfolios: dict) -> tuple[pd.DataFrame, dict]:
    rows, series = [], {}
    for name, w in portfolios.items():
        pr = engine.portfolio_returns(returns, w)
        series[name] = pr
        rows.append({
            "Portfolio": name,
            "Ann. Return": engine.annualized_return(pr),
            "Ann. Volatility": engine.annualized_vol(pr),
            "Sharpe": engine.sharpe_ratio(pr),
            "Max Drawdown": engine.max_drawdown(pr),
            "Tracking Error vs SPY": engine.tracking_error(pr, returns["SPY"]),
        })
    return pd.DataFrame(rows).set_index("Portfolio"), series


PORTFOLIO_COLORS = {
    "MacroTilt (your view)": "#3987e5",
    "Equal-Weight": engine.EQUAL_WEIGHT_COLOR,
    "100% SPY": engine.BENCHMARK_COLOR,
}


# ---------------------------------------------------------------------------
# Sidebar (shared across every page)
# ---------------------------------------------------------------------------

def render_sidebar() -> dict[str, int]:
    """Renders the macro questionnaire. Because widget keys are stable and
    Streamlit keeps session state across pages, moving a slider on any page
    updates every other page too.
    """
    sb = st.sidebar

    sb.markdown('<div class="mt-sb-title">\U0001F30D Your macro read</div>', unsafe_allow_html=True)
    sb.caption(
        "Rate each question 0–10. **5 = neutral**, meaning no view — leave it there and it "
        "will not move your portfolio at all. These sliders persist as you move between pages."
    )

    sb.markdown('<div class="mt-sb-group">Quick scenarios</div>', unsafe_allow_html=True)
    sb.caption("One click sets all eight sliders to a coherent macro narrative.")

    cols = sb.columns(2)
    for i, (name, preset) in enumerate(PRESET_SCENARIOS.items()):
        if cols[i % 2].button(f"{preset['icon']} {name}", width="stretch", key=f"preset_{i}"):
            for k, v in preset["scores"].items():
                st.session_state[f"slider_{k}"] = v
            st.session_state["last_preset"] = name

    with sb.expander("\U0001F4D6  What do these scenarios mean?"):
        for name, preset in PRESET_SCENARIOS.items():
            st.markdown(f"**{preset['icon']} {name}** — *{preset['summary']}*")
            st.caption(preset["detail"])

    scores = {}
    for category in engine.VIEW_CATEGORIES:
        sb.markdown(f'<div class="mt-sb-group">{category}</div>', unsafe_allow_html=True)
        for cfg in [c for c in engine.VIEWS_CONFIG if c["category"] == category]:
            key = f"slider_{cfg['key']}"
            if key not in st.session_state:
                st.session_state[key] = 5
            scores[cfg["key"]] = sb.slider(
                f"{cfg['icon']} {cfg['label']}",
                min_value=0, max_value=10, key=key,
                help=f"{cfg['question']}\n\n**Why it matters:** {cfg['rationale']}",
            )
            sb.caption(f"{cfg['low_caption']} · {cfg['high_caption']}")

    active = sum(1 for v in scores.values() if v != 5)
    cls = "mt-badge" if active else "mt-badge mt-badge-neutral"
    sb.markdown(
        f'<div class="{cls}">\U0001F4CD {active} of {len(scores)} views active</div>',
        unsafe_allow_html=True,
    )

    with sb.expander("⚙️  Advanced settings"):
        if "tau" not in st.session_state:
            st.session_state["tau"] = 0.05
        st.slider(
            "View conviction weight (τ)",
            min_value=0.01, max_value=0.20, step=0.01, key="tau",
            help="Black-Litterman tuning parameter: how much weight the model gives your "
                 "stated views versus the historical-equilibrium baseline.",
        )
        st.caption(
            "τ scales the uncertainty of the equilibrium prior. 0.05 is the conventional "
            "default in the literature; it is exposed here so you can see how sensitive "
            "the allocation is to that choice."
        )
        st.number_input(
            "Portfolio value (USD)", min_value=1_000, max_value=1_000_000_000,
            value=st.session_state.get("portfolio_value", 1_000_000), step=50_000,
            key="portfolio_value",
            help="Used only to translate percentage weights into dollar amounts.",
        )

    return scores


# ---------------------------------------------------------------------------
# Plotly styling
# ---------------------------------------------------------------------------

def style_fig(fig: go.Figure, height: int = 420, legend: bool = True, title: str = "") -> go.Figure:
    """One dark chart style for the whole app -- recessive grid and axes,
    generous margins, consistent hover treatment.
    """
    fig.update_layout(
        height=height,
        title=dict(text=title, font=dict(size=15, color=engine.COLOR_TEXT)) if title else None,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(
            family="system-ui, -apple-system, 'Segoe UI', sans-serif",
            color=engine.COLOR_TEXT_DIM, size=12,
        ),
        margin=dict(t=48 if title else 18, b=16, l=10, r=10),
        hoverlabel=dict(
            bgcolor=engine.COLOR_SURFACE_HI,
            bordercolor=engine.COLOR_BORDER,
            font=dict(color=engine.COLOR_TEXT, size=12),
        ),
        showlegend=legend,
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, x=0,
            bgcolor="rgba(0,0,0,0)", font=dict(size=11.5),
        ),
    )
    fig.update_xaxes(
        gridcolor=engine.COLOR_GRID, zeroline=False,
        linecolor=engine.COLOR_BORDER, tickfont=dict(color=engine.COLOR_TEXT_MUTED, size=11),
    )
    fig.update_yaxes(
        gridcolor=engine.COLOR_GRID, zeroline=False,
        linecolor=engine.COLOR_BORDER, tickfont=dict(color=engine.COLOR_TEXT_MUTED, size=11),
    )
    return fig


def market_pulse(prices: pd.DataFrame, window: str = "1D") -> None:
    """Live-ish market strip. Real trailing returns from the same price data
    the model uses -- decorative in placement, honest in content.

    Colour never carries the up/down meaning alone: every tile pairs its
    colour with a ▲/▼ glyph and a signed number.
    """
    perf = engine.recent_performance(prices)
    tiles = []
    for t in engine.CHART_ORDER:
        val = perf.loc[t, window]
        if pd.isna(val):
            colour, arrow, txt = engine.COLOR_TEXT_MUTED, "·", "n/a"
        else:
            up = val >= 0
            colour = engine.COLOR_UP if up else engine.COLOR_DOWN
            arrow = "▲" if up else "▼"
            txt = f"{val:+.2%}"
        short = engine.ASSET_LABELS[t].split(" (")[0]
        tiles.append(
            f'<div class="mt-tick">'
            f'  <div class="mt-tick-top">'
            f'    <span class="mt-dot" style="background:{engine.ASSET_COLORS[t]}"></span>'
            f'    <span class="mt-tick-sym">{t}</span>'
            f'  </div>'
            f'  <div class="mt-tick-name">{short}</div>'
            f'  <div class="mt-tick-val" style="color:{colour}">{arrow} {txt}</div>'
            f'  <div class="mt-tick-win">{window} change</div>'
            f'</div>'
        )
    st.markdown(f'<div class="mt-pulse">{"".join(tiles)}</div>', unsafe_allow_html=True)


def allocation_donut(weights: dict, height: int = 400) -> go.Figure:
    """Donut in fixed palette-slot order, so neighbouring slices are always a
    validated adjacent colour pair. Direct percentage labels and 2px surface
    gaps supply the secondary encoding the six-series case requires.
    """
    order = [t for t in engine.CHART_ORDER if t in weights]
    fig = go.Figure(go.Pie(
        labels=[engine.ASSET_LABELS[t] for t in order],
        values=[weights[t] for t in order],
        marker=dict(
            colors=[engine.ASSET_COLORS[t] for t in order],
            line=dict(color=engine.COLOR_SURFACE, width=2),
        ),
        hole=0.62, sort=False, direction="clockwise",
        textinfo="percent", textposition="outside",
        textfont=dict(color=engine.COLOR_TEXT_DIM, size=12),
        hovertemplate="%{label}<br>%{percent}<extra></extra>",
    ))
    top = max(weights, key=weights.get)
    fig.add_annotation(
        text=f"<b style='font-size:26px'>{weights[top]:.0%}</b><br>"
             f"<span style='font-size:11px;color:{engine.COLOR_TEXT_MUTED}'>{top} · largest</span>",
        x=0.5, y=0.5, showarrow=False, font=dict(color=engine.COLOR_TEXT),
    )
    style_fig(fig, height=height, legend=True)
    fig.update_layout(legend=dict(orientation="v", x=1.0, y=0.5, yanchor="middle"))
    return fig
