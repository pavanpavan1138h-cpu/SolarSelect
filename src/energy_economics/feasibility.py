"""
SolarSelect — Phase 8: Stage 8 Multi-Gate Feasibility Engine
Evaluates multi-stage feasibility gates across geometric, catalogue, capacity,
prediction, electrical, and economic domains.
Enforces the strict rule that unevaluated gates never count as a pass,
and hard feasibility failures disqualify candidates before ranking.
"""

from typing import Dict, Any, Optional, List, Union

from src.energy_economics.catalogue import ReadOnlyPanelCatalogue
from src.energy_economics.capacity_evaluator import CapacitySupportEvaluator
from src.energy_economics.types import (
    FeasibilityResult,
    GeometricFeasibility,
    CatalogueValidity,
    CapacitySupportStatus,
    CapacityEligibility,
    PredictionAvailability,
    ElectricalCompatibility,
    EconomicFeasibility,
    OverallRecommendationEligibility,
    ElectricalCompatibilityResult,
    FinancialEvaluationResult,
)


class FeasibilityEvaluator:
    """
    Evaluates multi-gate feasibility for candidate panel configurations.
    Enforces sequential failure logging, hard constraint filtering,
    and strict separation between marginal capacity eligibility and overall
    recommendation eligibility.
    """

    def __init__(
        self,
        catalogue: Optional[ReadOnlyPanelCatalogue] = None,
        capacity_evaluator: Optional[CapacitySupportEvaluator] = None,
    ) -> None:
        self.catalogue = catalogue or ReadOnlyPanelCatalogue()
        self.capacity_evaluator = capacity_evaluator or CapacitySupportEvaluator()

    def evaluate(
        self,
        phase7_config: Dict[str, Any],
        electrical_result: Optional[ElectricalCompatibilityResult] = None,
        financial_result: Optional[FinancialEvaluationResult] = None,
        prediction_status: Optional[Union[PredictionAvailability, str]] = None,
        user_budget: Optional[float] = None,
        budget_basis: str = "net",
    ) -> FeasibilityResult:
        """
        Evaluates feasibility for an ingested Phase 7 candidate configuration across all gates.

        Args:
            phase7_config: Validated Phase 7 configuration dictionary.
            electrical_result: Optional evaluated ElectricalCompatibilityResult.
            financial_result: Optional evaluated FinancialEvaluationResult.
            prediction_status: Prediction availability status (default: PREDICTION_PENDING_LAG_POLICY).
            user_budget: Optional maximum investment budget limit.
            budget_basis: Basis to test budget against ("net" or "gross").

        Returns:
            Structured FeasibilityResult containing individual gate verdicts and overall eligibility.
        """
        first_failed_stage: Optional[str] = None

        # 1. Geometric Feasibility (inherited from Phase 7)
        raw_geo = phase7_config.get("feasibility_status", "").upper()
        panel_count = phase7_config.get("panel_count", 0)
        violations = phase7_config.get("constraint_violations", [])

        if raw_geo == "FEASIBLE" and panel_count >= 1 and len(violations) == 0:
            geometric_status = GeometricFeasibility.FEASIBLE
        else:
            geometric_status = GeometricFeasibility.INFEASIBLE
            if first_failed_stage is None:
                first_failed_stage = "geometric"

        # 2. Catalogue Validity (Phase 6 record audit)
        panel_id = phase7_config.get("panel_id", "")
        cat_valid, cat_errors = self.catalogue.validate_panel_record(panel_id)
        if cat_valid:
            catalogue_status = CatalogueValidity.VALID
        else:
            catalogue_status = CatalogueValidity.INVALID
            if first_failed_stage is None:
                first_failed_stage = "catalogue"

        # 3. Capacity Support and Marginal Capacity Eligibility
        installed_kwp = phase7_config.get("installed_dc_capacity_kwp", 0.0)
        cap_res = self.capacity_evaluator.evaluate(installed_kwp)
        capacity_support_status = cap_res.status
        capacity_eligibility = cap_res.capacity_eligibility

        if capacity_eligibility in (
            CapacityEligibility.CAPACITY_INELIGIBLE_OUT_OF_RANGE,
            CapacityEligibility.CAPACITY_INELIGIBLE_UNAVAILABLE,
        ):
            if first_failed_stage is None:
                first_failed_stage = "capacity"

        # 4. Prediction Availability
        if prediction_status is not None:
            if isinstance(prediction_status, str):
                try:
                    pred_enum = PredictionAvailability(prediction_status.upper())
                except ValueError:
                    pred_enum = PredictionAvailability.PREDICTION_PENDING_LAG_POLICY
            else:
                pred_enum = prediction_status
        else:
            pred_enum = PredictionAvailability.PREDICTION_PENDING_LAG_POLICY

        prediction_status_val = pred_enum
        if prediction_status_val == PredictionAvailability.PREDICTION_UNAVAILABLE:
            if first_failed_stage is None:
                first_failed_stage = "prediction"

        # 5. Electrical Compatibility
        electrical_checks: List[Dict[str, Any]] = []
        if electrical_result is not None:
            status_str = electrical_result.overall_status.upper()
            if status_str == ElectricalCompatibility.COMPATIBLE.value:
                electrical_status = ElectricalCompatibility.COMPATIBLE
            elif status_str == ElectricalCompatibility.INCOMPATIBLE.value:
                electrical_status = ElectricalCompatibility.INCOMPATIBLE
                if first_failed_stage is None:
                    first_failed_stage = "electrical"
            else:
                electrical_status = ElectricalCompatibility.NOT_EVALUATED_INSUFFICIENT_SPECIFICATIONS

            electrical_checks = [c.to_dict() for c in electrical_result.checks]
        else:
            electrical_status = ElectricalCompatibility.NOT_EVALUATED_INSUFFICIENT_SPECIFICATIONS

        # 6. Economic Feasibility
        if user_budget is not None:
            cost_to_check = None
            if financial_result is not None:
                if budget_basis.lower() == "gross" and financial_result.c_gross is not None:
                    cost_to_check = financial_result.c_gross
                elif financial_result.c_net is not None:
                    cost_to_check = financial_result.c_net

            if cost_to_check is not None:
                if cost_to_check <= user_budget:
                    economic_status = EconomicFeasibility.PASS
                else:
                    economic_status = EconomicFeasibility.FAIL
                    if first_failed_stage is None:
                        first_failed_stage = "economic"
            else:
                economic_status = EconomicFeasibility.NOT_EVALUATED_MISSING_COSTS
        else:
            if financial_result is not None and financial_result.c_net is not None:
                economic_status = EconomicFeasibility.PASS
            else:
                economic_status = EconomicFeasibility.NOT_EVALUATED_MISSING_COSTS

        # 7. Overall Recommendation Eligibility
        # - Any evaluated gate failure -> RECOMMENDATION_INELIGIBLE
        # - Any mandatory gate unevaluated -> RECOMMENDATION_NOT_EVALUATED
        # - All mandatory evaluated gates pass + capacity flagged sparse -> RECOMMENDATION_FLAGGED
        # - All mandatory evaluated gates pass + capacity eligible -> RECOMMENDATION_ELIGIBLE
        if first_failed_stage is not None:
            overall_eligibility = OverallRecommendationEligibility.RECOMMENDATION_INELIGIBLE
        elif (
            prediction_status_val != PredictionAvailability.PREDICTION_AVAILABLE
            or electrical_status != ElectricalCompatibility.COMPATIBLE
            or economic_status == EconomicFeasibility.NOT_EVALUATED_MISSING_COSTS
        ):
            overall_eligibility = OverallRecommendationEligibility.RECOMMENDATION_NOT_EVALUATED
        elif capacity_eligibility == CapacityEligibility.CAPACITY_FLAGGED_SPARSE:
            overall_eligibility = OverallRecommendationEligibility.RECOMMENDATION_FLAGGED
        else:
            overall_eligibility = OverallRecommendationEligibility.RECOMMENDATION_ELIGIBLE

        return FeasibilityResult(
            geometric=geometric_status,
            catalogue=catalogue_status,
            capacity_support_status=capacity_support_status,
            capacity_eligibility=capacity_eligibility,
            prediction_availability=prediction_status_val,
            electrical=electrical_status,
            electrical_checks=electrical_checks,
            economic=economic_status,
            first_failed_stage=first_failed_stage,
            overall_recommendation_eligibility=overall_eligibility,
        )
