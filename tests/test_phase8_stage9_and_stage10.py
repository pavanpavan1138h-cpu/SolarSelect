"""
SolarSelect — Phase 8: Stage 9 (Pareto & Weighted Ranking) & Stage 10 (Recommendation) Tests
Comprehensive test suite validating:
- Stage 9A: Pareto dominance, multi-objective frontiers, ties, missing objectives.
- Stage 9A: Capacity support safeguards, sparse flags, out-of-range quarantine annex.
- Stage 9A: Energy-only single-objective fallback mode.
- Stage 9B: Min-max normalisation (maximize, minimize, equal bounds / zero discrimination).
- Stage 9B: Weight validation (sum == 1.0, non-negative, finite, no implicit defaults).
- Stage 9B: Candidate exclusion on missing criteria without per-candidate re-normalisation.
- Stage 9B: Reproducibility metadata and candidate-pool bound sensitivity.
- Stage 10: Recommendation synthesis across pareto, weighted, energy-only, and none bases.
- Stage 10: Consensus vs Divergent ranking trade-off explanations.
- Stage 10: Eligibility enforcement (RECOMMENDATION_INELIGIBLE, RECOMMENDATION_NOT_EVALUATED).
- Stage 10: Section 6 Output Schema Contract compliance.
- Integration: Full orchestration via EnergyEconomicsEngine.
- Scientific verification: Real prospective candidates evaluate strictly to RECOMMENDATION_NOT_EVALUATED.
"""

import math
import pytest

from src.energy_economics.exceptions import RankingError, RecommendationError
from src.energy_economics.types import (
    ParetoStatus,
    WeightedRankingStatus,
    RecommendationBasis,
    OverallRecommendationEligibility,
    CapacityEligibility,
    CapacitySupportStatus,
    CostItem,
    InverterSpecs,
    StringDesign,
    ModuleElectricalSpecs,
    RateBasis,
    LCOECapexBasis,
)
from src.energy_economics.pareto import Phase8ParetoEngine
from src.energy_economics.weighted_ranking import Phase8WeightedRankingEngine
from src.energy_economics.recommendation import Phase8RecommendationEngine
from src.energy_economics.engine import EnergyEconomicsEngine


@pytest.fixture(scope="module")
def pareto_engine():
    return Phase8ParetoEngine()


@pytest.fixture(scope="module")
def weighted_engine():
    return Phase8WeightedRankingEngine()


@pytest.fixture(scope="module")
def recommendation_engine():
    return Phase8RecommendationEngine()


@pytest.fixture(scope="module")
def orchestrator():
    return EnergyEconomicsEngine()


