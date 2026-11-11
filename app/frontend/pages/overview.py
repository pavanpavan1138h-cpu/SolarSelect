"""
SolarSelect — Overview Dashboard Page
Presents platform overview, workflow explanation, catalogue summary, and system notices.
"""

import streamlit as st
import pandas as pd

from app.frontend.components.ui import (
    render_page_header,
    render_metric_card,
    render_section_header,
    render_banner,
    render_step_card,
    render_status_badge,
)
from app.backend.services import SolarSelectPlatformService


def render_overview_page(service: SolarSelectPlatformService) -> None:
    """Renders the Overview Dashboard page."""
    render_page_header(
        title="Engineering Overview",
        subtitle="End-to-End MLOps System for Constraint-Aware Solar Panel Selection & Economics",
        breadcrumb="SolarSelect Platform / Overview"
    )

    # Core System Status Notice
    render_banner(
        message=(
            "SolarSelect couples machine learning solar yield predictions (Layer A) with real "
            "hardware catalogue records and 2D spatial array packing (Layer B). All energy and economic "
            "outputs reflect documented engineering boundaries without unverified extrapolations."
        ),
        variant="info",
        title="Platform Governance"
    )

    # Top-Level Platform Metrics
    status = service.get_system_status()
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        render_metric_card(
            label="Hardware Catalogue",
            value=f"{status['layer_b_hardware']['panel_count']} Panels",
            caption="Verified commercial datasheets",
            badge_text="Phase 6 Complete",
            badge_variant="success"
        )
    with col2:
        render_metric_card(
            label="Layer A Forecasting",
            value="MAE 0.905",
            caption="Tuned ExtraTrees (Peer Cohort)",
            badge_text="R² +0.2580",
            badge_variant="success"
        )
    with col3:
        render_metric_card(
            label="Layer B Array Packing",
            value="0.1 mm",
            caption="Row-wise strip packing heuristic",
            badge_text="Phase 7 Complete",
            badge_variant="success"
        )
    with col4:
        render_metric_card(
            label="Recommendation Engine",
            value="Pareto / MCDA",
            caption="10-stage sequential pipeline",
            badge_text="Phase 8 Complete",
            badge_variant="success"
        )

    # Workflow Architecture
    render_section_header(
        title="Integrated Engineering Workflow",
        subtitle="End-to-end data flow from rooftop geometry to multi-criteria recommendation"
    )

    w1, w2, w3, w4 = st.columns(4)
    with w1:
        render_step_card(
            step_num="Stage 01",
            title="Spatial Array Packing",
            description="Phase 7 row-wise heuristic packs panels onto rooftop envelopes with millimeter precision and setback avoidance.",
            status_label="Phase 7 Engine",
            status_variant="success"
        )
    with w2:
        render_step_card(
            step_num="Stage 02",
            title="Yield Forecasting",
            description="Phase 5 machine learning models forecast site-specific normalized daily yield (kWh/kWp) using 29 features.",
            status_label="Phase 5 Models",
            status_variant="success"
        )
    with w3:
        render_step_card(
            step_num="Stage 03",
            title="Lifetime Economics",
            description="Phase 8 computes 25-year degradation, system cash flows, NPV, fractional payback, and net/gross LCOE.",
            status_label="Phase 8 Financials",
            status_variant="success"
        )
    with w4:
        render_step_card(
            step_num="Stage 04",
            title="Pareto Ranking",
            description="Multi-objective Pareto peeling (Year-1 energy E₁ vs cost) and weighted MCDA synthesize transparent recommendations.",
            status_label="Recommendation",
            status_variant="success"
        )

    # Catalogue Summary Table
    render_section_header(
        title="Available Commercial Hardware Catalogue",
        subtitle="12 authenticated commercial PV modules spanning 6 distinct semiconductor technologies"
    )

    catalogue_df = service.get_panel_catalogue_summary()
    st.dataframe(
        catalogue_df,
        use_container_width=True,
        hide_index=True
    )

    # Documented Limitations & Operational Boundaries
    render_section_header(
        title="System Notices & Scientific Governance Boundaries",
        subtitle="Active engineering limitations registered in accordance with strict academic integrity"
    )

    limitations = service.get_documented_limitations()
    for lim in limitations:
        st.markdown(
            f"""
            <div style="background-color:#F8FAFC; border:1px solid #E2E8F0; border-left:3px solid #64748B; border-radius:4px; padding:0.75rem 1rem; margin-bottom:0.6rem;">
                <div style="font-size:0.85rem; font-weight:600; color:#0F172A; margin-bottom:0.2rem;">
                    <span style="color:#15803D; font-weight:700;">[{lim['id']}]</span> {lim['title']}
                </div>
                <div style="font-size:0.82rem; color:#475569; line-height:1.4;">
                    {lim['desc']}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
