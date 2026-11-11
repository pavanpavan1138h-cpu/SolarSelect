"""
SolarSelect — Energy Analysis Page
Displays Layer A specific yield predictions, annualization, and lifetime degradation profiles.
"""

import streamlit as st
import plotly.graph_objects as go
import numpy as np

from app.frontend.components.ui import (
    render_page_header,
    render_section_header,
    render_banner,
    render_empty_state,
    render_metric_card,
)
from app.backend.services import SolarSelectPlatformService


def render_energy_page(service: SolarSelectPlatformService) -> None:
    """Renders the Energy Analysis page."""
    render_page_header(
        title="Energy & Yield Analysis",
        subtitle="Site-specific daily yield predictions, annualization coverage, and 25-year degradation modeling",
        breadcrumb="SolarSelect Platform / Energy Analysis"
    )

    render_banner(
        message=(
            "Decision B-1 & B-2 Governance: Prospective unbuilt roofs lack empirical yield lag history "
            "and evaluate strictly to PREDICTION_PENDING_LAG_POLICY unless a valid historical replay "
            "or explicit scenario input is supplied. Historical observation spans 358 days (May 2021–Apr 2022)."
        ),
        variant="warning",
        title="Scientific Governance Notice"
    )

    # Preview Toggle for Visual Design Demonstration
    show_demo = st.checkbox(
        "Show Synthetic Layout Preview (DEMONSTRATION DATA ONLY — NOT A REAL SOLARSELECT PREDICTION)",
        value=False
    )

    if not show_demo:
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            render_metric_card(
                label="Specific Daily Yield",
                value="— kWh/kWp",
                caption="Phase 5 ML Estimate",
                badge_text="Pending Lag Policy",
                badge_variant="neutral"
            )
        with m2:
            render_metric_card(
                label="Year-1 Annual Energy",
                value="— kWh",
                caption="Observed or Scenario Basis",
                badge_text="Unverified Basis",
                badge_variant="warning"
            )
        with m3:
            render_metric_card(
                label="25-Yr Lifetime Baseline",
                value="— MWh",
                caption="Constant Performance",
                badge_text="Not Evaluated",
                badge_variant="neutral"
            )
        with m4:
            render_metric_card(
                label="Degraded 25-Yr Yield",
                value="— MWh",
                caption="Compounded Model",
                badge_text="Not Evaluated",
                badge_variant="neutral"
            )

        render_empty_state(
            title="Awaiting Scenario or Historical Replay Input",
            description=(
                "Real prospective roof configurations require an approved lag-feature substitution policy (Decision B-2) "
                "or historical UNISOLAR site replay selection. Toggle the demonstration preview above to inspect the visual layout."
            ),
            badge_text="B-2 Blocked / Empty State"
        )
    else:
        render_banner(
            message="The metrics and trajectory shown below use controlled synthetic demonstration data solely for UI layout preview.",
            variant="warning",
            title="DEMONSTRATION MODE ACTIVE"
        )

        m1, m2, m3, m4 = st.columns(4)
        with m1:
            render_metric_card(
                label="Demo Specific Yield",
                value="3.85 kWh/kWp",
                caption="Synthetic Demonstration",
                badge_text="Demo Value",
                badge_variant="neutral"
            )
        with m2:
            render_metric_card(
                label="Demo Year-1 Energy",
                value="45,000 kWh",
                caption="32.04 kWp Array",
                badge_text="Synthetic Scenario",
                badge_variant="neutral"
            )
        with m3:
            render_metric_card(
                label="25-Yr Baseline",
                value="1,125.0 MWh",
                caption="Constant Nominal",
                badge_text="Demo Value",
                badge_variant="neutral"
            )
        with m4:
            render_metric_card(
                label="Degraded Total (0.55%/yr)",
                value="1,053.4 MWh",
                caption="Compounded Degradation",
                badge_text="Demo Value",
                badge_variant="neutral"
            )

        render_section_header(
            title="25-Year Lifetime Energy Trajectory (Demonstration Preview)",
            subtitle="Comparison of constant baseline vs compounded annual degradation (d = 0.55%/yr)"
        )

        years = list(range(1, 26))
        baseline = [45000.0] * 25
        compounded = [45000.0 * ((1 - 0.0055) ** (t - 1)) for t in years]

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=years, y=baseline, name="Constant Baseline",
            line=dict(color="#94A3B8", width=2, dash="dash")
        ))
        fig.add_trace(go.Scatter(
            x=years, y=compounded, name="Compounded Degradation (0.55%/yr)",
            line=dict(color="#15803D", width=3),
            fill="tozeroy", fillcolor="rgba(21, 128, 61, 0.08)"
        ))
        fig.update_layout(
            plot_bgcolor="#FFFFFF",
            paper_bgcolor="#FFFFFF",
            margin=dict(l=20, r=20, t=20, b=20),
            xaxis=dict(title="Operating Year", gridcolor="#F1F5F9", showline=True, linecolor="#CBD5E1"),
            yaxis=dict(title="Annual Energy (kWh/yr)", gridcolor="#F1F5F9", showline=True, linecolor="#CBD5E1", range=[35000, 48000]),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            height=360
        )
        st.plotly_chart(fig, use_container_width=True)