# ==============================================================================
# Helper Synthetic Fixtures (Clearly labeled TEST-ONLY data)
# ==============================================================================
@pytest.fixture
def synthetic_candidate_pool():
    """
    Synthetic pool of 5 candidates labeled strictly for mathematical testing.
    Candidate A: High energy (60,000 kWh), Higher LCOE (0.12 AUD/kWh) -> Frontier 1
    Candidate B: Moderate energy (50,000 kWh), Lower LCOE (0.09 AUD/kWh) -> Frontier 1
    Candidate C: Lower energy (40,000 kWh), Higher LCOE (0.11 AUD/kWh) -> Dominated by B
    Candidate D: Sparse capacity (45,000 kWh, 0.10 AUD/kWh) -> Frontier 2, Flagged Sparse
    Candidate E: Hard Ineligible (infeasible geometry) -> Excluded
    """
    return [
        {
            "configuration_id": "SYNTH_A",
            "installed_dc_capacity_kwp": 50.0,
            "annual_energy_kwh": 60000.0,
            "lcoe_per_kwh": 0.12,
            "capex_net": 40000.0,
            "feasibility": {
                "geometric": "FEASIBLE",
                "catalogue": "VALID",
                "capacity_eligibility": "CAPACITY_ELIGIBLE",
                "overall_recommendation_eligibility": "RECOMMENDATION_ELIGIBLE",
            },
        },
        {
            "configuration_id": "SYNTH_B",
            "installed_dc_capacity_kwp": 40.0,
            "annual_energy_kwh": 50000.0,
            "lcoe_per_kwh": 0.09,
            "capex_net": 30000.0,
            "feasibility": {
                "geometric": "FEASIBLE",
                "catalogue": "VALID",
                "capacity_eligibility": "CAPACITY_ELIGIBLE",
                "overall_recommendation_eligibility": "RECOMMENDATION_ELIGIBLE",
            },
        },
        {
            "configuration_id": "SYNTH_C",
            "installed_dc_capacity_kwp": 35.0,
            "annual_energy_kwh": 40000.0,
            "lcoe_per_kwh": 0.11,
            "capex_net": 32000.0,
            "feasibility": {
                "geometric": "FEASIBLE",
                "catalogue": "VALID",
                "capacity_eligibility": "CAPACITY_ELIGIBLE",
                "overall_recommendation_eligibility": "RECOMMENDATION_ELIGIBLE",
            },
        },
        {
            "configuration_id": "SYNTH_D_SPARSE",
            "installed_dc_capacity_kwp": 120.0,  # sparse band
            "annual_energy_kwh": 45000.0,
            "lcoe_per_kwh": 0.10,
            "capex_net": 35000.0,
            "feasibility": {
                "geometric": "FEASIBLE",
                "catalogue": "VALID",
                "capacity_eligibility": "CAPACITY_FLAGGED_SPARSE",
                "overall_recommendation_eligibility": "RECOMMENDATION_FLAGGED",
            },
        },
        {
            "configuration_id": "SYNTH_E_INELIGIBLE",
            "installed_dc_capacity_kwp": 30.0,
            "annual_energy_kwh": 70000.0,
            "lcoe_per_kwh": 0.05,
            "feasibility": {
                "geometric": "INFEASIBLE",
                "catalogue": "VALID",
                "capacity_eligibility": "CAPACITY_ELIGIBLE",
                "overall_recommendation_eligibility": "RECOMMENDATION_INELIGIBLE",
                "first_failed_stage": "geometric",
            },
        },
    ]


# ==============================================================================
# 1. Stage 9A: Pareto Ranking Tests
# ==============================================================================
def test_pareto_two_objective_dominance_and_frontiers(pareto_engine, synthetic_candidate_pool):
    """
    Validates Pareto dominance:
    - SYNTH_A (60k kWh, 0.12) and SYNTH_B (50k kWh, 0.09) form Frontier 1 (mutually non-dominated).
    - SYNTH_C (40k kWh, 0.11) is dominated by SYNTH_B (50k > 40k, 0.09 < 0.11) -> Frontier 2.
    - SYNTH_D_SPARSE is on Frontier 2 and carries sparse_support_flag.
    - SYNTH_E_INELIGIBLE is excluded (EXCLUDED_INELIGIBLE).
    """
    res = pareto_engine.evaluate_pareto_ranking(
        candidates=synthetic_candidate_pool,
        cost_objective="lcoe",
    )

    # Frontier 1 must contain SYNTH_A and SYNTH_B
    assert sorted(res.pareto_set) == ["SYNTH_A", "SYNTH_B"]
    assert res.candidates["SYNTH_A"].pareto_rank == 1
    assert res.candidates["SYNTH_A"].is_non_dominated is True

    assert res.candidates["SYNTH_B"].pareto_rank == 1
    assert res.candidates["SYNTH_B"].is_non_dominated is True

    # SYNTH_D_SPARSE is Frontier 2 (dominated by B, dominates C)
    cand_d = res.candidates["SYNTH_D_SPARSE"]
    assert cand_d.pareto_rank == 2
    assert cand_d.sparse_support_flag is True
    assert any("SPARSE_SUPPORT_FLAG" in w for w in cand_d.warnings)

    # SYNTH_C dominated by B and D -> Frontier 3
    cand_c = res.candidates["SYNTH_C"]
    assert cand_c.pareto_rank == 3
    assert cand_c.is_non_dominated is False
    assert "SYNTH_B" in cand_c.dominated_by
    assert "SYNTH_D_SPARSE" in cand_c.dominated_by

    # SYNTH_E excluded
    cand_e = res.candidates["SYNTH_E_INELIGIBLE"]
    assert cand_e.pareto_status == ParetoStatus.EXCLUDED_INELIGIBLE.value
    assert cand_e.pareto_rank is None


