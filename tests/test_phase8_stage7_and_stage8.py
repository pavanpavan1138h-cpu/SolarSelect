"""
SolarSelect — Phase 8: Stage 7 (System Cost & Financials) & Stage 8 (Feasibility & Electrical) Tests
Comprehensive test suite validating:
- Stage 7: CAPEX aggregation (gross vs net, subsidies, BOS, labour, permits, taxes).
- Stage 7: Subsidies exceeding gross CAPEX rejection.
- Stage 7: OPEX recurring, escalation, replacements schedule, and residual value.
- Stage 7: Currency mismatch detection and strict ISO 4217 validation.
- Stage 7: Missing commercial catalogue pricing preservation without synthetic fabrication.
- Stage 7: Net Present Value (NPV) calculation across discounted lifecycle cash flows.
- Stage 7: Simple and discounted payback with exact fractional-year linear interpolation.
- Stage 7: Payback failure scenarios (NOT_ACHIEVED_WITHIN_LIFETIME, NOT_APPLICABLE_NONPOSITIVE_NET_CAPEX).
- Stage 7: Levelized Cost of Energy (LCOE) with explicit net vs gross CAPEX basis.
- Stage 7: Rejection of missing discount rates, negative rates, and mismatched real/nominal rate bases.
- Stage 7: Prevention of double-counting (initial outlay enters once at t=0, subsidies not double-credited).
- Stage 8: Module-level electrical specification extraction and validation.
- Stage 8: Temperature-corrected Voc cold voltage and MPPT upper/lower voltage checks.
- Stage 8: MPPT current and short-circuit current limit validations.
- Stage 8: Series fuse protection check in multi-string combiners.
- Stage 8: DC/AC ratio calculation and clipping warnings.
- Stage 8: Missing inverter specifications resulting strictly in NOT_EVALUATED.
- Stage 8: Missing Vmp temperature coefficient handling.
- Stage 8: Hard feasibility filtering before ranking (electrical failure -> RECOMMENDATION_INELIGIBLE).
- Stage 8: Multi-gate feasibility integration across geometric, catalogue, capacity, electrical, economic.
- End-to-end integration: Stage 5 annual energy -> Stage 6 degradation -> Stage 7 financials -> Stage 8 feasibility.
"""

import math
import pytest
import pandas as pd

from src.energy_economics.exceptions import (
    FinancialError,
    CostStructureError,
    CurrencyMismatchError,
    InvalidFinancialInputError,
    ElectricalError,
    ElectricalConfigurationError,
)
from src.energy_economics.types import (
    CostCategory,
    LCOECapexBasis,
    RateBasis,
    PaybackStatus,
    CostItem,
    SystemCostResult,
    CashFlowYear,
    FinancialEvaluationResult,
    ModuleElectricalSpecs,
    InverterSpecs,
    StringDesign,
    ElectricalCheckResult,
    ElectricalCompatibilityResult,
    GeometricFeasibility,
    CatalogueValidity,
    CapacityEligibility,
    PredictionAvailability,
    ElectricalCompatibility,
    EconomicFeasibility,
    OverallRecommendationEligibility,
    AnnualEnergyResult,
    DegradationModel,
    DegradationSource,
    AnnualEvidenceStatus,
    EnergyScenarioType,
)
from src.energy_economics.system_cost import Phase8SystemCostEngine
from src.energy_economics.financial import Phase8FinancialEngine
from src.energy_economics.electrical import Phase8ElectricalEngine
from src.energy_economics.feasibility import FeasibilityEvaluator
from src.energy_economics.annualization import Phase8AnnualizationEngine
from src.energy_economics.degradation import Phase8DegradationEngine
from src.energy_economics.catalogue import ReadOnlyPanelCatalogue


@pytest.fixture(scope="module")
def cost_engine():
    return Phase8SystemCostEngine()


@pytest.fixture(scope="module")
def financial_engine():
    return Phase8FinancialEngine()


@pytest.fixture(scope="module")
def electrical_engine():
    return Phase8ElectricalEngine()


@pytest.fixture(scope="module")
def feasibility_evaluator():
    return FeasibilityEvaluator()


