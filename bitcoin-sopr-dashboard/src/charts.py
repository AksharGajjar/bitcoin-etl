#!/usr/bin/env python3
"""
Plotly chart builders for SOPR analytics.

Provides functions to create interactive visualizations for the dashboard.
"""

import sys
from pathlib import Path
from typing import Optional

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
import config


def create_sopr_chart(
    sopr_df: pd.DataFrame,
    prices_df: Optional[pd.DataFrame] = None,
    show_price_overlay: bool = False
) -> go.Figure:
    """
    Create an interactive SOPR line chart with threshold indicator.

    Args:
        sopr_df: DataFrame with columns: date, sopr
        prices_df: Optional DataFrame with columns: date, price (for overlay)
        show_price_overlay: If True, show BTC price on secondary y-axis

    Returns:
        Plotly Figure object ready for display
    """
    # Ensure date column is datetime
    sopr_df = sopr_df.copy()
    sopr_df['date'] = pd.to_datetime(sopr_df['date'])
    sopr_df = sopr_df.sort_values('date')

    # Create figure with secondary y-axis if price overlay requested
    if show_price_overlay and prices_df is not None:
        fig = make_subplots(specs=[[{"secondary_y": True}]])
    else:
        fig = go.Figure()

    # Color points based on SOPR value (green above 1.0, red below)
    colors = [
        '#10B981' if sopr >= config.SOPR_THRESHOLD else '#EF4444'
        for sopr in sopr_df['sopr']
    ]

    # Add SOPR line trace
    trace_kwargs = dict(
        x=sopr_df['date'],
        y=sopr_df['sopr'],
        mode='lines+markers',
        name='SOPR',
        line=dict(color='#3B82F6', width=2.5),
        marker=dict(
            color=colors,
            size=7,
            line=dict(width=0)
        ),
        hovertemplate='<b>%{x|%b %d, %Y}</b><br>SOPR: %{y:.4f}<extra></extra>'
    )

    if show_price_overlay and prices_df is not None:
        fig.add_trace(go.Scatter(**trace_kwargs), secondary_y=False)
    else:
        fig.add_trace(go.Scatter(**trace_kwargs))

    # Add subtle threshold line at SOPR = 1.0
    fig.add_hline(
        y=config.SOPR_THRESHOLD,
        line_dash="dot",
        line_color="rgba(251, 191, 36, 0.6)",
        line_width=1.5,
        annotation_text="1.0",
        annotation_position="left",
        annotation_font_size=10,
        annotation_font_color="rgba(251, 191, 36, 0.8)"
    )

    # Add price overlay if requested
    if show_price_overlay and prices_df is not None:
        prices_df = prices_df.copy()
        prices_df['date'] = pd.to_datetime(prices_df['date'])
        prices_df = prices_df.sort_values('date')

        fig.add_trace(
            go.Scatter(
                x=prices_df['date'],
                y=prices_df['price'],
                mode='lines',
                name='BTC Price',
                line=dict(color='#F59E0B', width=1.5),
                opacity=0.8,
                hovertemplate='<b>%{x|%b %d, %Y}</b><br>$%{y:,.0f}<extra></extra>'
            ),
            secondary_y=True
        )

        # Update y-axis for dual axis
        fig.update_yaxes(
            title_text=None,
            showgrid=False,
            zeroline=False,
            secondary_y=True,
            tickformat='$,.0f',
            tickfont=dict(color='#F59E0B', size=10)
        )

    # Update layout - clean, minimal dark theme
    fig.update_layout(
        title=None,  # Remove title (we have section header)
        xaxis_title=None,
        yaxis_title=None,
        hovermode='x unified',
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            bgcolor='rgba(0,0,0,0)',
            font=dict(size=11)
        ),
        margin=dict(l=50, r=20, t=30, b=40),
        height=400
    )

    # Clean x-axis
    fig.update_xaxes(
        tickformat='%b %d',
        tickangle=0,
        showgrid=False,
        showline=True,
        linewidth=1,
        linecolor='rgba(255,255,255,0.1)',
        tickfont=dict(size=10),
        dtick='D7'  # Weekly ticks
    )

    # Clean y-axis
    yaxis_config = dict(
        showgrid=True,
        gridwidth=1,
        gridcolor='rgba(255,255,255,0.05)',
        showline=False,
        zeroline=False,
        tickfont=dict(size=10),
        tickformat='.2f'
    )

    if show_price_overlay and prices_df is not None:
        fig.update_yaxes(**yaxis_config, secondary_y=False)
    else:
        fig.update_yaxes(**yaxis_config)

    return fig


def create_metrics_cards(
    current_sopr: float,
    avg_sopr: float,
    current_price: float,
    price_change_pct: Optional[float] = None
) -> dict:
    """
    Generate metric values and labels for dashboard display.

    Args:
        current_sopr: Most recent SOPR value
        avg_sopr: Average SOPR over the selected period
        current_price: Current BTC price in USD
        price_change_pct: Optional price change percentage

    Returns:
        Dictionary with metric labels and values for Streamlit metrics
    """
    # Determine SOPR sentiment
    if current_sopr >= config.SOPR_THRESHOLD:
        sopr_sentiment = config.SOPR_GREED_LABEL
        sopr_delta_color = "normal"
    else:
        sopr_sentiment = config.SOPR_FEAR_LABEL
        sopr_delta_color = "inverse"

    return {
        'current_sopr': {
            'label': 'Current SOPR',
            'value': f"{current_sopr:.4f}",
            'delta': sopr_sentiment,
            'delta_color': sopr_delta_color
        },
        'avg_sopr': {
            'label': 'Period Average',
            'value': f"{avg_sopr:.4f}",
            'delta': None
        },
        'current_price': {
            'label': 'BTC Price',
            'value': f"${current_price:,.2f}",
            'delta': f"{price_change_pct:+.2f}%" if price_change_pct else None
        }
    }