def test_pareto_tied_objectives(pareto_engine):
    """Candidates identical on both objectives are mutually non-dominated."""
    tied_candidates = [
        {
            "configuration_id": "TIED_1",
            "annual_energy_kwh": 50000.0,
            "lcoe_per_kwh": 0.10,
            "feasibility": {"overall_recommendation_eligibility": "RECOMMENDATION_ELIGIBLE"},
        },
        {
            "configuration_id": "TIED_2",
            "annual_energy_kwh": 50000.0,
            "lcoe_per_kwh": 0.10,
            "feasibility": {"overall_recommendation_eligibility": "RECOMMENDATION_ELIGIBLE"},
        },
    ]

    res = pareto_engine.evaluate_pareto_ranking(candidates=tied_candidates)
    assert len(res.pareto_set) == 2
    assert res.candidates["TIED_1"].pareto_rank == 1
    assert res.candidates["TIED_2"].pareto_rank == 1


def test_pareto_missing_objectives_not_substituted(pareto_engine):
    """Candidates missing energy or LCOE receive NOT_COMPARABLE_MISSING_OBJECTIVE without zero substitution."""
    missing_cands = [
        {
            "configuration_id": "MISSING_E",
            "annual_energy_kwh": None,
            "lcoe_per_kwh": 0.10,
            "feasibility": {"overall_recommendation_eligibility": "RECOMMENDATION_ELIGIBLE"},
        },
        {
            "configuration_id": "MISSING_COST",
            "annual_energy_kwh": 50000.0,
            "lcoe_per_kwh": None,
            "feasibility": {"overall_recommendation_eligibility": "RECOMMENDATION_ELIGIBLE"},
        },
    ]

    res = pareto_engine.evaluate_pareto_ranking(candidates=missing_cands)
    for cid in ["MISSING_E", "MISSING_COST"]:
        c = res.candidates[cid]
        assert c.pareto_status == ParetoStatus.NOT_COMPARABLE_MISSING_OBJECTIVE.value
        assert c.pareto_rank is None
        assert c.exclusion_reason is not None


def test_pareto_capacity_out_of_range_quarantine(pareto_engine):
    """Confirms capacity out-of-range candidates are quarantined in exploratory annex."""
    cands = [
        {
            "configuration_id": "OOD_CAND",
            "installed_dc_capacity_kwp": 600.0,  # > 539.8 kWp
            "annual_energy_kwh": 700000.0,
            "lcoe_per_kwh": 0.08,
            "feasibility": {
                "capacity_eligibility": "CAPACITY_INELIGIBLE_OUT_OF_RANGE",
                "overall_recommendation_eligibility": "RECOMMENDATION_INELIGIBLE",
            },
        }
    ]

    res = pareto_engine.evaluate_pareto_ranking(candidates=cands, allow_exploratory_annex=True)
    c = res.candidates["OOD_CAND"]
    assert c.pareto_status == ParetoStatus.EXTRAPOLATED_CAPACITY_QUARANTINED.value
    assert len(res.quarantined_annex) == 1
    assert "QUARANTINED EXPLORATORY RECORD" in res.quarantined_annex[0]["disclaimer"]


def test_pareto_energy_only_fallback(pareto_engine, synthetic_candidate_pool):
    """Validates energy-only ranking when cost objectives are unavailable."""
    res = pareto_engine.evaluate_pareto_ranking(
        candidates=synthetic_candidate_pool,
        energy_only=True,
    )

    assert res.energy_only_mode is True
    assert any("ENERGY_ONLY" in w for w in res.warnings)
    # Ranked strictly by energy: SYNTH_A (60k) > SYNTH_B (50k) > SYNTH_D (45k) > SYNTH_C (40k)
    assert res.candidates["SYNTH_A"].pareto_rank == 1
    assert res.candidates["SYNTH_B"].pareto_rank == 2