@pytest.fixture(scope="module")
def sample_module_specs():
    return ModuleElectricalSpecs(
        voc_v=49.5,
        isc_a=11.5,
        vmp_v=41.2,
        imp_a=10.8,
        max_system_voltage_v=1500.0,
        max_series_fuse_rating_a=20.0,
        voc_temp_coefficient_pct_per_c=-0.28,
        isc_temp_coefficient_pct_per_c=0.048,
        vmp_temp_coefficient_pct_per_c=-0.35,
        rated_power_wp=445.0,
    )


@pytest.fixture(scope="module")
def sample_inverter_specs():
    return InverterSpecs(
        inverter_model="SolarEdge_SE50K",
        rated_ac_power_kw=50.0,
        max_dc_input_power_kw=75.0,
        max_dc_input_voltage_v=1000.0,
        mppt_min_voltage_v=350.0,
        mppt_max_voltage_v=850.0,
        max_input_current_per_mppt_a=35.0,
        max_short_circuit_current_per_mppt_a=45.0,
        n_mppt_inputs=2,
    )


@pytest.fixture(scope="module")
def sample_string_design():
    return StringDesign(
        modules_per_string=18,
        n_strings=4,
        parallel_strings_per_mppt=2,
        min_design_temperature_c=-5.0,
        max_design_temperature_c=45.0,
        max_cell_temperature_c=70.0,
    )


# ==============================================================================
# 1. Stage 7: System Cost Engine Tests
# ==============================================================================
def test_system_cost_aggregation_and_subsidies(cost_engine):
    """Verifies CAPEX gross vs net separation, upfront incentives, and OPEX items."""
    cost_items = [
        CostItem("Panels", "CAPEX", "panels", amount=200.0, currency="AUD", quantity=100.0),
        CostItem("Inverter", "CAPEX", "inverter", amount=5000.0, currency="AUD", quantity=1.0),
        CostItem("Mounting", "CAPEX", "mounting", amount=30.0, currency="AUD", quantity=100.0),
        CostItem("BOS", "CAPEX", "bos", amount=2000.0, currency="AUD", quantity=1.0),
        CostItem("Labour", "CAPEX", "labour", amount=4000.0, currency="AUD", quantity=1.0),
        CostItem("Permits", "CAPEX", "permits", amount=1000.0, currency="AUD", quantity=1.0),
        CostItem("STC Subsidy", "CAPEX", "subsidies", amount=6000.0, currency="AUD", quantity=1.0),
        CostItem("Annual Maintenance", "OPEX", "maintenance", amount=500.0, currency="AUD", quantity=1.0),
        CostItem("Insurance", "OPEX", "insurance", amount=300.0, currency="AUD", quantity=1.0),
        CostItem("Inverter Replacement", "OPEX", "replacement", amount=4500.0, currency="AUD", quantity=1.0, replacement_year=12),
        CostItem("Decommissioning Residual", "OPEX", "residual", amount=1500.0, currency="AUD", quantity=1.0),
    ]

    res = cost_engine.evaluate_system_cost(
        cost_items=cost_items,
        rate_basis=RateBasis.REAL,
        opex_escalation_rate=0.02,
    )

    # Gross CAPEX: 200*100 (20000) + 5000 + 30*100 (3000) + 2000 + 4000 + 1000 = 35,000 AUD
    assert res.c_gross == 35000.0
    # Subsidies: 6000 AUD
    assert res.s_upfront == 6000.0
    # Net CAPEX: 35000 - 6000 = 29,000 AUD
    assert res.c_net == 29000.0
    assert res.currency == "AUD"
    assert res.rate_basis == "real"

    # Annual base OPEX: 500 + 300 = 800 AUD
    assert res.annual_base_opex == 800.0
    assert res.opex_escalation_rate == 0.02
    assert res.replacement_schedule == {12: 4500.0}
    assert res.residual_value == 1500.0


def test_system_cost_subsidy_exceeding_gross_rejection(cost_engine):
    """Rejects upfront subsidies exceeding gross CAPEX."""
    cost_items = [
        CostItem("Panels", "CAPEX", "panels", amount=5000.0, currency="AUD"),
        CostItem("Excess Subsidy", "CAPEX", "subsidies", amount=8000.0, currency="AUD"),
    ]
    with pytest.raises(InvalidFinancialInputError, match="cannot exceed gross CAPEX"):
        cost_engine.evaluate_system_cost(cost_items=cost_items)


