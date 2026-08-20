"""
MacroTilt — entry point
------------------------
Streamlit multi-page app for the IE NYC Python for Finance final project.

    streamlit run app.py

This file only wires up navigation. Each page lives in views/, shared
presentation logic lives in macrotilt_ui.py, and all financial mathematics
lives in engine.py (which imports no Streamlit and is independently tested
by verify_calculations.py).

The entry point is deliberately still called app.py so an existing
Streamlit Community Cloud deployment pointing at "app.py" keeps working
without touching its settings.

--------------------------------------------------------------------------
The product
--------------------------------------------------------------------------
Pitch: the 60/40 stock-bond portfolio was built for a world without a
geopolitical risk premium. The S&P 500 sits near all-time highs, bond
yields are near multi-decade highs, and "just buy the index" has no
mechanism at all for expressing what an investor actually believes about
the Middle East, the Fed, or the next recession.

Investor: a self-directed investor who thinks in macro/geopolitical terms
and wants a portfolio that reflects that view without hand-picking trades.

Decision: given a read on eight live macro questions, what allocation
across US equities / EM equities / Treasuries / gold / energy equities /
the dollar reflects that view — and how would it have behaved through real
historical stress events?
"""

import streamlit as st

PAGES = [
    st.Page("views/home.py", title="Overview", icon="\U0001F3E0", default=True),
    st.Page("views/build.py", title="Build Portfolio", icon="\U0001F3AF"),
    st.Page("views/performance.py", title="Performance", icon="\U0001F4C8"),
    st.Page("views/stress.py", title="Stress Tests", icon="\U0001F6A8"),
    st.Page("views/scenarios.py", title="Scenario Lab", icon="\U0001F52C"),
    st.Page("views/assets.py", title="Asset Explorer", icon="\U0001F50D"),
    st.Page("views/method.py", title="Methodology", icon="\U0001F9EE"),
    st.Page("views/data.py", title="Data & Sources", icon="\U0001F4C4"),
]

st.navigation(PAGES).run()
