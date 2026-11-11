"""
SolarSelect — Phase 9 Interactive Dashboard Application Entry Point
Light Theme + Minimal Professional SaaS Design System.
"""

import os
import sys
from pathlib import Path

# Ensure project root is in Python sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

# Must be the very first Streamlit command
st.set_page_config(
    page_title="SolarSelect — MLOps Engineering Platform",
    page_icon="☀️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Load custom CSS
CSS_PATH = Path(__file__).resolve().parent / "styles" / "custom.css"
if CSS_PATH.exists():
    with open(CSS_PATH, "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

from app.backend.services import SolarSelectPlatformService
from app.frontend.pages.overview import render_overview_page
from app.frontend.pages.roof_config import render_roof_config_page
from app.frontend.pages.energy_analysis import render_energy_page
from app.frontend.pages.financial_analysis import render_financial_page
from app.frontend.pages.recommendations import render_recommendations_page
from app.frontend.pages.mlops_centre import render_mlops_page


@st.cache_resource
def get_service() -> SolarSelectPlatformService:
    """Initializes and caches the platform service layer."""
    return SolarSelectPlatformService()


def main() -> None:
    service = get_service()

    # Sidebar Navigation Branding & Menu
    with st.sidebar:
        st.markdown(
            """
            <div style="padding: 0.5rem 0 1.25rem 0; border-bottom: 1px solid #E2E8F0; margin-bottom: 1rem;">
                <div style="font-size: 1.25rem; font-weight: 700; color: #0F172A; display: flex; align-items: center; gap: 0.4rem;">
                    <span style="color: #15803D;">☀️</span> SolarSelect
                </div>
                <div style="font-size: 0.78rem; color: #64748B; font-weight: 500; margin-top: 0.2rem;">
                    MLOps Laboratory Platform
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            '<div style="font-size: 0.72rem; font-weight: 700; text-transform: uppercase; color: #94A3B8; letter-spacing: 0.05em; margin-bottom: 0.5rem;">Navigation</div>',
            unsafe_allow_html=True,
        )

        pages = {
            "Overview": "Overview",
            "Roof Configuration": "Roof Configuration",
            "Energy Analysis": "Energy Analysis",
            "Financial Analysis": "Financial Analysis",
            "Recommendations": "Recommendations",
            "Model & MLOps Centre": "Model & MLOps Centre",
        }

        selection = st.radio(
            "Go to",
            list(pages.keys()),
            label_visibility="collapsed",
            index=0,
        )

        st.markdown(
            """
            <div style="margin-top: 3.5rem; padding-top: 1rem; border-top: 1px solid #E2E8F0;">
                <div style="font-size: 0.72rem; font-weight: 700; text-transform: uppercase; color: #94A3B8; letter-spacing: 0.05em; margin-bottom: 0.4rem;">Platform Status</div>
                <div style="font-size: 0.78rem; color: #334155; margin-bottom: 0.25rem;"><span style="color: #15803D;">●</span> Core: <strong>Active</strong></div>
                <div style="font-size: 0.78rem; color: #334155; margin-bottom: 0.25rem;"><span style="color: #15803D;">●</span> Catalogue: <strong>12 Modules</strong></div>
                <div style="font-size: 0.78rem; color: #334155; margin-bottom: 0.25rem;"><span style="color: #15803D;">●</span> Models: <strong>Peer Cohort</strong></div>
                <div style="font-size: 0.72rem; color: #94A3B8; margin-top: 0.6rem;">Phase 9 UI Shell v0.1.0</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Route Page
    if selection == "Overview":
        render_overview_page(service)
    elif selection == "Roof Configuration":
        render_roof_config_page(service)
    elif selection == "Energy Analysis":
        render_energy_page(service)
    elif selection == "Financial Analysis":
        render_financial_page(service)
    elif selection == "Recommendations":
        render_recommendations_page(service)
    elif selection == "Model & MLOps Centre":
        render_mlops_page(service)


if __name__ == "__main__":
    main()