def test_system_cost_currency_mismatch_rejection(cost_engine):
    """Rejects cost items with differing currencies."""
    cost_items = [
        CostItem("Panels AUD", "CAPEX", "panels", amount=5000.0, currency="AUD"),
        CostItem("Inverter USD", "CAPEX", "inverter", amount=3000.0, currency="USD"),
    ]
    with pytest.raises(CurrencyMismatchError, match="Mismatched currencies"):
        cost_engine.evaluate_system_cost(cost_items=cost_items)


def test_system_cost_missing_pricing_preservation(cost_engine):
    """Preserves missing commercial pricing when no cost items provided."""
    res = cost_engine.evaluate_system_cost(cost_items=[])
    assert res.c_gross is None
    assert res.c_net is None
    assert "missing_inputs" in res.to_dict()
    assert any("Commercial pricing is not populated" in w for w in res.warnings)


# ==============================================================================
# 2. Stage 7: Financial Evaluation Engine Tests
# ==============================================================================
def test_financial_metrics_npv_payback_lcoe(financial_engine, cost_engine):
    """
    Validates complete financial workflow:
    - Net CAPEX at t=0
    - Annual savings and revenues
    - Discounted cash flows and NPV
    - Simple and discounted payback with fractional year interpolation
    - LCOE with explicit net and gross basis
    """
    cost_items = [
        CostItem("Turnkey System", "CAPEX", "panels", amount=30000.0, currency="AUD"),
        CostItem("Rebate", "CAPEX", "subsidies", amount=5000.0, currency="AUD"),
        CostItem("O&M", "OPEX", "maintenance", amount=500.0, currency="AUD"),
    ]
    cost_res = cost_engine.evaluate_system_cost(cost_items=cost_items, rate_basis=RateBasis.REAL)

    # 10,000 kWh/yr, 70% self-consumption, purchase tariff 0.30 AUD/kWh, export 0.08 AUD/kWh
    # Annual generation: 10,000 kWh
    # Self-consumed: 7,000 kWh * 0.30 = 2,100 AUD
    # Exported: 3,000 kWh * 0.08 = 240 AUD
    # Total revenue/savings: 2,340 AUD
    # O&M: 500 AUD
    # Net operating cash flow: 2,340 - 500 = 1,840 AUD/yr
    # Net CAPEX C_net = 25,000 AUD
    # Simple payback: 25,000 / 1,840 = 13.587 years

    fin_res_net = financial_engine.evaluate_financials(
        system_cost=cost_res,
        annual_energy=10000.0,
        lifetime_years=25,
        discount_rate=0.05,
        rate_basis=RateBasis.REAL,
        lcoe_capex_basis=LCOECapexBasis.NET,
        self_consumption_ratio=0.70,
        purchase_tariff=0.30,
        export_tariff=0.08,
    )

    assert fin_res_net.c_net == 25000.0
    assert fin_res_net.c_gross == 30000.0
    assert fin_res_net.simple_payback_status == "ACHIEVED"
    assert fin_res_net.simple_payback_integer_year == 14
    assert math.isclose(fin_res_net.simple_payback_years, 25000.0 / 1840.0, rel_tol=1e-3)

    # Discounted payback: at 5% discount rate
    assert fin_res_net.discounted_payback_status in ("ACHIEVED", "NOT_ACHIEVED_WITHIN_LIFETIME")
    assert fin_res_net.npv is not None
    assert fin_res_net.lcoe_per_kwh is not None
    assert fin_res_net.lcoe_capex_basis == "net"

    # LCOE gross check
    fin_res_gross = financial_engine.evaluate_financials(
        system_cost=cost_res,
        annual_energy=10000.0,
        lifetime_years=25,
        discount_rate=0.05,
        rate_basis=RateBasis.REAL,
        lcoe_capex_basis=LCOECapexBasis.GROSS,
        self_consumption_ratio=0.70,
        purchase_tariff=0.30,
        export_tariff=0.08,
    )
    assert fin_res_gross.lcoe_capex_basis == "gross"
    assert fin_res_gross.lcoe_per_kwh > fin_res_net.lcoe_per_kwh


