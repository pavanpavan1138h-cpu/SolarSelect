"""
SolarSelect — Phase 9 Application Service Layer
Clean separation of concerns: connects to Phase 6 catalogue, Phase 7, and Phase 8.
"""

from typing import Dict, Any, List, Optional
import os
import pandas as pd

from src.energy_economics.catalogue import ReadOnlyPanelCatalogue
from src.roof_fit.engine import RoofFitEngine


class SolarSelectPlatformService:
    """
    Service adapter providing read-only access to existing Phase 6, 7, and 8 interfaces
    without duplicating business logic.
    """

    def __init__(self) -> None:
        self.catalogue = ReadOnlyPanelCatalogue()
        self.roof_engine = RoofFitEngine()

    def get_system_status(self) -> Dict[str, Any]:
        """Returns verified status of the core SolarSelect engineering components."""
        return {
            "platform_name": "SolarSelect Engineering Laboratory",
            "version": "Phase 9.0-alpha",
            "layer_a_forecasting": {
                "status": "READY_OFFLINE_EVALUATED",
                "model_cohort": "Peer Cohort (22 Sites)",
                "primary_model": "Tuned ExtraTreesRegressor",
                "test_r2": "+0.2580",
                "test_mae": "0.9050 kWh/kWp/day"
            },
            "layer_b_hardware": {
                "status": "CATALOGUE_VERIFIED",
                "panel_count": len(self.catalogue.list_panel_ids()),
                "commercial_pricing_status": "UNPOPULATED_PER_POLICY"
            },
            "layer_b_geometry": {
                "status": "PHASE_7_COMPLETE",
                "engine": "RowWisePlacementEngine (0.1 mm precision)"
            },
            "layer_b_economics": {
                "status": "PHASE_8_COMPLETE_WITH_LIMITATIONS",
                "orchestrator": "EnergyEconomicsEngine"
            }
        }

    def get_panel_catalogue_summary(self) -> pd.DataFrame:
        """Retrieves structured summary of all 12 commercial panels from Phase 6 catalogue."""
        panel_ids = self.catalogue.list_panel_ids()
        records = []
        for pid in panel_ids:
            p = self.catalogue.get_panel(pid)
            records.append({
                "Panel ID": p.panel_id,
                "Manufacturer": p.manufacturer,
                "Model": p.model,
                "Technology": p.cell_technology,
                "Rated Power (Wp)": p.rated_power_wp,
                "Efficiency (%)": p.module_efficiency_pct,
                "Length (mm)": int(p.length_mm),
                "Width (mm)": int(p.width_mm),
                "Weight (kg)": p.weight_kg if p.weight_kg is not None else "—",
                "Warranty (Yrs)": int(p.performance_warranty_years) if p.performance_warranty_years else "—"
            })
        return pd.DataFrame(records)

    def get_documented_limitations(self) -> List[Dict[str, str]]:
        """Returns the authoritative project limitations register items relevant to application users."""
        return [
            {
                "id": "B-1",
                "title": "Metering Basis Unverified",
                "desc": "Training generation reflects unverified AC vs DC net metering semantics. System derates must not be applied on a verified basis."
            },
            {
                "id": "B-2",
                "title": "Prospective Roof Lag Policy",
                "desc": "Phase 5 ML models require historical yield lag features. Prospective unbuilt roofs lack empirical yield and evaluate to PREDICTION_PENDING_LAG_POLICY."
            },
            {
                "id": "Commercial Pricing",
                "title": "Procurement Pricing Unpopulated",
                "desc": "The Phase 6 panel catalogue contains verified physical and thermal specs, but commercial panel pricing is unpopulated. Financial evaluations require explicit user cost ledgers."
            },
            {
                "id": "Inverter Records",
                "title": "Inverter Specifications Unpopulated",
                "desc": "The catalogue currently does not store matched inverter records. Electrical compatibility requires user-supplied inverter datasheets."
            },
            {
                "id": "Capacity Distribution",
                "title": "Commercial Training Support Range",
                "desc": "86.4% of Phase 5 training arrays cluster between 21.39 and 100 kWp. Residential arrays (< 21.39 kWp) represent unsupported extrapolations and are quarantined in Pareto ranking."
            }
        ]