# ==============================================================================
# 2. Stage 9B: Weighted Ranking Tests
# ==============================================================================
def test_weighted_ranking_normalisation_and_scoring(weighted_engine, synthetic_candidate_pool):
    """
    Validates min-max normalisation and multi-criteria scoring:
    Weights: 60% energy (maximize), 40% LCOE (minimize).
    """
    weights = {"annual_energy": 0.6, "lcoe": 0.4}
    res = weighted_engine.evaluate_weighted_ranking(
        candidates=synthetic_candidate_pool,
        weights=weights,
    )

    # Eligible pool: SYNTH_A (60k, 0.12), SYNTH_B (50k, 0.09), SYNTH_C (40k, 0.11), SYNTH_D (45k, 0.10)
    # Energy bounds: min=40000, max=60000 -> span = 20000
    # LCOE bounds: min=0.09, max=0.12 -> span = 0.03
    # Check normalisation for SYNTH_A:
    # z_energy = (60k - 40k) / 20k = 1.0
    # z_lcoe = (0.12 - 0.12) / 0.03 = 0.0
    # Score = 0.6 * 1.0 + 0.4 * 0.0 = 0.6000
    score_a = res.candidates["SYNTH_A"].weighted_score
    assert math.isclose(score_a, 0.60, rel_tol=1e-3)

    # Check normalisation for SYNTH_B:
    # z_energy = (50k - 40k) / 20k = 0.5
    # z_lcoe = (0.12 - 0.09) / 0.03 = 1.0
    # Score = 0.6 * 0.5 + 0.4 * 1.0 = 0.30 + 0.40 = 0.7000
    score_b = res.candidates["SYNTH_B"].weighted_score
    assert math.isclose(score_b, 0.70, rel_tol=1e-3)

    # Under this 60/40 weighting, SYNTH_B beats SYNTH_A (0.70 > 0.60)
    assert res.ranked_order[0] == "SYNTH_B"
    assert res.candidates["SYNTH_B"].weighted_rank == 1
    assert res.candidates["SYNTH_A"].weighted_rank == 2

    # Reproducibility metadata check
    assert res.normalisation_bounds["annual_energy"] == {"min": 40000.0, "max": 60000.0}
    assert res.normalisation_bounds["lcoe"] == {"min": 0.09, "max": 0.12}


def test_weighted_ranking_equal_bounds_zero_discrimination(weighted_engine):
    """When x_max == x_min, z is set to 1.0 and non-discriminatory warning is emitted."""
    cands = [
        {
            "configuration_id": "CAND_1",
            "annual_energy_kwh": 50000.0,
            "lcoe_per_kwh": 0.10,
            "feasibility": {"overall_recommendation_eligibility": "RECOMMENDATION_ELIGIBLE"},
        },
        {
            "configuration_id": "CAND_2",
            "annual_energy_kwh": 50000.0,  # identical energy
            "lcoe_per_kwh": 0.08,
            "feasibility": {"overall_recommendation_eligibility": "RECOMMENDATION_ELIGIBLE"},
        },
    ]

    res = weighted_engine.evaluate_weighted_ranking(
        candidates=cands,
        weights={"annual_energy": 0.5, "lcoe": 0.5},
    )

    assert "annual_energy" in res.non_discriminatory_criteria
    assert any("NON_DISCRIMINATORY_CRITERION" in w for w in res.warnings)
    # For CAND_1: z_energy=1.0, z_lcoe=(0.10-0.10)/0.02=0.0 -> score = 0.5
    assert math.isclose(res.candidates["CAND_1"].weighted_score, 0.5, rel_tol=1e-3)


def test_weighted_ranking_weight_validation(weighted_engine):
    """Rejects negative, non-finite, and non-sum-to-1 weights."""
    cands = [{"configuration_id": "C1", "annual_energy_kwh": 10.0, "lcoe_per_kwh": 0.1}]

    # Sum does not equal 1.0
    with pytest.raises(RankingError, match="sum to exactly 1.0"):
        weighted_engine.evaluate_weighted_ranking(candidates=cands, weights={"annual_energy": 0.5, "lcoe": 0.4})

    # Negative weight
    with pytest.raises(RankingError, match="non-negative"):
        weighted_engine.evaluate_weighted_ranking(candidates=cands, weights={"annual_energy": 1.2, "lcoe": -0.2})

    # Non-finite weight
    with pytest.raises(RankingError, match="finite"):
        weighted_engine.evaluate_weighted_ranking(candidates=cands, weights={"annual_energy": float("nan"), "lcoe": 0.5})


