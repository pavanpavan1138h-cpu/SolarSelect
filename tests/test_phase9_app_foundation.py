"""
SolarSelect — Phase 9 Application & UI Smoke Tests
Validates frontend components, service integration, design tokens, and navigation.
"""

import pytest
import pandas as pd

from app.backend.services import SolarSelectPlatformService
from app.backend.schemas import (
    RoofConfigurationRequestSchema,
    ObstacleInputSchema,
    SystemStatusSchema,
)
from app.frontend.styles import theme
from app.frontend.components.ui import (
    render_status_badge,
)


def test_platform_service_status():
    """Verifies that platform service correctly reports the status of Phases 5-8."""
    svc = SolarSelectPlatformService()
    status = svc.get_system_status()

    assert "platform_name" in status
    assert status["layer_b_hardware"]["panel_count"] == 12
    assert status["layer_a_forecasting"]["status"] == "READY_OFFLINE_EVALUATED"
    assert status["layer_b_geometry"]["status"] == "PHASE_7_COMPLETE"
    assert status["layer_b_economics"]["status"] == "PHASE_8_COMPLETE_WITH_LIMITATIONS"


def test_platform_service_catalogue_summary():
    """Verifies that service extracts all 12 commercial panel records."""
    svc = SolarSelectPlatformService()
    df = svc.get_panel_catalogue_summary()

    assert isinstance(df, pd.DataFrame)
    assert len(df) == 12
    assert "Panel ID" in df.columns
    assert "Manufacturer" in df.columns
    assert "Rated Power (Wp)" in df.columns
    assert "PNL-CANADIAN-445W" in df["Panel ID"].values


def test_platform_service_limitations():
    """Verifies that authoritative project limitations are exposed."""
    svc = SolarSelectPlatformService()
    lims = svc.get_documented_limitations()

    assert len(lims) >= 5
    lim_ids = [lim["id"] for lim in lims]
    assert "B-1" in lim_ids
    assert "B-2" in lim_ids
    assert "Commercial Pricing" in lim_ids


def test_pydantic_schemas():
    """Verifies request schemas for roof configuration and status."""
    obs = ObstacleInputSchema(
        obstacle_id="OBS-1",
        x=2.0,
        y=3.0,
        width=1.5,
        height=1.0,
        buffer=0.2
    )
    assert obs.width == 1.5

    req = RoofConfigurationRequestSchema(
        roof_id="ROOF-01",
        length=20.0,
        width=15.0,
        perimeter_setback=0.5,
        panel_id="PNL-CANADIAN-445W",
        obstacles=[obs]
    )
    assert req.length == 20.0
    assert len(req.obstacles) == 1


def test_ui_theme_tokens():
    """Verifies that design system tokens conform to light SaaS theme."""
    assert theme.COLOR_BG_PRIMARY == "#FFFFFF"
    assert theme.COLOR_TEXT_PRIMARY == "#0F172A"
    assert theme.COLOR_ACCENT == "#15803D"
    assert "SUCCESS" in theme.STATUS_COLORS
    assert "WARNING" in theme.STATUS_COLORS
    assert "ERROR" in theme.STATUS_COLORS
    assert "NEUTRAL" in theme.STATUS_COLORS


def test_status_badge_html_rendering():
    """Verifies that status badge produces clean, semantic HTML."""
    badge = render_status_badge("Eligible", variant="success", return_html=True)
    assert "ss-badge-success" in badge
    assert "Eligible" in badge

    badge_warn = render_status_badge("Flagged", variant="warning", return_html=True)
    assert "ss-badge-warning" in badge_warn


def test_streamlit_app_navigation():
    """Verifies that all 6 application pages render cleanly without exceptions via AppTest."""
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("app/frontend/main.py", default_timeout=15)
    at.run()
    assert not at.exception

    # Check Overview content
    assert len(at.markdown) > 5

    # Navigate across each page
    radio = at.sidebar.radio[0]
    pages = [
        "Roof Configuration",
        "Energy Analysis",
        "Financial Analysis",
        "Recommendations",
        "Model & MLOps Centre",
    ]
    for page_name in pages:
        radio.set_value(page_name).run()
        assert not at.exception, f"Failed rendering page {page_name}: {at.exception}"

