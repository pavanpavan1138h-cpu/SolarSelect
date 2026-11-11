"""
SolarSelect — Financial Analysis Page
Displays lifecycle cost accounting, LCOE, NPV, and payback metrics when inputs exist.
"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd

from app.frontend.components.ui import (
    render_page_header,
    render_section_header,
    render_banner,
    render_empty_state,
    render_metric_card,
)
from app.backend.services import SolarSelectPlatformService


def render_financial_page(service: SolarSelectPlatformService) -> None:
    """Renders the Financial Analysis page."""
    render_page_header(
        title="Financial & LCOE Analysis",
        subtitle="Itemized CAPEX/OPEX accounting, Net Present Value, payback interpolation, and Levelized Cost of Energy",
        breadcrumb="SolarSelect Platform / Financial Analysis"
    )

    render_banner(
        message=(
            "Phase 6 Commercial Pricing Completeness is 0.00% (unpopulated per policy). "
            "No panel prices, inverter prices, or tariff structures are fabricated by the platform. "
            "Financial metrics evaluate strictly to NOT_EVALUATED_MISSING_COSTS until explicit user cost ledgers are provided."
        ),
        variant="warning",
        title="Missing Commercial Inputs"
    )

    show_demo = st.checkbox(
        "Show Synthetic Financial Layout Preview (DEMONSTRATION DATA ONLY — NOT A FINANCIAL PROJECTION)",
        value=False
    )

    if not show_demo:
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            render_metric_card(
                label="Net CAPEX",
                value="— AUD",
                caption="Gross outlay less upfront subsidy",
                badge_text="Missing Pricing",
                badge_variant="neutral"
            )
        with m2:
            render_metric_card(
                label="LCOE (Net Basis)",
                value="— /kWh",
                caption="Discounted cost per kWh",
                badge_text="Not Evaluated",
                badge_variant="neutral"
            )
        with m3:
            render_metric_card(
                label="Net Present Value",
                value="— AUD",
                caption="25-Yr discounted cash flows",
                badge_text="Missing Tariffs",
                badge_variant="neutral"
            )
        with m4:
            render_metric_card(
                label="Simple Payback",
                value="— Years",
                caption="Fractional-year recovery",
                badge_text="Not Evaluated",
                badge_variant="neutral"
            )

        render_section_header(
            title="Required External Financial Inputs",
            subtitle="Status of mandatory inputs required to unlock Stage 7 financial calculations"
        )

        req_df = pd.DataFrame([
            {"Input Category": "Module Procurement Price", "Source": "Phase 6 Catalogue", "Status": "Unpopulated (Null)", "Impact": "Blocks Gross/Net CAPEX"},
            {"Input Category": "Inverter & BOS Hardware", "Source": "External Vendor Quote", "Status": "Not Supplied", "Impact": "Blocks CAPEX & Replacement Schedule"},
            {"Input Category": "Electricity Retail & Feed-in Tariffs", "Source": "User / Jurisdiction", "Status": "Not Supplied", "Impact": "Blocks NPV & Payback"},
            {"Input Category": "Discount Rate & Basis (Real/Nominal)", "Source": "User Preference", "Status": "No Implicit Default", "Impact": "Blocks Discounting & LCOE"},
        ])
        st.dataframe(req_df, use_container_width=True, hide_index=True)

    else:
        render_banner(
            message="Values below represent an isolated synthetic test fixture solely to preview the Stage 7 financial UI layout.",
            variant="warning",
            title="DEMONSTRATION MODE ACTIVE"
        )

        m1, m2, m3, m4 = st.columns(4)
        with m1:
            render_metric_card(
                label="Demo Net CAPEX",
                value="$30,000 AUD",
                caption="Gross $35k - $5k STC subsidy",
                badge_text="Demo Value",
                badge_variant="neutral"
            )
        with m2:
            render_metric_card(
                label="Demo LCOE (Net)",
                value="$0.047 /kWh",
                caption="5.0% real discount rate",
                badge_text="Demo Value",
                badge_variant="neutral"
            )
        with m3:
            render_metric_card(
                label="Demo 25-Yr NPV",
                value="+$84,210 AUD",
                caption="70% self-consumption @ $0.30",
                badge_text="Demo Value",
                badge_variant="neutral"
            )
        with m4:
            render_metric_card(
                label="Demo Payback",
                value="3.8 Years",
                caption="Discounted: 4.3 Years",
                badge_text="Demo Value",
                badge_variant="neutral"
            )

        render_section_header(
            title="Cumulative Discounted Cash Flow (Demonstration Preview)",
            subtitle="Initial CAPEX enters strictly once at Year 0; annual savings accumulate over 25 years"
        )

        years = list(range(0, 26))
        dcf = [-30000.0]
        running = -30000.0
        for t in range(1, 26):
            annual_cf = 7800.0 * ((1 - 0.0055) ** (t - 1)) / ((1 + 0.05) ** t)
            running += annual_cf
            dcf.append(running)

        colors = ["#DC2626" if val < 0 else "#15803D" for val in dcf]

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=years, y=dcf, marker_color=colors, name="Cumulative DCF (AUD)"
        ))
        fig.update_layout(
            plot_bgcolor="#FFFFFF",
            paper_bgcolor="#FFFFFF",
            margin=dict(l=20, r=20, t=20, b=20),
            xaxis=dict(title="Project Year", gridcolor="#F1F5F9", showline=True, linecolor="#CBD5E1"),
            yaxis=dict(title="Cumulative Discounted Cash Flow (AUD)", gridcolor="#F1F5F9", showline=True, linecolor="#CBD5E1"),
            height=360
        )
        st.plotly_chart(fig, use_container_width=True)