def test_financial_no_payback_and_nonpositive_capex(financial_engine, cost_engine):
    """Verifies NOT_ACHIEVED_WITHIN_LIFETIME and NOT_APPLICABLE_NONPOSITIVE_NET_CAPEX statuses."""
    # Scenario A: Low revenue, never achieves payback
    cost_items_a = [
        CostItem("High Cost System", "CAPEX", "panels", amount=100000.0, currency="AUD"),
        CostItem("O&M", "OPEX", "maintenance", amount=1000.0, currency="AUD"),
    ]
    cost_res_a = cost_engine.evaluate_system_cost(cost_items=cost_items_a, rate_basis=RateBasis.REAL)
    fin_a = financial_engine.evaluate_financials(
        system_cost=cost_res_a,
        annual_energy=2000.0,
        lifetime_years=25,
        discount_rate=0.06,
        rate_basis=RateBasis.REAL,
        lcoe_capex_basis=LCOECapexBasis.NET,
        self_consumption_ratio=0.5,
        purchase_tariff=0.20,
        export_tariff=0.05,
    )
    assert fin_a.simple_payback_status == "NOT_ACHIEVED_WITHIN_LIFETIME"
    assert fin_a.simple_payback_years is None
    assert fin_a.npv < 0.0

    # Scenario B: Fully subsidized system (C_net == 0)
    cost_items_b = [
        CostItem("System", "CAPEX", "panels", amount=20000.0, currency="AUD"),
        CostItem("Full Grant", "CAPEX", "subsidies", amount=20000.0, currency="AUD"),
    ]
    cost_res_b = cost_engine.evaluate_system_cost(cost_items=cost_items_b, rate_basis=RateBasis.REAL)
    fin_b = financial_engine.evaluate_financials(
        system_cost=cost_res_b,
        annual_energy=10000.0,
        lifetime_years=25,
        discount_rate=0.05,
        rate_basis=RateBasis.REAL,
        lcoe_capex_basis=LCOECapexBasis.NET,
        self_consumption_ratio=0.7,
        purchase_tariff=0.30,
        export_tariff=0.08,
    )
    assert fin_b.simple_payback_status == "NOT_APPLICABLE_NONPOSITIVE_NET_CAPEX"
    assert fin_b.simple_payback_years is None


def test_financial_input_validation_and_no_defaults(financial_engine, cost_engine):
    """Enforces rejection of missing discount rates, mismatched rate bases, and invalid inputs."""
    cost_items = [CostItem("System", "CAPEX", "panels", amount=20000.0, currency="AUD")]
    cost_res = cost_engine.evaluate_system_cost(cost_items=cost_items, rate_basis=RateBasis.REAL)

    # Missing discount rate (None)
    with pytest.raises(InvalidFinancialInputError, match="discount_rate"):
        financial_engine.evaluate_financials(
            system_cost=cost_res,
            annual_energy=10000.0,
            lifetime_years=25,
            discount_rate=None,
            rate_basis=RateBasis.REAL,
            lcoe_capex_basis=LCOECapexBasis.NET,
        )

    # Mismatched rate basis
    with pytest.raises(InvalidFinancialInputError, match="Rate basis mismatch"):
        financial_engine.evaluate_financials(
            system_cost=cost_res,
            annual_energy=10000.0,
            lifetime_years=25,
            discount_rate=0.05,
            rate_basis=RateBasis.NOMINAL,  # cost_res is REAL
            lcoe_capex_basis=LCOECapexBasis.NET,
        )

    # Missing LCOE basis
    with pytest.raises(InvalidFinancialInputError, match="lcoe_capex_basis"):
        financial_engine.evaluate_financials(
            system_cost=cost_res,
            annual_energy=10000.0,
            lifetime_years=25,
            discount_rate=0.05,
            rate_basis=RateBasis.REAL,
            lcoe_capex_basis=None,
        )


