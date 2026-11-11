"""
SolarSelect — Phase 8: Foundation Engine Orchestrator
Public entry point for Phase 8 Stage 1: Foundation and Integration Layer.
Connects Phase 6 catalogue, Phase 7 roof-fit outputs, and Phase 8 capacity/feasibility evaluators.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
import uuid

from src.energy_economics.catalogue import ReadOnlyPanelCatalogue
from src.energy_economics.capacity_evaluator import CapacitySupportEvaluator
from src.energy_economics.phase7_adapter import Phase7Adapter
from src.energy_economics.feasibility import FeasibilityEvaluator


class Phase8FoundationEngine:
    """
    Orchestration engine for Phase 8 Stage 1.
    Ingests Phase 7 configurations, performs read-only Phase 6 catalogue audits,
    evaluates marginal training-capacity support, and produces Phase 8 contract-compliant outputs.
    """

    SCHEMA_VERSION = "phase8-io-0.1"
    STAGE_IDENTIFIER = "STAGE_1_FOUNDATION"

    def __init__(
        self,
        catalogue_path: Optional[Union[str, Path]] = None,
        catalogue: Optional[ReadOnlyPanelCatalogue] = None,
        capacity_evaluator: Optional[CapacitySupportEvaluator] = None,
    ) -> None:
        if catalogue is not None:
            self.catalogue = catalogue
        else:
            self.catalogue = ReadOnlyPanelCatalogue(
                catalogue_path=Path(catalogue_path) if catalogue_path else None
            )

        self.capacity_evaluator = capacity_evaluator or CapacitySupportEvaluator()
        self.feasibility_evaluator = FeasibilityEvaluator(
            catalogue=self.catalogue,
            capacity_evaluator=self.capacity_evaluator,
        )

    def evaluate_configuration(
        self,
        phase7_result: Union[Dict[str, Any], Any],
        run_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Evaluates a single Phase 7 configuration through the Stage 1 foundation pipeline.

        Args:
            phase7_result: Phase 7 PanelConfigurationResult or serialized dictionary.
            run_id: Optional run identifier. Generated automatically if omitted.

        Returns:
            Phase 8 contract-compliant output dictionary.
        """
        return self.evaluate_batch([phase7_result], run_id=run_id)

    def evaluate_batch(
        self,
        phase7_results: List[Union[Dict[str, Any], Any]],
        run_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Evaluates a batch of Phase 7 candidate configurations.

        Args:
            phase7_results: List of Phase 7 results.
            run_id: Optional run identifier.

        Returns:
            Phase 8 contract-compliant output dictionary for the candidate cohort.
        """
        active_run_id = run_id or f"RUN-PHASE8-FOUNDATION-{uuid.uuid4().hex[:8].upper()}"
        ingested_configs = Phase7Adapter.ingest_batch(phase7_results)

        candidate_outputs: List[Dict[str, Any]] = []
        global_warnings: List[str] = []

        for config in ingested_configs:
            cfg_id = config["configuration_id"]
            roof_id = config["roof_id"]
            panel_id = config["panel_id"]
            installed_kwp = config["installed_dc_capacity_kwp"]

            # Feasibility evaluation
            feasibility_res = self.feasibility_evaluator.evaluate(config)

            # Capacity support evaluation
            cap_res = self.capacity_evaluator.evaluate(installed_kwp)
            if cap_res.warning:
                global_warnings.append(
                    f"Candidate '{cfg_id}' ({installed_kwp:.2f} kWp): {cap_res.warning}"
                )

            # Catalogue provenance
            cat_provenance = (
                self.catalogue.get_provenance(panel_id)
                if self.catalogue.has_panel(panel_id)
                else {}
            )

            candidate_dict = {
                "configuration_id": cfg_id,
                "roof_id": roof_id,
                "panel_id": panel_id,
                "panel_model": config.get("panel_model", ""),
                "feasibility": feasibility_res.to_dict(),
                "energy": {
                    "mode": "not_evaluated_stage1",
                    "energy_basis": "UNVERIFIED",
                    "installed_dc_capacity_kwp": installed_kwp,
                    "model_input_kwp": installed_kwp,
                    "model_input_kwp_status": "PENDING_INFERENCE_BINDING",
                    "model_input_kwp_note": (
                        "Candidate DC capacity designated for Phase 5 'kWp' feature binding. "
                        "Model inference is not executed in Stage 1 (PREDICTION_PENDING_LAG_POLICY)."
                    ),
                    "capacity_support": cap_res.to_dict(),
                    "predicted_specific_yield_kwh_per_kwp_day": None,
                    "coverage": None,
                    "historical_year_status": None,
                    "observed_period_energy_kwh": None,
                    "e_year1_kwh": None,
                    "lifetime_total_kwh": None,
                    "degradation": None,
                },
                "temperature_comparison": None,
                "costs": None,
                "financials": None,
                "ranking": {
                    "pareto_status": "NOT_EVALUATED_STAGE1",
                    "pareto_rank": None,
                    "weighted_score": None,
                    "weighted_status": "NOT_EVALUATED_STAGE1",
                    "weighted_rank": None,
                },
                "spatial_metrics": config.get("spatial_metrics", {}),
                "catalogue_provenance": cat_provenance,
            }
            candidate_outputs.append(candidate_dict)

        # Remove duplicate warnings while preserving order
        dedup_warnings = list(dict.fromkeys(global_warnings))

        output: Dict[str, Any] = {
            "run_id": active_run_id,
            "schema_version": self.SCHEMA_VERSION,
            "engine_status": "SUCCESS",
            "stage": self.STAGE_IDENTIFIER,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "candidates": candidate_outputs,
            "pareto_set": [],
            "weighted_ranking": {"weights": {}, "normalisation_bounds": {}, "order": []},
            "recommendation": {
                "configuration_id": None,
                "basis": "none",
                "overall_recommendation_eligibility": "RECOMMENDATION_NOT_EVALUATED",
                "explanation": (
                    "Phase 8 Stage 1 Foundation layer only. Energy prediction, financial calculator, "
                    "and ranking algorithms are deferred to subsequent stages."
                ),
                "caveats": [
                    "Capacity support is strictly a marginal univariate assessment.",
                    "Energy basis is UNVERIFIED; AC/DC metering point remains unconfirmed under Blocking Issue B-1. No AC/DC conversion applied.",
                    "Model prediction pending approved prospective lag-yield policy (Blocking Issue B-2); no model inference executed in Stage 1.",
                    "Phase 6 catalogue technical specs are compiled from local PDF summaries; original manufacturer source authenticity was not independently verified.",
                    "No pricing or financial metrics evaluated.",
                ],
            },
            "provenance": {
                "phase6_catalogue_path": str(self.catalogue.catalogue_path),
                "phase6_catalogue_sha256": self.catalogue.compute_file_sha256(),
                "phase7_configurations_count": len(candidate_outputs),
                "phase8_stage": self.STAGE_IDENTIFIER,
            },
            "warnings": dedup_warnings,
            "unresolved_inputs": [
                "B-1: AC/DC metering point confirmation (energy_basis remains UNVERIFIED; no AC/DC conversion applied)",
                "B-2: Prospective roof lag-yield policy (model prediction remains PREDICTION_PENDING_LAG_POLICY)",
                "D-2: Weather source for non-UNISOLAR sites",
                "D-3: Commercial panel prices and balance-of-system costs",
            ],
        }

        return output

