"""
SolarSelect — Recommendations Page
Presents Pareto frontier comparisons, weighted MCDA scores, and trade-off explanations.
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
    render_status_badge,
)
from app.backend.services import SolarSelectPlatformService


def render_recommendations_page(service: SolarSelectPlatformService) -> None:
    """Renders the Recommendations & Explanations page."""
    render_page_header(
        title="Hardware Recommendations",
        subtitle="Multi-objective Pareto frontier sorting, weighted MCDA ranking, and trade-off explanations",
        breadcrumb="SolarSelect Platform / Recommendations"
    )

    render_banner(
        message=(
            "Eligibility Governance: Primary ranking is strictly restricted to candidates with "
            "RECOMMENDATION_ELIGIBLE or RECOMMENDATION_FLAGGED status. Real prospective configurations "
            "currently evaluate strictly to RECOMMENDATION_NOT_EVALUATED and are never displayed as successful recommendations."
        ),
        variant="info",
        title="Recommendation Governance"
    )

    show_demo = st.checkbox(
        "Show Synthetic Recommendation Preview (DEMONSTRATION DATA ONLY — NOT A PRODUCTION PROPOSAL)",
        value=False
    )

    if not show_demo:
        render_empty_state(
            title="No Candidate Configurations Currently Eligible",
            description=(
                "Prospective rooftop configurations currently evaluate to RECOMMENDATION_NOT_EVALUATED "
                "due to unverified AC/DC metering (B-1), missing prospective yield history (B-2), unpopulated panel pricing, "
                "and unpopulated inverter records. Returning NOT_EVALUATED is the compliant engineering verdict. "
                "Toggle demonstration mode above to preview the multi-criteria ranking interface."
            ),
            badge_text="RECOMMENDATION_NOT_EVALUATED (Preserved)"
        )

        render_section_header(
            title="Mandatory Feasibility Gate Status Across Real Candidates",
            subtitle="Ordered evaluation hierarchy defined in Mathematical Specification §4.7"
        )

        gate_df = pd.DataFrame([
            {"Evaluation Gate": "1. Geometric Feasibility", "Module": "Phase 7 Placement Engine", "Verdict": "FEASIBLE", "Status": "PASS"},
            {"Evaluation Gate": "2. Catalogue Validity", "Module": "Phase 6 Catalogue", "Verdict": "VALID", "Status": "PASS"},
            {"Evaluation Gate": "3. Capacity Distribution", "Module": "Training Distribution", "Verdict": "CAPACITY_ELIGIBLE", "Status": "PASS"},
            {"Evaluation Gate": "4. Energy Prediction", "Module": "Phase 5 Inference", "Verdict": "PREDICTION_PENDING_LAG_POLICY", "Status": "BLOCKED (B-2)"},
            {"Evaluation Gate": "5. Electrical Compatibility", "Module": "Phase 8 Electrical", "Verdict": "NOT_EVALUATED_INSUFFICIENT_SPECS", "Status": "BLOCKED (Inverter)"},
            {"Evaluation Gate": "6. Economic Feasibility", "Module": "Phase 8 Cost Engine", "Verdict": "NOT_EVALUATED_MISSING_COSTS", "Status": "BLOCKED (Pricing)"},
            {"Evaluation Gate": "7. Overall Eligibility", "Module": "Feasibility Evaluator", "Verdict": "RECOMMENDATION_NOT_EVALUATED", "Status": "GOVERNANCE VERDICT"},
        ])
        st.dataframe(gate_df, use_container_width=True, hide_index=True)

    else:
        render_banner(
            message="Demonstration candidate set illustrating 2-objective Pareto peeling and trade-off explanation narrative.",
            variant="warning",
            title="DEMONSTRATION MODE ACTIVE"
        )

        m1, m2, m3 = st.columns(3)
        with m1:
            render_metric_card(
                label="Selected Hardware",
                value="SYNTH_P7_A",
                caption="Canadian Solar HiKu 445W (72 Panels)",
                badge_text="Pareto Frontier 1",
                badge_variant="success"
            )
        with m2:
            render_metric_card(
                label="Consensus Status",
                value="CONSENSUS",
                caption="Pareto Top = Weighted Top",
                badge_text="MCDA Score: 0.942",
                badge_variant="success"
            )
        with m3:
            render_metric_card(
                label="Trade-Off Profile",
                value="High Yield / Low LCOE",
                caption="45,000 kWh/yr @ $0.047/kWh",
                badge_text="Balanced",
                badge_variant="neutral"
            )

        render_section_header(
            title="Pareto Trade-Off Frontier (Demonstration Preview)",
            subtitle="Maximizing Year-1 Energy Generation vs Minimizing Levelized Cost of Energy"
        )

        demo_cands = [
            {"id": "SYNTH_P7_A", "energy": 45000, "lcoe": 0.047, "rank": "Frontier 1", "desc": "Balanced commercial solution"},
            {"id": "SYNTH_P7_B", "energy": 40000, "lcoe": 0.045, "rank": "Frontier 1", "desc": "Lowest cost per kWh"},
            {"id": "SYNTH_P7_C", "energy": 42000, "lcoe": 0.051, "rank": "Frontier 2", "desc": "Dominated by A and B"},
            {"id": "SYNTH_P7_D", "energy": 36000, "lcoe": 0.054, "rank": "Frontier 3", "desc": "Dominated alternative"},
        ]

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=[c["lcoe"] for c in demo_cands if c["rank"] == "Frontier 1"],
            y=[c["energy"] for c in demo_cands if c["rank"] == "Frontier 1"],
            mode="markers+text",
            marker=dict(size=14, color="#15803D", symbol="circle"),
            text=[c["id"] for c in demo_cands if c["rank"] == "Frontier 1"],
            textposition="top right",
            name="Frontier 1 (Non-Dominated)"
        ))
        fig.add_trace(go.Scatter(
            x=[c["lcoe"] for c in demo_cands if c["rank"] != "Frontier 1"],
            y=[c["energy"] for c in demo_cands if c["rank"] != "Frontier 1"],
            mode="markers+text",
            marker=dict(size=11, color="#94A3B8", symbol="diamond"),
            text=[c["id"] for c in demo_cands if c["rank"] != "Frontier 1"],
            textposition="top right",
            name="Dominated Frontiers"
        ))
        fig.update_layout(
            plot_bgcolor="#FFFFFF",
            paper_bgcolor="#FFFFFF",
            margin=dict(l=20, r=20, t=20, b=20),
            xaxis=dict(title="LCOE (AUD/kWh) [Minimizing]", gridcolor="#F1F5F9", showline=True, linecolor="#CBD5E1", range=[0.040, 0.060]),
            yaxis=dict(title="Year-1 Energy (kWh/yr) [Maximizing]", gridcolor="#F1F5F9", showline=True, linecolor="#CBD5E1", range=[32000, 48000]),
            height=360
        )
        st.plotly_chart(fig, use_container_width=True)

        st.markdown(
            """
            <div style="background-color:#F8FAFC; border:1px solid #E2E8F0; border-radius:6px; padding:1rem; margin-top:1rem;">
                <div style="font-size:0.9rem; font-weight:600; color:#0F172A; margin-bottom:0.25rem;">
                    Recommendation Explanation (Consensus Narrative)
                </div>
                <div style="font-size:0.85rem; color:#475569; line-height:1.5;">
                    Configuration <strong>SYNTH_P7_A</strong> is selected on Pareto Frontier 1. It achieves an optimal balance between maximizing total generation (45,000 kWh/yr) and maintaining competitive LCOE ($0.047/kWh). Weighted multi-criteria scoring confirms consensus alignment with user preference weights (60% Energy, 40% LCOE).
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