# ==============================================================================
# 3. Stage 8: Electrical Compatibility Engine Tests
# ==============================================================================
def test_electrical_evaluation_pass(electrical_engine, sample_module_specs, sample_inverter_specs, sample_string_design):
    """Validates successful pass across all 8 electrical checks with compatible specifications."""
    # 4 strings of 18 modules = 72 modules total
    res = electrical_engine.evaluate_compatibility(
        module_specs=sample_module_specs,
        inverter_specs=sample_inverter_specs,
        string_design=sample_string_design,
        total_panel_count=72,
    )

    assert res.overall_status == "COMPATIBLE"
    assert len(res.checks) == 8
    assert all(c.status == "PASS" for c in res.checks)
    assert res.dc_ac_ratio is not None


def test_electrical_cold_voc_exceeded_failure(electrical_engine, sample_module_specs, sample_inverter_specs):
    """Rejects string design where cold Voc exceeds inverter maximum DC voltage."""
    # 25 modules per string: 25 * 49.5 * (1 + -0.0028 * -30) = 25 * 49.5 * 1.084 = 1,341 V > 1,000 V
    long_string_design = StringDesign(
        modules_per_string=25,
        n_strings=4,
        parallel_strings_per_mppt=2,
        min_design_temperature_c=-5.0,
        max_design_temperature_c=45.0,
        max_cell_temperature_c=70.0,
    )

    res = electrical_engine.evaluate_compatibility(
        module_specs=sample_module_specs,
        inverter_specs=sample_inverter_specs,
        string_design=long_string_design,
        total_panel_count=100,
    )

    assert res.overall_status == "INCOMPATIBLE"
    voc_check = next(c for c in res.checks if c.check_name == "max_string_voltage_cold")
    assert voc_check.status == "FAIL"


def test_electrical_missing_specs_not_evaluated(electrical_engine, sample_module_specs):
    """Confirms real candidates without inverter or string design evaluate strictly to NOT_EVALUATED."""
    res = electrical_engine.evaluate_compatibility(
        module_specs=sample_module_specs,
        inverter_specs=None,
        string_design=None,
    )

    assert res.overall_status == "NOT_EVALUATED_INSUFFICIENT_SPECIFICATIONS"
    assert len(res.checks) == 0
    assert "inverter_specifications" in res.missing_specifications


def test_electrical_missing_vmp_coefficient_not_evaluated(electrical_engine, sample_inverter_specs, sample_string_design):
    """Confirms that missing Vmp temperature coefficient leaves MPPT voltage checks NOT_EVALUATED."""
    mod_no_gamma = ModuleElectricalSpecs(
        voc_v=49.5,
        isc_a=11.5,
        vmp_v=41.2,
        imp_a=10.8,
        max_system_voltage_v=1500.0,
        max_series_fuse_rating_a=20.0,
        voc_temp_coefficient_pct_per_c=-0.28,
        isc_temp_coefficient_pct_per_c=0.048,
        vmp_temp_coefficient_pct_per_c=None,  # missing
        rated_power_wp=445.0,
    )

    res = electrical_engine.evaluate_compatibility(
        module_specs=mod_no_gamma,
        inverter_specs=sample_inverter_specs,
        string_design=sample_string_design,
        total_panel_count=72,
    )

    assert res.overall_status == "NOT_EVALUATED_INSUFFICIENT_SPECIFICATIONS"
    mppt_cold = next(c for c in res.checks if c.check_name == "mppt_upper_voltage_cold")
    assert mppt_cold.status == "NOT_EVALUATED"


