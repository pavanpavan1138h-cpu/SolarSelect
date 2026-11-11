"""
SolarSelect — Phase 8: Comprehensive Energy, Economics & Recommendation Engine
Orchestrates the entire Phase 8 pipeline conforming strictly to Section 6 Output Schema:
Phase 7 geometry + Phase 6 catalogue
  -> Stage 1: Foundation Layer & Marginal Capacity Support
  -> Stage 2: Frozen Phase 5 Inference & Historical Replay
  -> Stage 3: Daily Energy Estimation & D-4 Negative Yield Preservation
  -> Stage 4: Temperature Evaluation Audit
  -> Stage 5: Annualization & Constant-Performance Lifetime Baseline
  -> Stage 6: Lifetime Degradation Modelling (Compounded & Linear)
  -> Stage 7: System Cost Accounting & Lifecycle Financials (NPV, Payback, LCOE)
  -> Stage 8: Electrical Compatibility & Multi-Gate Hard Feasibility
  -> Stage 9: Deterministic Pareto & Multi-Criteria Weighted Ranking
  -> Stage 10: Recommendation Synthesis & Transparent Explanation
"""

from typing import Dict, Any, List, Optional, Tuple, Union
from datetime import datetime, timezone
import uuid

from src.energy_economics.exceptions import Phase8Error
from src.energy_economics.types import (
    RecommendationBasis,
    RateBasis,
    LCOECapexBasis,
    DegradationModel,
    DegradationSource,
    OverallRecommendationEligibility,
    CapacityEligibility,
    PredictionAvailability,
    EnergyScenarioType,
    CostItem,
    InverterSpecs,
    StringDesign,
    ModuleElectricalSpecs,
)
from src.energy_economics.catalogue import ReadOnlyPanelCatalogue
from src.energy_economics.phase7_adapter import Phase7Adapter
from src.energy_economics.foundation import Phase8FoundationEngine
from src.energy_economics.inference import Phase5PeerCohortPredictor
from src.energy_economics.historical_replay import UNISOLARHistoricalReplayEngine
from src.energy_economics.energy_engine import Phase8EnergyEstimationEngine
from src.energy_economics.annualization import Phase8AnnualizationEngine
from src.energy_economics.degradation import Phase8DegradationEngine
from src.energy_economics.system_cost import Phase8SystemCostEngine
from src.energy_economics.financial import Phase8FinancialEngine
from src.energy_economics.electrical import Phase8ElectricalEngine
from src.energy_economics.feasibility import FeasibilityEvaluator
from src.energy_economics.pareto import Phase8ParetoEngine
from src.energy_economics.weighted_ranking import Phase8WeightedRankingEngine
from src.energy_economics.recommendation import Phase8RecommendationEngine