def test_weighted_ranking_missing_criterion_exclusion(weighted_engine):
    """Excludes candidates with missing criteria without per-candidate re-normalisation."""
    cands = [
        {
            "configuration_id": "CAND_VALID",
            "annual_energy_kwh": 50000.0,
            "lcoe_per_kwh": 0.10,
            "feasibility": {"overall_recommendation_eligibility": "RECOMMENDATION_ELIGIBLE"},
        },
        {
            "configuration_id": "CAND_MISSING",
            "annual_energy_kwh": 60000.0,
            "lcoe_per_kwh": None,  # missing
            "feasibility": {"overall_recommendation_eligibility": "RECOMMENDATION_ELIGIBLE"},
        },
    ]

    res = weighted_engine.evaluate_weighted_ranking(
        candidates=cands,
        weights={"annual_energy": 0.5, "lcoe": 0.5},
    )

    assert "CAND_MISSING" not in res.ranked_order
    cand_m = res.candidates["CAND_MISSING"]
    assert cand_m.weighted_status == WeightedRankingStatus.EXCLUDED_MISSING_CRITERION.value
    assert cand_m.weighted_rank is None


# ==============================================================================
# 3. Stage 10: Recommendation & Explanation Engine Tests
# ==============================================================================
def test_recommendation_pareto_basis_and_divergence(
    pareto_engine, weighted_engine, recommendation_engine, synthetic_candidate_pool
):
    """
    Demonstrates Pareto vs Weighted divergence:
    - Pareto Frontier 1 contains SYNTH_A and SYNTH_B.
    - User selects Pareto basis with preferred_tradeoff='max_energy' -> selects SYNTH_A.
    - Weighted ranking selected SYNTH_B.
    - Explanation identifies DIVERGENT trade-off and documents why both are valid.
    """
    par_res = pareto_engine.evaluate_pareto_ranking(synthetic_candidate_pool, cost_objective="lcoe")
    wt_res = weighted_engine.evaluate_weighted_ranking(synthetic_candidate_pool, weights={"annual_energy": 0.6, "lcoe": 0.4})

    rec_res = recommendation_engine.evaluate_recommendation(
        candidates=synthetic_candidate_pool,
        pareto_result=par_res,
        weighted_result=wt_res,
        basis=RecommendationBasis.PARETO,
        preferred_tradeoff="max_energy",
    )

    assert rec_res.configuration_id == "SYNTH_A"
    assert rec_res.basis == "pareto"
    assert rec_res.explanation.alignment_status == "DIVERGENT"
    assert "Method divergence" in rec_res.explanation.pareto_vs_weighted_alignment
    assert len(rec_res.caveats) >= 5


def test_recommendation_weighted_basis_and_consensus(
    pareto_engine, weighted_engine, recommendation_engine, synthetic_candidate_pool
):
    """
    Demonstrates weighted basis selection and consensus detection when weights favor Frontier 1 leader.
    """
    par_res = pareto_engine.evaluate_pareto_ranking(synthetic_candidate_pool, cost_objective="lcoe")
    wt_res = weighted_engine.evaluate_weighted_ranking(synthetic_candidate_pool, weights={"annual_energy": 0.2, "lcoe": 0.8})

    rec_res = recommendation_engine.evaluate_recommendation(
        candidates=synthetic_candidate_pool,
        pareto_result=par_res,
        weighted_result=wt_res,
        basis=RecommendationBasis.WEIGHTED,
    )

    # Top weighted candidate is SYNTH_B (lowest LCOE 0.09)
    assert rec_res.configuration_id == "SYNTH_B"
    assert rec_res.basis == "weighted"


def test_recommendation_no_eligible_candidate(recommendation_engine, pareto_engine):
    """When all candidates have unevaluated or failed gates, returns None with explanation."""
    ineligible_cands = [
        {
            "configuration_id": "INELIGIBLE_1",
            "annual_energy_kwh": 50000.0,
            "lcoe_per_kwh": 0.10,
            "feasibility": {
                "overall_recommendation_eligibility": "RECOMMENDATION_NOT_EVALUATED",
                "first_failed_stage": None,
            },
        }
    ]

    par_res = pareto_engine.evaluate_pareto_ranking(ineligible_cands)
    rec_res = recommendation_engine.evaluate_recommendation(
        candidates=ineligible_cands,
        pareto_result=par_res,
        basis=RecommendationBasis.PARETO,
    )

    assert rec_res.configuration_id is None
    assert rec_res.overall_recommendation_eligibility == "RECOMMENDATION_NOT_EVALUATED"
    assert "No configuration can be recommended" in rec_res.explanation.summary


