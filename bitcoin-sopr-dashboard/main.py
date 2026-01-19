#!/usr/bin/env python3
"""
Bitcoin SOPR Analytics Dashboard

Interactive Streamlit dashboard for analyzing Bitcoin's Spent Output Profit Ratio.
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

import streamlit as st
import pandas as pd

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
import config

from src.queries import query_sopr, query_prices
from src.charts import create_sopr_chart, create_metrics_cards

# =============================================================================
# Page Configuration
# =============================================================================

st.set_page_config(
    page_title="Bitcoin SOPR Dashboard",
    page_icon="₿",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for professional styling
st.markdown("""
<style>
    /* Sidebar header */
    .sidebar-title {
        font-size: 1.5rem;
        font-weight: 700;
        color: #F7931A;
        padding: 0.5rem 0;
        margin-bottom: 1rem;
        border-bottom: 2px solid #F7931A;
    }

    /* Sidebar section headers */
    .sidebar-section {
        font-size: 0.85rem;
        font-weight: 600;
        color: #888;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin: 1.5rem 0 0.5rem 0;
        padding-bottom: 0.25rem;
        border-bottom: 1px solid #333;
    }

    /* Main header styling */
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        background: linear-gradient(90deg, #F7931A, #FFD700);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin-bottom: 0;
    }

    .sub-header {
        font-size: 1rem;
        color: #888;
        margin-top: 0;
        margin-bottom: 1.5rem;
    }

    /* Metric card styling */
    [data-testid="stMetricValue"] {
        font-size: 1.6rem;
    }

    [data-testid="stMetricLabel"] {
        font-size: 0.9rem;
    }

    /* Section headers in main area */
    .section-header {
        font-size: 1.2rem;
        font-weight: 600;
        color: #F7931A;
        margin: 1rem 0;
    }

    /* Button styling */
    .stDownloadButton > button {
        width: 100%;
        border: 1px solid #F7931A;
    }

    .stDownloadButton > button:hover {
        border-color: #FFD700;
        color: #FFD700;
    }

    /* Footer */
    .footer {
        text-align: center;
        color: #666;
        font-size: 0.75rem;
        margin-top: 3rem;
        padding: 1rem 0;
        border-top: 1px solid #333;
    }

    /* Hide default sidebar decoration */
    [data-testid="stSidebarNav"] {
        display: none;
    }

    /* Improve expander styling */
    .streamlit-expanderHeader {
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)


# =============================================================================
# Cached Data Fetching (for speed)
# =============================================================================

@st.cache_data(ttl=config.CACHE_TTL_SECONDS, show_spinner=False)
def fetch_sopr_data(start_date: str, end_date: str, use_sample: bool) -> pd.DataFrame:
    """Cached SOPR data fetch."""
    return query_sopr(start_date, end_date, use_sample)


@st.cache_data(ttl=config.CACHE_TTL_SECONDS, show_spinner=False)
def fetch_price_data(start_date: str, end_date: str, use_sample: bool) -> pd.DataFrame:
    """Cached price data fetch."""
    return query_prices(start_date, end_date, use_sample)


# =============================================================================
# Sidebar Controls
# =============================================================================

