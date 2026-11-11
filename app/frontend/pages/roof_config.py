"""
SolarSelect — Roof Configuration Page
Enables users to specify rooftop parameters and inspect geometric proposal readiness.
"""

import streamlit as st
import pandas as pd

from app.frontend.components.ui import (
    render_page_header,
    render_section_header,
    render_banner,
    render_empty_state,
    render_metric_card,
    render_status_badge,
)
from app.backend.services import SolarSelectPlatformService


def render_roof_config_page(service: SolarSelectPlatformService) -> None:
    """Renders the Roof Configuration page."""
    render_page_header(
        title="Roof Configuration",
        subtitle="Define rooftop geometry, perimeter setbacks, and panel hardware for array placement",
        breadcrumb="SolarSelect Platform / Configuration"
    )

    render_banner(
        message=(
            "Phase 7 implements a deterministic 2D row-wise strip packing heuristic operating on "
            "planar rectangular rooftops with 0.1 mm coordinate quantization. Placement proposals "
            "represent geometric feasibility only and do not constitute structural or electrical sign-off."
        ),
        variant="info",
        title="Geometric Contract"
    )

    col_form, col_preview = st.columns([1, 1], gap="large")

    with col_form:
        render_section_header(
            title="Rooftop & Mounting Specifications",
            subtitle="Configure physical boundary dimensions and safety clearances"
        )

        roof_id = st.text_input("Roof Identifier", value="ROOF-COMMERCIAL-01")

        dim_col1, dim_col2 = st.columns(2)
        with dim_col1:
            length = st.number_input("Eave Length (m)", min_value=2.0, max_value=200.0, value=30.0, step=1.0)
        with dim_col2:
            width = st.number_input("Slope Width (m)", min_value=2.0, max_value=200.0, value=20.0, step=1.0)

        setback_col1, setback_col2 = st.columns(2)
        with setback_col1:
            setback = st.number_input("Perimeter Setback (m)", min_value=0.0, max_value=5.0, value=0.5, step=0.1)
        with setback_col2:
            walkway = st.number_input("Inter-Row Walkway (m)", min_value=0.0, max_value=2.0, value=0.5, step=0.05)

        panel_ids = service.catalogue.list_panel_ids()
        selected_panel = st.selectbox(
            "Target Commercial Panel Model",
            options=panel_ids,
            index=0
        )

        panel_record = service.catalogue.get_panel(selected_panel)
        st.markdown(
            f"""
            <div style="font-size:0.8rem; color:#475569; background:#F8FAFC; padding:0.5rem 0.75rem; border-radius:4px; border:1px solid #E2E8F0; margin-bottom:1rem;">
                <strong>Selected Hardware:</strong> {panel_record.manufacturer} {panel_record.model} ({panel_record.rated_power_wp} Wp, {panel_record.module_efficiency_pct}% eff, {int(panel_record.length_mm)}×{int(panel_record.width_mm)} mm)
            </div>
            """,
            unsafe_allow_html=True
        )

        orientation = st.radio(
            "Orientation Selection Policy",
            options=["Automatic Optimization (Maximize Capacity)", "Forced Portrait", "Forced Landscape"],
            index=0
        )

        st.button("Run Phase 7 Placement Engine", type="primary", use_container_width=True)

    with col_preview:
        render_section_header(
            title="Spatial Geometry Preview",
            subtitle="Calculated rooftop envelope and array placement metrics"
        )

        gross_area = length * width
        usable_len = max(0.0, length - 2 * setback)
        usable_wid = max(0.0, width - 2 * setback)
        usable_area = usable_len * usable_wid

        m1, m2 = st.columns(2)
        with m1:
            render_metric_card(
                label="Gross Roof Area",
                value=f"{gross_area:.1f} m²",
                caption=f"{length:.1f} m × {width:.1f} m footprint"
            )
        with m2:
            render_metric_card(
                label="Net Usable Envelope",
                value=f"{usable_area:.1f} m²",
                caption=f"{setback:.1f} m perimeter safety buffer",
                badge_text="Quantized 0.1 mm",
                badge_variant="neutral"
            )

        render_empty_state(
            title="Interactive Layout Canvas Ready",
            description=(
                "Click 'Run Phase 7 Placement Engine' to execute the row-wise heuristic strip packing algorithm, "
                "generate coordinate placements, and audit whole-array physical constraints."
            ),
            badge_text="Integration Ready — Phase 7 Engine"
        )