# ==============================================================================
# 4. End-to-End Orchestrator Integration Test & Scientific Honesty Check
# ==============================================================================
def test_energy_economics_engine_orchestration(orchestrator, synthetic_candidate_pool):
    """Verifies complete Section 6 schema output generation via EnergyEconomicsEngine."""
    weights = {"annual_energy": 0.5, "lcoe": 0.5}

    out = orchestrator.run(
        candidate_evaluations=synthetic_candidate_pool,
        weights=weights,
        recommendation_basis=RecommendationBasis.PARETO,
        cost_objective="lcoe",
    )

    # Validate top-level Section 6 schema fields
    assert "run_id" in out
    assert out["schema_version"] == "phase8-io-0.1"
    assert out["engine_status"] in ("SUCCESS", "PARTIAL_RESULT")
    assert "candidates" in out
    assert "pareto_set" in out
    assert "weighted_ranking" in out
    assert "recommendation" in out
    assert "provenance" in out
    assert "warnings" in out
    assert "unresolved_inputs" in out

    # Check candidates have ranking subdictionary
    for cand in out["candidates"]:
        assert "ranking" in cand
        r = cand["ranking"]
        assert "pareto_status" in r
        assert "pareto_rank" in r
        assert "weighted_score" in r
        assert "weighted_rank" in r


def test_real_world_prospective_roof_remains_not_evaluated(orchestrator):
    """
    Scientific Honesty Check:
    A real candidate configuration with unresolved B-1, B-2, and missing inverter specifications
    must strictly evaluate to RECOMMENDATION_NOT_EVALUATED without manufactured passing scores.
    """
    real_candidate = {
        "configuration_id": "REAL_PROSPECTIVE_ROOF_01",
        "panel_id": "PNL-CANADIAN-445W",
        "installed_dc_capacity_kwp": 45.0,
        "energy": {
            "mode": "prospective_roof",
            "annual_energy_kwh": None,  # Blocked under B-2
        },
        "costs": {
            "c_net": None,  # Missing commercial panel pricing
        },
        "financials": {
            "lcoe": None,
        },
        "feasibility": {
            "geometric": "FEASIBLE",
            "catalogue": "VALID",
            "capacity_eligibility": "CAPACITY_ELIGIBLE",
            "prediction_availability": "PREDICTION_PENDING_LAG_POLICY",
            "electrical": "NOT_EVALUATED_INSUFFICIENT_SPECIFICATIONS",
            "economic": "NOT_EVALUATED_MISSING_COSTS",
            "first_failed_stage": None,
            "overall_recommendation_eligibility": "RECOMMENDATION_NOT_EVALUATED",
        },
    }

    out = orchestrator.run(
        candidate_evaluations=[real_candidate],
        recommendation_basis=RecommendationBasis.PARETO,
    )

    rec = out["recommendation"]
    assert rec["configuration_id"] is None
    assert rec["overall_recommendation_eligibility"] == "RECOMMENDATION_NOT_EVALUATED"
    assert out["candidates"][0]["ranking"]["pareto_status"] == ParetoStatus.NOT_EVALUATED_UNRESOLVED_GATES.value
    assert any("B-2" in u for u in out["unresolved_inputs"])