with st.sidebar:
    # Sidebar branding
    st.markdown('<div class="sidebar-title">₿ SOPR Analytics</div>', unsafe_allow_html=True)

    # --- DATA SOURCE SECTION ---
    st.markdown('<div class="sidebar-section">Data Source</div>', unsafe_allow_html=True)

    use_sample_sopr = st.toggle(
        "Use Sample SOPR",
        value=True,
        help="ON = Demo SOPR data | OFF = Query BigQuery (requires UTXO index)"
    )

    if use_sample_sopr:
        st.info("SOPR: Sample data", icon="📊")
    else:
        st.warning("SOPR: BigQuery", icon="💰")

    st.caption("Price data always from BigQuery")

    # --- DATE RANGE SECTION ---
    st.markdown('<div class="sidebar-section">Date Range</div>', unsafe_allow_html=True)

    # Quick select buttons in a cleaner grid
    st.caption("Quick Select:")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("7D", use_container_width=True, help="Last 7 days"):
            st.session_state.lookback_days = 7
        if st.button("90D", use_container_width=True, help="Last 90 days"):
            st.session_state.lookback_days = 90
    with col2:
        if st.button("30D", use_container_width=True, help="Last 30 days"):
            st.session_state.lookback_days = 30
        if st.button("1Y", use_container_width=True, help="Last year"):
            st.session_state.lookback_days = 365

    # Initialize lookback days in session state
    if 'lookback_days' not in st.session_state:
        st.session_state.lookback_days = config.DEFAULT_LOOKBACK_DAYS

    # Date pickers with labels
    default_end = datetime.now().date()
    default_start = default_end - timedelta(days=st.session_state.lookback_days)

    st.caption("Custom Range:")
    start_date = st.date_input(
        "From",
        value=default_start,
        max_value=default_end,
        label_visibility="visible"
    )

    end_date = st.date_input(
        "To",
        value=default_end,
        min_value=start_date,
        max_value=default_end,
        label_visibility="visible"
    )

    # --- CHART OPTIONS SECTION ---
    st.markdown('<div class="sidebar-section">Chart Options</div>', unsafe_allow_html=True)

    show_price_overlay = st.checkbox(
        "Show BTC Price",
        value=False,
        help="Overlay Bitcoin price on secondary Y-axis"
    )

    # --- ACTIONS SECTION ---
    st.markdown('<div class="sidebar-section">Actions</div>', unsafe_allow_html=True)

    if st.button("🔄 Refresh Data", use_container_width=True, type="primary"):
        st.cache_data.clear()
        st.rerun()

    # --- ABOUT SECTION ---
    st.markdown('<div class="sidebar-section">About</div>', unsafe_allow_html=True)
    st.caption(
        "SOPR measures if Bitcoin holders are selling at profit or loss. "
        "Values above 1.0 indicate profit-taking; below 1.0 indicates capitulation."
    )


# =============================================================================
# Main Content Area
# =============================================================================

# Header
st.markdown('<p class="main-header">₿ Bitcoin SOPR Dashboard</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Spent Output Profit Ratio — On-Chain Market Sentiment</p>', unsafe_allow_html=True)

# Convert dates to strings
start_str = start_date.strftime('%Y-%m-%d')
end_str = end_date.strftime('%Y-%m-%d')

# Fetch data with loading indicator
with st.spinner("Loading data..."):
    try:
        # SOPR uses sample toggle; prices always from BigQuery
        sopr_df = fetch_sopr_data(start_str, end_str, use_sample_sopr)
        prices_df = fetch_price_data(start_str, end_str, use_sample=False)
        data_loaded = True
    except Exception as e:
        st.error(f"Failed to load data: {str(e)}")
        data_loaded = False