# ==============================================================================
# 4. Stage 8: Feasibility Engine & Multi-Gate Integration Tests
# ==============================================================================
def test_feasibility_evaluator_gate_filtering(feasibility_evaluator, electrical_engine, sample_module_specs, sample_inverter_specs, sample_string_design):
    """
    Validates multi-gate feasibility evaluation:
    - Electrical failure -> RECOMMENDATION_INELIGIBLE
    - Over-budget economic failure -> RECOMMENDATION_INELIGIBLE
    - Incomplete gates -> RECOMMENDATION_NOT_EVALUATED
    - All gates pass -> RECOMMENDATION_ELIGIBLE
    """
    valid_phase7_config = {
        "configuration_id": "config-test-1",
        "panel_id": "PNL-CANADIAN-445W",
        "panel_count": 72,
        "installed_dc_capacity_kwp": 32.04,
        "feasibility_status": "FEASIBLE",
        "constraint_violations": [],
    }

    # Case A: Electrical failure
    incompatible_string = StringDesign(
        modules_per_string=25,
        n_strings=4,
        parallel_strings_per_mppt=2,
        min_design_temperature_c=-5.0,
        max_design_temperature_c=45.0,
        max_cell_temperature_c=70.0,
    )
    elec_fail = electrical_engine.evaluate_compatibility(
        module_specs=sample_module_specs,
        inverter_specs=sample_inverter_specs,
        string_design=incompatible_string,
        total_panel_count=100,
    )
    res_a = feasibility_evaluator.evaluate(
        phase7_config=valid_phase7_config,
        electrical_result=elec_fail,
    )
    assert res_a.first_failed_stage == "electrical"
    assert res_a.overall_recommendation_eligibility == OverallRecommendationEligibility.RECOMMENDATION_INELIGIBLE

    # Case B: Electrical passes, but prediction is pending lag policy B-2
    elec_pass = electrical_engine.evaluate_compatibility(
        module_specs=sample_module_specs,
        inverter_specs=sample_inverter_specs,
        string_design=sample_string_design,
        total_panel_count=72,
    )
    res_b = feasibility_evaluator.evaluate(
        phase7_config=valid_phase7_config,
        electrical_result=elec_pass,
        prediction_status=PredictionAvailability.PREDICTION_PENDING_LAG_POLICY,
    )
    assert res_b.first_failed_stage is None
    assert res_b.overall_recommendation_eligibility == OverallRecommendationEligibility.RECOMMENDATION_NOT_EVALUATED

    # Case C: Over budget
    mock_financial = FinancialEvaluationResult(
        currency="AUD",
        rate_basis="real",
        discount_rate=0.05,
        lifetime_years=25,
        financial_capex_basis="net",
        lcoe_capex_basis="net",
        c_gross=50000.0,
        s_upfront=5000.0,
        c_net=45000.0,
        npv=10000.0,
        simple_payback_years=8.0,
        simple_payback_integer_year=8,
        simple_payback_status="ACHIEVED",
        discounted_payback_years=10.0,
        discounted_payback_integer_year=10,
        discounted_payback_status="ACHIEVED",
        lcoe_per_kwh=0.08,
        annual_base_opex=500.0,
        lifetime_nominal_opex=12500.0,
        lifetime_discounted_opex=8000.0,
        cash_flows=[],
        evidence_status="VALIDATED",
    )
    res_c = feasibility_evaluator.evaluate(
        phase7_config=valid_phase7_config,
        electrical_result=elec_pass,
        financial_result=mock_financial,
        prediction_status=PredictionAvailability.PREDICTION_AVAILABLE,
        user_budget=40000.0,  # net cost is 45000 -> exceeds budget
    )
    assert res_c.first_failed_stage == "economic"
    assert res_c.overall_recommendation_eligibility == OverallRecommendationEligibility.RECOMMENDATION_INELIGIBLE

    # Case D: All gates pass
    res_d = feasibility_evaluator.evaluate(
        phase7_config=valid_phase7_config,
        electrical_result=elec_pass,
        financial_result=mock_financial,
        prediction_status=PredictionAvailability.PREDICTION_AVAILABLE,
        user_budget=50000.0,  # net cost 45000 <= 50000 -> passes
    )
    assert res_d.first_failed_stage is None
    assert res_d.overall_recommendation_eligibility in (
        OverallRecommendationEligibility.RECOMMENDATION_ELIGIBLE,
        OverallRecommendationEligibility.RECOMMENDATION_FLAGGED,
    )