class EnergyEconomicsEngine:
    """
    Top-level orchestrator for SolarSelect Phase 8.
    Produces comprehensive, deterministic evaluation reports conforming to the
    Section 6 Output Schema Contract.
    """

    SCHEMA_VERSION = "phase8-io-0.1"

    def __init__(
        self,
        catalogue: Optional[ReadOnlyPanelCatalogue] = None,
        foundation_engine: Optional[Phase8FoundationEngine] = None,
        energy_engine: Optional[Phase8EnergyEstimationEngine] = None,
        annualization_engine: Optional[Phase8AnnualizationEngine] = None,
        degradation_engine: Optional[Phase8DegradationEngine] = None,
        cost_engine: Optional[Phase8SystemCostEngine] = None,
        financial_engine: Optional[Phase8FinancialEngine] = None,
        electrical_engine: Optional[Phase8ElectricalEngine] = None,
        feasibility_evaluator: Optional[FeasibilityEvaluator] = None,
        pareto_engine: Optional[Phase8ParetoEngine] = None,
        weighted_engine: Optional[Phase8WeightedRankingEngine] = None,
        recommendation_engine: Optional[Phase8RecommendationEngine] = None,
    ) -> None:
        self.catalogue = catalogue or ReadOnlyPanelCatalogue()
        self.foundation_engine = foundation_engine or Phase8FoundationEngine(catalogue=self.catalogue)
        self.energy_engine = energy_engine or Phase8EnergyEstimationEngine()
        self.annualization_engine = annualization_engine or Phase8AnnualizationEngine()
        self.degradation_engine = degradation_engine or Phase8DegradationEngine(catalogue=self.catalogue)
        self.cost_engine = cost_engine or Phase8SystemCostEngine()
        self.financial_engine = financial_engine or Phase8FinancialEngine()
        self.electrical_engine = electrical_engine or Phase8ElectricalEngine()
        self.feasibility_evaluator = feasibility_evaluator or FeasibilityEvaluator(catalogue=self.catalogue)
        self.pareto_engine = pareto_engine or Phase8ParetoEngine()
        self.weighted_engine = weighted_engine or Phase8WeightedRankingEngine()
        self.recommendation_engine = recommendation_engine or Phase8RecommendationEngine()

    def evaluate_configuration(
        self,
        phase7_config: Dict[str, Any],
        scenario_annual_energy_kwh: Optional[float] = None,
        cost_items: Optional[List[CostItem]] = None,
        discount_rate: Optional[float] = None,
        rate_basis: Optional[RateBasis] = None,
        lcoe_capex_basis: LCOECapexBasis = LCOECapexBasis.NET,
        self_consumption_ratio: Optional[float] = None,
        purchase_tariff: Optional[float] = None,
        export_tariff: Optional[float] = None,
        inverter_specs: Optional[InverterSpecs] = None,
        string_design: Optional[StringDesign] = None,
        module_specs: Optional[Union[ModuleElectricalSpecs, Any]] = None,
        min_design_temp_c: float = -5.0,
        max_design_temp_c: float = 45.0,
        degradation_rate: Optional[float] = None,
        degradation_model: DegradationModel = DegradationModel.COMPOUNDED,
        lifetime_years: int = 25,
        user_budget: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Evaluates a single Phase 7 candidate configuration across all ten stages of Phase 8.

        Executes:
        - Stage 1: Foundation ingestion and capacity support assessment.
        - Stage 2/3/5: Energy availability and annualization baseline.
        - Stage 6: Degradation profiling.
        - Stage 7: System cost accounting and financial evaluation (NPV, payback, LCOE).
        - Stage 8: Electrical compatibility and multi-gate feasibility filtering.
        """
        # 1. Foundation ingestion
        ingested = Phase7Adapter.validate_and_ingest(phase7_config)
        cfg_id = ingested["configuration_id"]
        roof_id = ingested["roof_id"]
        panel_id = ingested["panel_id"]
        installed_dc_capacity_kwp = ingested["installed_dc_capacity_kwp"]
        panel_count = ingested["panel_count"]

        # 2. Energy and Prediction Availability
        if scenario_annual_energy_kwh is not None:
            annual_energy = scenario_annual_energy_kwh
            prediction_status = PredictionAvailability.PREDICTION_AVAILABLE
        else:
            annual_energy = None
            prediction_status = PredictionAvailability.PREDICTION_PENDING_LAG_POLICY

        # 3. Annualization & Degradation
        lifetime_baseline = None
        degradation_profile = None
        if annual_energy is not None:
            lifetime_baseline = self.annualization_engine.compute_lifetime_baseline(
                annual_energy, lifetime_years=lifetime_years
            )
            degradation_profile = self.degradation_engine.evaluate_degradation(
                annual_energy=annual_energy,
                degradation_model=degradation_model,
                degradation_rate=degradation_rate,
                panel_id=panel_id,
                lifetime_years=lifetime_years,
                degradation_source=(
                    DegradationSource.CATALOGUE
                    if degradation_rate is None
                    else DegradationSource.USER
                ),
            )

        # 4. System Cost & Financials
        cost_res = None
        fin_res = None
        if cost_items:
            cost_res = self.cost_engine.evaluate_system_cost(
                cost_items=cost_items,
                rate_basis=rate_basis or RateBasis.REAL,
            )
            if (
                annual_energy is not None
                and discount_rate is not None
                and rate_basis is not None
            ):
                fin_res = self.financial_engine.evaluate_financials(
                    system_cost=cost_res,
                    annual_energy=annual_energy,
                    lifetime_years=lifetime_years,
                    discount_rate=discount_rate,
                    rate_basis=rate_basis,
                    lcoe_capex_basis=lcoe_capex_basis,
                    self_consumption_ratio=self_consumption_ratio,
                    purchase_tariff=purchase_tariff,
                    export_tariff=export_tariff,
                )

        # 5. Electrical Compatibility
        elec_res = None
        if inverter_specs and string_design:
            target_module = module_specs if module_specs is not None else self.catalogue.get_panel(panel_id)
            if target_module:
                elec_res = self.electrical_engine.evaluate_compatibility(
                    module_specs=target_module,
                    inverter_specs=inverter_specs,
                    string_design=string_design,
                    total_panel_count=panel_count,
                )

        # 6. Multi-Gate Feasibility
        feas_res = self.feasibility_evaluator.evaluate(
            phase7_config=phase7_config,
            electrical_result=elec_res,
            financial_result=fin_res,
            prediction_status=prediction_status,
            user_budget=user_budget,
        )

        return {
            "configuration_id": cfg_id,
            "roof_id": roof_id,
            "panel_id": panel_id,
            "installed_dc_capacity_kwp": installed_dc_capacity_kwp,
            "panel_count": panel_count,
            "energy": {
                "annual_energy_kwh": annual_energy,
                "prediction_availability": (
                    prediction_status.value
                    if hasattr(prediction_status, "value")
                    else str(prediction_status)
                ),
                "lifetime_energy_baseline_kwh": (
                    lifetime_baseline.baseline_lifetime_energy_kwh
                    if lifetime_baseline
                    else None
                ),
                "lifetime_degraded_energy_kwh": (
                    degradation_profile.cumulative_lifetime_energy_kwh
                    if degradation_profile
                    else None
                ),
            },
            "annual_energy_kwh": annual_energy,
            "costs": {
                "c_gross": cost_res.c_gross if cost_res else None,
                "s_up": cost_res.s_upfront if cost_res else None,
                "c_net": cost_res.c_net if cost_res else None,
            },
            "capex_net": cost_res.c_net if cost_res else None,
            "financials": {
                "npv": fin_res.npv if fin_res else None,
                "lcoe": fin_res.lcoe_per_kwh if fin_res else None,
                "simple_payback_years": (
                    fin_res.simple_payback_years if fin_res else None
                ),
                "discounted_payback_years": (
                    fin_res.discounted_payback_years if fin_res else None
                ),
            },
            "lcoe_per_kwh": fin_res.lcoe_per_kwh if fin_res else None,
            "feasibility": feas_res.to_dict(),
        }

    def run(
        self,
        candidate_evaluations: List[Dict[str, Any]],
        weights: Optional[Dict[str, float]] = None,
        recommendation_basis: Union[RecommendationBasis, str] = RecommendationBasis.PARETO,
        cost_objective: str = "lcoe",
        preferred_tradeoff: Optional[str] = None,
        energy_only: bool = False,
        run_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Executes multi-candidate ranking and recommendation synthesis.

        Args:
            candidate_evaluations: List of candidate dictionaries already populated with feasibility,
                                   energy, costs, and financials, or evaluated configurations.
            weights: User-supplied weights for weighted ranking (e.g. {'annual_energy': 0.6, 'lcoe': 0.4}).
            recommendation_basis: Recommendation basis ('pareto', 'weighted', 'energy_only', 'none').
            cost_objective: Metric to minimize in Pareto ranking (default: 'lcoe').
            preferred_tradeoff: Optional preference for Pareto selection ('min_cost', 'max_energy', config_id).
            energy_only: If True, executes single-objective energy ordering.
            run_id: Optional run identifier.

        Returns:
            Structured JSON-compatible dictionary conforming strictly to Section 6 schema.
        """
        active_run_id = run_id or f"phase8-run-{uuid.uuid4().hex[:12]}"
        warnings: List[str] = []
        unresolved_inputs: List[str] = [
            "B-1: AC/DC metering point confirmation (energy_basis remains UNVERIFIED)",
            "B-2: Prospective roof lag-yield policy (PREDICTION_PENDING_LAG_POLICY)",
        ]

        # 1. Execute Pareto Ranking (Stage 9A)
        pareto_res = self.pareto_engine.evaluate_pareto_ranking(
            candidates=candidate_evaluations,
            cost_objective=cost_objective,
            energy_only=energy_only,
            allow_exploratory_annex=True,
        )
        warnings.extend(pareto_res.warnings)

        # 2. Execute Weighted Ranking (Stage 9B) if weights supplied
        weighted_res = None
        if weights:
            weighted_res = self.weighted_engine.evaluate_weighted_ranking(
                candidates=candidate_evaluations,
                weights=weights,
            )
            warnings.extend(weighted_res.warnings)

        # 3. Execute Recommendation Engine (Stage 10)
        rec_res = self.recommendation_engine.evaluate_recommendation(
            candidates=candidate_evaluations,
            pareto_result=pareto_res,
            weighted_result=weighted_res,
            basis=recommendation_basis,
            preferred_tradeoff=preferred_tradeoff,
        )

        # 4. Synthesize Candidates with Ranking Subdictionaries conforming to Section 6 schema
        processed_candidates = []
        for cand in candidate_evaluations:
            cid = str(cand.get("configuration_id", ""))
            par_c = pareto_res.candidates.get(cid)
            wt_c = weighted_res.candidates.get(cid) if weighted_res else None

            cand_copy = dict(cand)
            cand_copy["ranking"] = {
                "pareto_status": par_c.pareto_status if par_c else "",
                "pareto_rank": par_c.pareto_rank if par_c else None,
                "weighted_score": wt_c.weighted_score if wt_c else None,
                "weighted_status": wt_c.weighted_status if wt_c else "",
                "weighted_rank": wt_c.weighted_rank if wt_c else None,
            }
            processed_candidates.append(cand_copy)

        # Determine overall engine status
        has_eligible = any(
            c.get("feasibility", {}).get("overall_recommendation_eligibility") in (
                OverallRecommendationEligibility.RECOMMENDATION_ELIGIBLE.value,
                OverallRecommendationEligibility.RECOMMENDATION_FLAGGED.value,
            )
            for c in candidate_evaluations
        )
        if not candidate_evaluations:
            engine_status = "INCOMPLETE_INPUTS"
        elif has_eligible:
            engine_status = "SUCCESS"
        else:
            engine_status = "PARTIAL_RESULT"

        return {
            "run_id": active_run_id,
            "schema_version": self.SCHEMA_VERSION,
            "engine_status": engine_status,
            "candidates": processed_candidates,
            "pareto_set": pareto_res.pareto_set,
            "weighted_ranking": {
                "weights": weighted_res.weights if weighted_res else {},
                "normalisation_bounds": weighted_res.normalisation_bounds if weighted_res else {},
                "order": weighted_res.ranked_order if weighted_res else [],
            },
            "recommendation": rec_res.to_dict(),
            "provenance": {
                "engine_version": "0.1.0",
                "schema_version": self.SCHEMA_VERSION,
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "cost_objective": cost_objective,
                "recommendation_basis": str(recommendation_basis),
            },
            "warnings": sorted(list(set(warnings))),
            "unresolved_inputs": unresolved_inputs,
        }