if data_loaded and not sopr_df.empty:
    # -------------------------------------------------------------------------
    # Metrics Row
    # -------------------------------------------------------------------------

    # Calculate metrics
    current_sopr = sopr_df['sopr'].iloc[0] if len(sopr_df) > 0 else 0
    avg_sopr = sopr_df['sopr'].mean()

    if not prices_df.empty and 'price' in prices_df.columns:
        current_price = prices_df['price'].iloc[0]
        if len(prices_df) > 1:
            price_change = ((prices_df['price'].iloc[0] / prices_df['price'].iloc[-1]) - 1) * 100
        else:
            price_change = 0
    else:
        current_price = 0
        price_change = 0

    # Display metrics in styled cards
    st.markdown('<div class="section-header">📈 Key Metrics</div>', unsafe_allow_html=True)

    metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)

    with metric_col1:
        sopr_delta = "Above break-even" if current_sopr >= 1.0 else "Below break-even"
        st.metric(
            label="Current SOPR",
            value=f"{current_sopr:.4f}",
            delta=sopr_delta,
            delta_color="normal" if current_sopr >= 1.0 else "inverse"
        )

    with metric_col2:
        st.metric(
            label="Period Average",
            value=f"{avg_sopr:.4f}",
            delta=f"{((current_sopr / avg_sopr) - 1) * 100:+.1f}% vs avg" if avg_sopr > 0 else None
        )

    with metric_col3:
        st.metric(
            label="BTC Price",
            value=f"${current_price:,.0f}",
            delta=f"{price_change:+.1f}%" if price_change != 0 else None
        )

    with metric_col4:
        # Market sentiment indicator
        if current_sopr >= 1.05:
            sentiment = "🟢 Profit Taking"
            sentiment_desc = "Holders selling at profit"
        elif current_sopr >= 1.0:
            sentiment = "🟡 Neutral"
            sentiment_desc = "Near break-even"
        elif current_sopr >= 0.95:
            sentiment = "🟠 Mild Fear"
            sentiment_desc = "Some selling at loss"
        else:
            sentiment = "🔴 Capitulation"
            sentiment_desc = "Heavy loss realization"

        st.metric(
            label="Market Sentiment",
            value=sentiment,
            delta=sentiment_desc,
            delta_color="off"
        )

    st.divider()

    # -------------------------------------------------------------------------
    # SOPR Chart
    # -------------------------------------------------------------------------

    st.markdown('<div class="section-header">📊 SOPR Over Time</div>', unsafe_allow_html=True)

    # Create and display chart
    fig = create_sopr_chart(
        sopr_df,
        prices_df if show_price_overlay else None,
        show_price_overlay=show_price_overlay
    )

    st.plotly_chart(fig, use_container_width=True, config={
        'displayModeBar': True,
        'displaylogo': False,
        'modeBarButtonsToRemove': ['lasso2d', 'select2d']
    })

    # -------------------------------------------------------------------------
    # SOPR Interpretation Guide
    # -------------------------------------------------------------------------

    with st.expander("ℹ️ How to Interpret SOPR", expanded=False):
        col_left, col_right = st.columns(2)

        with col_left:
            st.markdown("""
            **What is SOPR?**

            SOPR (Spent Output Profit Ratio) compares the price at which
            Bitcoin was bought vs. sold. It reveals market psychology.

            | Value | Meaning |
            |-------|---------|
            | **> 1.0** | Profit realization |
            | **= 1.0** | Break-even |
            | **< 1.0** | Loss realization |
            """)

        with col_right:
            st.markdown("""
            **Trading Signals**

            - 📈 **Rising SOPR**: Increasing profit-taking, watch for local tops
            - 📉 **Falling SOPR**: Growing capitulation, potential bottoms
            - 🔄 **Bounces off 1.0**: Strong psychological support level
            - ⚠️ **Extreme values**: Often mark trend reversals
            """)

    st.divider()

    # -------------------------------------------------------------------------
    # Raw Data & Export
    # -------------------------------------------------------------------------

    st.markdown('<div class="section-header">📋 Export Data</div>', unsafe_allow_html=True)

    export_col1, export_col2, export_col3 = st.columns([1, 1, 2])

    # Prepare export data
    export_df = sopr_df.copy()
    export_df['date'] = pd.to_datetime(export_df['date']).dt.strftime('%Y-%m-%d')

    with export_col1:
        csv_data = export_df.to_csv(index=False)
        st.download_button(
            label="📥 CSV",
            data=csv_data,
            file_name=f"sopr_{start_str}_{end_str}.csv",
            mime="text/csv",
            use_container_width=True
        )

    with export_col2:
        json_data = export_df.to_json(orient='records', date_format='iso')
        st.download_button(
            label="📥 JSON",
            data=json_data,
            file_name=f"sopr_{start_str}_{end_str}.json",
            mime="application/json",
            use_container_width=True
        )

    # Raw data expander
    with st.expander(f"🔍 View Raw Data ({len(sopr_df)} records)"):
        st.dataframe(
            sopr_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "date": st.column_config.DateColumn("Date", format="YYYY-MM-DD"),
                "sopr": st.column_config.NumberColumn("SOPR", format="%.4f")
            }
        )

elif data_loaded and sopr_df.empty:
    st.warning("No data available for the selected date range. Try adjusting the dates or enabling sample data.")

# =============================================================================
# Footer
# =============================================================================

st.markdown("""
<div class="footer">
    Bitcoin SOPR Dashboard · Data: BigQuery Public Bitcoin Ledger · Built with Streamlit + Plotly<br>
    <span style="color: #F7931A;">₿</span> On-chain analytics for informed decisions
</div>
""", unsafe_allow_html=True)