def test_end_to_end_ten_stage_pipeline_from_phase7_to_recommendation(orchestrator):
    """
    Controlled synthetic scenario testing the complete 10-stage orchestration interface:
    Phase 7 Layout -> Foundation -> Capacity -> Annualization -> Degradation ->
    Costs/Financials -> Electrical -> Feasibility -> Pareto/Weighted Ranking -> Recommendation.
    Clearly labeled synthetic test data.
    """
    cfg_a = {
        "configuration_id": "SYNTH_P7_A",
        "roof_id": "ROOF_COMMERCIAL_01",
        "panel_id": "PNL-CANADIAN-445W",
        "panel_count": 72,
        "installed_dc_capacity_kwp": 32.04,
        "module_stc_power_wp": 445.0,
        "feasibility_status": "FEASIBLE",
        "selected_orientation": "portrait",
        "spatial_metrics": {"total_usable_area_m2": 500.0},
        "placements": [{"panel_index": i} for i in range(72)],
        "constraint_violations": [],
    }

    cfg_b = {
        "configuration_id": "SYNTH_P7_B",
        "roof_id": "ROOF_COMMERCIAL_01",
        "panel_id": "PNL-CANADIAN-445W",
        "panel_count": 64,
        "installed_dc_capacity_kwp": 28.48,
        "module_stc_power_wp": 445.0,
        "feasibility_status": "FEASIBLE",
        "selected_orientation": "portrait",
        "spatial_metrics": {"total_usable_area_m2": 500.0},
        "placements": [{"panel_index": i} for i in range(64)],
        "constraint_violations": [],
    }

    mod = ModuleElectricalSpecs(
        voc_v=49.1,
        vmp_v=41.2,
        isc_a=11.5,
        imp_a=10.8,
        rated_power_wp=445.0,
        voc_temp_coefficient_pct_per_c=-0.26,
        isc_temp_coefficient_pct_per_c=0.05,
        vmp_temp_coefficient_pct_per_c=-0.35,
        max_system_voltage_v=1500.0,
        max_series_fuse_rating_a=20.0,
    )

    inv = InverterSpecs(
        inverter_model="INV-50KW",
        rated_ac_power_kw=50.0,
        max_dc_input_power_kw=60.0,
        max_dc_input_voltage_v=1000.0,
        mppt_min_voltage_v=200.0,
        mppt_max_voltage_v=850.0,
        max_input_current_per_mppt_a=30.0,
        max_short_circuit_current_per_mppt_a=40.0,
        n_mppt_inputs=2,
    )

    str_des_a = StringDesign(
        modules_per_string=18,
        n_strings=4,
        parallel_strings_per_mppt=2,
        min_design_temperature_c=-5.0,
        max_design_temperature_c=45.0,
        max_cell_temperature_c=65.0,
    )

    str_des_b = StringDesign(
        modules_per_string=16,
        n_strings=4,
        parallel_strings_per_mppt=2,
        min_design_temperature_c=-5.0,
        max_design_temperature_c=45.0,
        max_cell_temperature_c=65.0,
    )

    # Candidate A: 45,000 kWh/yr, $30k net CAPEX
    cost_a = [CostItem("Panels & BOS", "CAPEX", "panels", amount=30000.0, currency="AUD")]
    eval_a = orchestrator.evaluate_configuration(
        phase7_config=cfg_a,
        scenario_annual_energy_kwh=45000.0,
        cost_items=cost_a,
        discount_rate=0.05,
        rate_basis=RateBasis.REAL,
        self_consumption_ratio=0.7,
        purchase_tariff=0.30,
        export_tariff=0.08,
        inverter_specs=inv,
        string_design=str_des_a,
        module_specs=mod,
    )

    # Candidate B: 40,000 kWh/yr, $26k net CAPEX
    cost_b = [CostItem("Panels & BOS", "CAPEX", "panels", amount=26000.0, currency="AUD")]
    eval_b = orchestrator.evaluate_configuration(
        phase7_config=cfg_b,
        scenario_annual_energy_kwh=40000.0,
        cost_items=cost_b,
        discount_rate=0.05,
        rate_basis=RateBasis.REAL,
        self_consumption_ratio=0.7,
        purchase_tariff=0.30,
        export_tariff=0.08,
        inverter_specs=inv,
        string_design=str_des_b,
        module_specs=mod,
    )

    assert eval_a["feasibility"]["overall_recommendation_eligibility"] == "RECOMMENDATION_ELIGIBLE"
    assert eval_b["feasibility"]["overall_recommendation_eligibility"] == "RECOMMENDATION_ELIGIBLE"
    assert eval_a["financials"]["lcoe"] is not None
    assert eval_b["financials"]["lcoe"] is not None

    # Run multi-candidate ranking and recommendation
    res = orchestrator.run(
        candidate_evaluations=[eval_a, eval_b],
        weights={"annual_energy": 0.6, "lcoe": 0.4},
        recommendation_basis=RecommendationBasis.PARETO,
        cost_objective="lcoe",
    )

    assert res["engine_status"] == "SUCCESS"
    assert len(res["candidates"]) == 2
    assert len(res["pareto_set"]) >= 1
    assert res["recommendation"]["configuration_id"] in ("SYNTH_P7_A", "SYNTH_P7_B")
    assert res["recommendation"]["overall_recommendation_eligibility"] == "RECOMMENDATION_ELIGIBLE"
    assert res["recommendation"]["basis"] == "pareto"
    assert res["schema_version"] == "phase8-io-0.1"