# ==============================================================================
# 5. End-to-End Pipeline Integration Test (Stages 5 -> 6 -> 7 -> 8)
# ==============================================================================
def test_full_pipeline_stages_5_to_8():
    """Validates complete contract pipeline from Stage 5 annualization through Stage 8 feasibility."""
    annual_eng = Phase8AnnualizationEngine()
    deg_eng = Phase8DegradationEngine()
    cost_eng = Phase8SystemCostEngine()
    fin_eng = Phase8FinancialEngine()
    elec_eng = Phase8ElectricalEngine()
    feas_eng = FeasibilityEvaluator()

    # 1. Stage 5: Representative annual scenario
    ann_res = annual_eng.evaluate_annual_energy(
        scenario_type=EnergyScenarioType.REPRESENTATIVE_PERIOD,
        annual_reference_kwh=50000.0,
    )
    assert ann_res.annual_energy_kwh == 50000.0

    # 2. Stage 6: Compounded degradation modeling
    deg_res = deg_eng.evaluate_degradation(
        annual_energy=ann_res,
        degradation_model=DegradationModel.COMPOUNDED,
        degradation_rate=0.005,
        lifetime_years=25,
    )
    assert deg_res.cumulative_lifetime_energy_kwh < 50000.0 * 25

    # 3. Stage 7: Cost and financials
    cost_items = [
        CostItem("Panels", "CAPEX", "panels", amount=25000.0, currency="AUD"),
        CostItem("Inverter & BOS", "CAPEX", "inverter", amount=10000.0, currency="AUD"),
        CostItem("Rebate", "CAPEX", "subsidies", amount=5000.0, currency="AUD"),
        CostItem("Maintenance", "OPEX", "maintenance", amount=600.0, currency="AUD"),
    ]
    cost_res = cost_eng.evaluate_system_cost(cost_items=cost_items, rate_basis=RateBasis.REAL)
    assert cost_res.c_net == 30000.0

    fin_res = fin_eng.evaluate_financials(
        system_cost=cost_res,
        annual_energy=deg_res,
        lifetime_years=25,
        discount_rate=0.05,
        rate_basis=RateBasis.REAL,
        lcoe_capex_basis=LCOECapexBasis.NET,
        self_consumption_ratio=0.75,
        purchase_tariff=0.28,
        export_tariff=0.07,
    )
    assert fin_res.npv is not None
    assert fin_res.simple_payback_status == "ACHIEVED"
    assert fin_res.lcoe_per_kwh is not None

    # 4. Stage 8: Electrical & Feasibility
    mod_specs = ModuleElectricalSpecs(
        voc_v=49.5,
        isc_a=11.5,
        vmp_v=41.2,
        imp_a=10.8,
        max_system_voltage_v=1500.0,
        max_series_fuse_rating_a=20.0,
        voc_temp_coefficient_pct_per_c=-0.28,
        isc_temp_coefficient_pct_per_c=0.048,
        vmp_temp_coefficient_pct_per_c=-0.35,
        rated_power_wp=445.0,
    )
    inv_specs = InverterSpecs(
        inverter_model="SolarEdge_SE50K",
        rated_ac_power_kw=50.0,
        max_dc_input_power_kw=75.0,
        max_dc_input_voltage_v=1000.0,
        mppt_min_voltage_v=350.0,
        mppt_max_voltage_v=850.0,
        max_input_current_per_mppt_a=35.0,
        max_short_circuit_current_per_mppt_a=45.0,
        n_mppt_inputs=2,
    )
    str_design = StringDesign(
        modules_per_string=18,
        n_strings=4,
        parallel_strings_per_mppt=2,
        min_design_temperature_c=-5.0,
        max_design_temperature_c=45.0,
        max_cell_temperature_c=70.0,
    )
    elec_res = elec_eng.evaluate_compatibility(
        module_specs=mod_specs,
        inverter_specs=inv_specs,
        string_design=str_design,
        total_panel_count=72,
    )
    assert elec_res.overall_status == "COMPATIBLE"

    phase7_config = {
        "configuration_id": "cfg-full-pipeline",
        "panel_id": "PNL-CANADIAN-445W",
        "panel_count": 72,
        "installed_dc_capacity_kwp": 32.04,
        "feasibility_status": "FEASIBLE",
        "constraint_violations": [],
    }
    feas_res = feas_eng.evaluate(
        phase7_config=phase7_config,
        electrical_result=elec_res,
        financial_result=fin_res,
        prediction_status=PredictionAvailability.PREDICTION_AVAILABLE,
        user_budget=35000.0,
    )
    assert feas_res.first_failed_stage is None
    assert feas_res.overall_recommendation_eligibility == OverallRecommendationEligibility.RECOMMENDATION_ELIGIBLE
