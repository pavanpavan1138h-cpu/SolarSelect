"""
SolarSelect — Phase 8: Stage 5 (Annualization & Lifetime Energy) & Stage 6 (Degradation Modelling) Tests
Comprehensive test suite validating:
- Observed-period energy aggregation and calendar boundary coverage.
- Rejection of 365-day simple scaling and unapproved D-5 monthly adjustments.
- Complete-year temporal validation (12 consecutive calendar months requirement).
- Leap-year aware calendar calculations.
- Representative-year scenario ingestion and completeness validation.
- Constant-performance lifetime energy baseline (E_lifetime = E_annual * L).
- Evidence status inheritance and limitation propagation (B-1, B-2, D-4).
- Compound degradation exact arithmetic and closed-form cumulative calculations.
- Linear degradation exact arithmetic and physical positivity constraint enforcement.
- Zero degradation behavior across models.
- Parameter validation (d in [0, 0.05], L in [1, 40], E_1 > 0).
- Catalogue datasheet warranty consistency checks and provenance qualifications.
- Separation of user assumptions from manufacturer warranty figures.
- HistoricalYearStatus backwards compatibility and normalization.
- End-to-end integration between annualization and degradation layers.
"""

import math
import pytest
import pandas as pd
import numpy as np

from src.energy_economics.exceptions import (
    AnnualizationError,
    DegradationError,
    InvalidDegradationInputError,
    ScenarioValidationError,
)
from src.energy_economics.types import (
    HistoricalYearStatus,
    AnnualizationMethod,
    AnnualEvidenceStatus,
    AnnualEnergyResult,
    LifetimeEnergyBaseline,
    DegradationModel,
    DegradationSource,
    EnergyScenarioType,
    ScenarioEvaluationStatus,
    ModelVariant,
)
from src.energy_economics.energy_engine import Phase8EnergyEstimationEngine
from src.energy_economics.annualization import Phase8AnnualizationEngine
from src.energy_economics.degradation import Phase8DegradationEngine
from src.energy_economics.catalogue import ReadOnlyPanelCatalogue


@pytest.fixture(scope="module")
def annualization_engine():
    return Phase8AnnualizationEngine()


@pytest.fixture(scope="module")
def degradation_engine():
    return Phase8DegradationEngine()


@pytest.fixture(scope="module")
def energy_engine():
    return Phase8EnergyEstimationEngine()


@pytest.fixture(scope="module")
def sample_test_slice():
    df = pd.read_csv("data/processed/unisolar/peer_cohort/features.csv")
    return df[
        (df["Date"] >= "2022-03-01") & 
        (df["Date"] <= "2022-03-05")
    ].copy()


# ==============================================================================
# 1. HistoricalYearStatus Compatibility & Status Normalization
# ==============================================================================
def test_historical_year_status_compatibility():
    """Confirms both legacy and specification statuses coexist without breaking Stage 3 contracts."""
    # Existing Stage 3 members
    assert HistoricalYearStatus.PARTIAL_PERIOD_NOT_A_FULL_YEAR.value == "PARTIAL_PERIOD_NOT_A_FULL_YEAR"
    assert HistoricalYearStatus.VALIDATED_COMPLETE_YEAR.value == "VALIDATED_COMPLETE_YEAR"
    assert HistoricalYearStatus.NOT_APPLICABLE_SCENARIO.value == "NOT_APPLICABLE_SCENARIO"

    # Specification member
    assert HistoricalYearStatus.NOT_A_VALIDATED_COMPLETE_YEAR.value == "NOT_A_VALIDATED_COMPLETE_YEAR"

    # Helper methods
    assert HistoricalYearStatus.is_incomplete("PARTIAL_PERIOD_NOT_A_FULL_YEAR") is True
    assert HistoricalYearStatus.is_incomplete("NOT_A_VALIDATED_COMPLETE_YEAR") is True
    assert HistoricalYearStatus.is_incomplete("VALIDATED_COMPLETE_YEAR") is False

    assert HistoricalYearStatus.is_complete("VALIDATED_COMPLETE_YEAR") is True
    assert HistoricalYearStatus.is_complete("NOT_A_VALIDATED_COMPLETE_YEAR") is False

    # Normalization
    norm1 = HistoricalYearStatus.normalize_spec_status(HistoricalYearStatus.PARTIAL_PERIOD_NOT_A_FULL_YEAR)
    assert norm1 == HistoricalYearStatus.NOT_A_VALIDATED_COMPLETE_YEAR

    norm2 = HistoricalYearStatus.normalize_spec_status("NOT_A_VALIDATED_COMPLETE_YEAR")
    assert norm2 == HistoricalYearStatus.NOT_A_VALIDATED_COMPLETE_YEAR


# ==============================================================================
# 2. Stage 5: Observed-Period Aggregation & Incomplete-Year Rejection
# ==============================================================================
def test_observed_period_aggregation_from_stage3(energy_engine, annualization_engine, sample_test_slice):
    """Verifies observed-period energy equals accepted positive energy, with annual_energy null."""
    stage3_res = energy_engine.estimate_energy(
        scenario_type=EnergyScenarioType.HISTORICAL_REPLAY,
        feature_dataset=sample_test_slice,
    )

    stage5_res = annualization_engine.evaluate_annual_energy(stage3_output=stage3_res)

    assert isinstance(stage5_res, AnnualEnergyResult)
    agg = stage3_res["aggregation_summary"]

    # Observed-period energy strictly matches accepted positive generation
    assert math.isclose(stage5_res.observed_period_energy_kwh, agg["accepted_positive_energy_kwh"], rel_tol=1e-5)
    assert math.isclose(stage5_res.accepted_positive_energy_kwh, agg["accepted_positive_energy_kwh"], rel_tol=1e-5)
    assert math.isclose(stage5_res.raw_mathematical_energy_kwh, agg["raw_mathematical_energy_kwh"], rel_tol=1e-5)

    # Incomplete historical period: annual_energy_kwh MUST be None
    assert stage5_res.annual_energy_kwh is None
    assert stage5_res.annualization_method == AnnualizationMethod.NONE_OBSERVED_ONLY.value
    assert stage5_res.extrapolated is False
    assert stage5_res.is_complete_annual_cycle is False

    # Status reconciliation: reports specification status while preserving legacy alias
    assert stage5_res.historical_year_status == HistoricalYearStatus.NOT_A_VALIDATED_COMPLETE_YEAR.value
    assert stage5_res.legacy_historical_year_status == HistoricalYearStatus.PARTIAL_PERIOD_NOT_A_FULL_YEAR.value
    assert stage5_res.evidence_status == AnnualEvidenceStatus.NOT_A_VALIDATED_COMPLETE_YEAR.value


def test_no_365_day_scaling_and_d5_prohibition(annualization_engine):
    """Enforces rejection of daily x 365 scaling and prohibition of Decision D-5 monthly adjustment."""
    # Create a 100-day observed DataFrame
    dates = pd.date_range("2021-05-01", periods=100, freq="D").strftime("%Y-%m-%d").tolist()
    daily_df = pd.DataFrame({
        "date": dates,
        "daily_energy_kwh": [50.0] * 100,
        "accepted_positive_energy_kwh": [50.0] * 100,
        "raw_mathematical_energy_kwh": [50.0] * 100,
        "is_negative_prediction": [False] * 100,
    })

    res = annualization_engine.evaluate_annual_energy(daily_estimates_df=daily_df)

    # Total observed is 5000 kWh. If someone scaled by 365/100, it would be 18250 kWh.
    # Must NOT scale!
    assert res.observed_period_energy_kwh == 5000.0
    assert res.annual_energy_kwh is None
    assert res.extrapolated is False
    assert res.historical_year_status == HistoricalYearStatus.NOT_A_VALIDATED_COMPLETE_YEAR.value

    # Explicit request for D-5 coverage adjustment must raise AnnualizationError
    with pytest.raises(AnnualizationError, match="Decision D-5"):
        annualization_engine.evaluate_annual_energy(
            daily_estimates_df=daily_df,
            request_monthly_coverage_adjustment=True,
        )


def test_complete_year_eligibility_synthetic(annualization_engine):
    """Validates complete-year qualification when exactly 12 complete consecutive months are observed without gaps."""
    # 365 days of 2021 (Jan 1 to Dec 31)
    dates = pd.date_range("2021-01-01", "2021-12-31", freq="D").strftime("%Y-%m-%d").tolist()
    assert len(dates) == 365

    daily_df = pd.DataFrame({
        "date": dates,
        "daily_energy_kwh": [100.0] * 365,
        "accepted_positive_energy_kwh": [100.0] * 365,
        "raw_mathematical_energy_kwh": [100.0] * 365,
        "is_negative_prediction": [False] * 365,
    })

    res = annualization_engine.evaluate_annual_energy(daily_estimates_df=daily_df)

    assert res.is_complete_annual_cycle is True
    assert res.consecutive_complete_months == 12
    assert res.missing_calendar_dates == 0
    assert res.coverage_fraction == 1.0
    assert res.annual_energy_kwh == 36500.0
    assert res.observed_period_energy_kwh == 36500.0
    assert res.annualization_method == AnnualizationMethod.FULL_OBSERVED_YEAR.value
    assert res.historical_year_status == HistoricalYearStatus.VALIDATED_COMPLETE_YEAR.value
    assert res.evidence_status == AnnualEvidenceStatus.VALIDATED_COMPLETE_ANNUAL.value
    assert res.extrapolated is False


def test_incomplete_year_boundary_truncation(annualization_engine):
    """Confirms UNISOLAR-like boundary truncation (May 1 2021 to April 23 2022) has only 11 complete months."""
    dates = pd.date_range("2021-05-01", "2022-04-23", freq="D").strftime("%Y-%m-%d").tolist()
    assert len(dates) == 358

    daily_df = pd.DataFrame({
        "date": dates,
        "daily_energy_kwh": [80.0] * 358,
        "accepted_positive_energy_kwh": [80.0] * 358,
        "raw_mathematical_energy_kwh": [80.0] * 358,
        "is_negative_prediction": [False] * 358,
    })

    res = annualization_engine.evaluate_annual_energy(daily_estimates_df=daily_df)

    # April 2022 is truncated at day 23 -> only 11 complete months (May 2021 - Mar 2022)
    assert res.consecutive_complete_months == 11
    assert res.is_complete_annual_cycle is False
    assert res.annual_energy_kwh is None
    assert res.historical_year_status == HistoricalYearStatus.NOT_A_VALIDATED_COMPLETE_YEAR.value


def test_leap_year_calendar_handling(annualization_engine):
    """Verifies that leap years accurately calculate 366 days instead of hardcoding 365."""
    dates = pd.date_range("2024-01-01", "2024-12-31", freq="D").strftime("%Y-%m-%d").tolist()
    assert len(dates) == 366

    daily_df = pd.DataFrame({
        "date": dates,
        "daily_energy_kwh": [10.0] * 366,
        "accepted_positive_energy_kwh": [10.0] * 366,
        "raw_mathematical_energy_kwh": [10.0] * 366,
        "is_negative_prediction": [False] * 366,
    })

    res = annualization_engine.evaluate_annual_energy(daily_estimates_df=daily_df)
    assert res.calendar_days == 366
    assert res.is_complete_annual_cycle is True
    assert res.consecutive_complete_months == 12
    assert res.annual_energy_kwh == 3660.0


# ==============================================================================
# 3. Stage 5: Representative-Year Scenarios & Prospective Roof Blocking
# ==============================================================================
def test_representative_year_scenario_handling(annualization_engine):
    """Validates representative-year scenario ingestion with provenance and completeness."""
    # Valid direct reference
    res = annualization_engine.evaluate_annual_energy(
        scenario_type=EnergyScenarioType.REPRESENTATIVE_PERIOD,
        annual_reference_kwh=150000.0,
    )

    assert res.annual_energy_kwh == 150000.0
    assert res.annualization_method == AnnualizationMethod.REPRESENTATIVE_YEAR.value
    assert res.historical_year_status == HistoricalYearStatus.NOT_APPLICABLE_SCENARIO.value
    assert res.evidence_status == AnnualEvidenceStatus.SCENARIO_BASED_UNVALIDATED.value

    # Invalid negative reference
    with pytest.raises(AnnualizationError, match="non-negative"):
        annualization_engine.evaluate_annual_energy(
            scenario_type=EnergyScenarioType.REPRESENTATIVE_PERIOD,
            annual_reference_kwh=-500.0,
        )

    # Incomplete representative profile (< 365 rows)
    short_df = pd.DataFrame({"col": range(100)})
    with pytest.raises(ScenarioValidationError, match="at least 365"):
        annualization_engine.evaluate_annual_energy(
            scenario_type=EnergyScenarioType.REPRESENTATIVE_PERIOD,
            representative_profile=short_df,
        )


def test_prospective_roof_blocking_b2(annualization_engine):
    """Confirms prospective candidate roofs are strictly blocked under Blocking Issue B-2."""
    res = annualization_engine.evaluate_annual_energy(
        scenario_type=EnergyScenarioType.PROSPECTIVE_ROOF,
    )

    assert res.annual_energy_kwh is None
    assert res.evidence_status == AnnualEvidenceStatus.PREDICTION_BLOCKED.value
    assert any("B-2" in w for w in res.warnings)


def test_negative_prediction_preservation(annualization_engine):
    """Verifies that negative daily yield predictions are excluded from positive energy and tracked."""
    daily_df = pd.DataFrame({
        "date": ["2021-06-01", "2021-06-02", "2021-06-03"],
        "daily_energy_kwh": [100.0, -15.0, 50.0],
        "accepted_positive_energy_kwh": [100.0, 0.0, 50.0],
        "raw_mathematical_energy_kwh": [100.0, -15.0, 50.0],
        "is_negative_prediction": [False, True, False],
    })

    res = annualization_engine.evaluate_annual_energy(daily_estimates_df=daily_df)
    assert res.accepted_positive_energy_kwh == 150.0
    assert res.raw_mathematical_energy_kwh == 135.0
    assert res.negative_prediction_count == 1


# ==============================================================================
# 4. Stage 5: Constant-Performance Lifetime Baseline
# ==============================================================================
def test_lifetime_baseline_calculation(annualization_engine):
    """Verifies E_lifetime_baseline = E_annual * L arithmetic and property preservation."""
    base = annualization_engine.compute_lifetime_baseline(
        annual_energy_kwh=100000.0,
        lifetime_years=25,
        evidence_status=AnnualEvidenceStatus.SCENARIO_BASED_UNVALIDATED.value,
    )

    assert isinstance(base, LifetimeEnergyBaseline)
    assert base.baseline_lifetime_energy_kwh == 2500000.0
    assert base.lifetime_years == 25
    assert base.annual_reference_kwh == 100000.0
    assert base.evidence_status == AnnualEvidenceStatus.SCENARIO_BASED_UNVALIDATED.value
    assert base.degradation_applied is False
    assert base.discounting_applied is False
    assert base.calculation_formula == "E_lifetime_baseline = E_annual * lifetime_years"


def test_lifetime_baseline_null_when_annual_none(annualization_engine):
    """Confirms lifetime baseline is reported as null when annual energy reference is unavailable."""
    base = annualization_engine.compute_lifetime_baseline(
        annual_energy_kwh=None,
        lifetime_years=25,
    )

    assert base.baseline_lifetime_energy_kwh is None
    assert base.annual_reference_kwh is None
    assert base.evidence_status == AnnualEvidenceStatus.PARTIAL_RESULT_UNVALIDATED.value
    assert any("null (PARTIAL_RESULT)" in w for w in base.warnings)


def test_lifetime_baseline_invalid_inputs(annualization_engine):
    """Rejects invalid lifetime years (non-integer, out-of-bounds) and negative energy."""
    with pytest.raises(AnnualizationError, match="integer"):
        annualization_engine.compute_lifetime_baseline(annual_energy_kwh=10000.0, lifetime_years=25.5)

    with pytest.raises(AnnualizationError, match="integer"):
        annualization_engine.compute_lifetime_baseline(annual_energy_kwh=10000.0, lifetime_years=True)

    with pytest.raises(AnnualizationError, match="between 1 and 40"):
        annualization_engine.compute_lifetime_baseline(annual_energy_kwh=10000.0, lifetime_years=0)

    with pytest.raises(AnnualizationError, match="between 1 and 40"):
        annualization_engine.compute_lifetime_baseline(annual_energy_kwh=10000.0, lifetime_years=50)

    with pytest.raises(AnnualizationError, match="non-negative"):
        annualization_engine.compute_lifetime_baseline(annual_energy_kwh=-10.0, lifetime_years=25)


# ==============================================================================
# 5. Stage 6: Compounded Degradation Modelling
# ==============================================================================
def test_compound_degradation_exact_arithmetic(degradation_engine):
    """
    Verifies compounded degradation formula:
    E_t = E_1 * (1 - d)^(t - 1)
    E_life = E_1 * [1 - (1 - d)^L] / d
    """
    e_1 = 10000.0
    d = 0.005  # 0.5% per year
    l = 25

    res = degradation_engine.evaluate_degradation(
        annual_energy=e_1,
        degradation_model=DegradationModel.COMPOUNDED,
        degradation_rate=d,
        lifetime_years=l,
        start_year=2024,
        degradation_source=DegradationSource.USER,
        degradation_source_note="User conservative estimate",
    )

    assert res.degradation_model == "compounded"
    assert res.degradation_rate == 0.005
    assert res.degradation_rate_pct == 0.5
    assert len(res.yearly_breakdown) == 25

    # Check year 1 and year 25
    yr1 = res.yearly_breakdown[0]
    assert yr1.operating_year == 1
    assert yr1.calendar_year == 2024
    assert math.isclose(yr1.degradation_factor, 1.0)
    assert math.isclose(yr1.annual_energy_kwh, 10000.0)

    yr25 = res.yearly_breakdown[24]
    assert yr25.operating_year == 25
    assert yr25.calendar_year == 2048
    expected_factor_25 = math.pow(1.0 - 0.005, 24)
    assert math.isclose(yr25.degradation_factor, expected_factor_25, rel_tol=1e-6)
    assert math.isclose(yr25.annual_energy_kwh, 10000.0 * expected_factor_25, rel_tol=1e-6)

    # Check closed-form cumulative lifetime energy
    expected_cumulative = e_1 * (1.0 - math.pow(1.0 - d, l)) / d
    assert math.isclose(res.cumulative_lifetime_energy_kwh, expected_cumulative, rel_tol=1e-6)

    # Constant performance baseline
    assert res.baseline_lifetime_energy_kwh == 250000.0
    assert res.lifetime_degradation_loss_kwh == 250000.0 - res.cumulative_lifetime_energy_kwh
    assert res.lifetime_loss_fraction > 0.0


# ==============================================================================
# 6. Stage 6: Linear Degradation Modelling & Positivity Enforcement
# ==============================================================================
def test_linear_degradation_exact_arithmetic(degradation_engine):
    """
    Verifies linear degradation formula:
    E_t = E_1 * [1 - d * (t - 1)]
    E_life = E_1 * [L - d * L*(L-1)/2]
    """
    e_1 = 10000.0
    d = 0.005
    l = 25

    res = degradation_engine.evaluate_degradation(
        annual_energy=e_1,
        degradation_model=DegradationModel.LINEAR,
        degradation_rate=d,
        lifetime_years=l,
        start_year=2024,
    )

    assert res.degradation_model == "linear"
    yr25 = res.yearly_breakdown[24]
    expected_factor_25 = 1.0 - 0.005 * 24  # 1 - 0.12 = 0.88
    assert math.isclose(yr25.degradation_factor, 0.88)
    assert math.isclose(yr25.annual_energy_kwh, 8800.0)

    # Cumulative linear formula: 10000 * [25 - 0.005 * 25*24/2] = 10000 * [25 - 0.005 * 300] = 10000 * 23.5 = 235000
    assert math.isclose(res.cumulative_lifetime_energy_kwh, 235000.0, rel_tol=1e-6)
    assert res.baseline_lifetime_energy_kwh == 250000.0
    assert res.lifetime_degradation_loss_kwh == 15000.0


def test_linear_positivity_constraint_rejection(degradation_engine):
    """Rejects linear degradation when 1 - d*(L-1) <= 0 (generation drops to zero or becomes negative)."""
    # d = 0.05, L = 25 -> 1 - 0.05 * 24 = 1 - 1.2 = -0.2 <= 0
    with pytest.raises(InvalidDegradationInputError, match="positivity constraint"):
        degradation_engine.evaluate_degradation(
            annual_energy=10000.0,
            degradation_model=DegradationModel.LINEAR,
            degradation_rate=0.05,
            lifetime_years=25,
        )


def test_zero_degradation_behavior(degradation_engine):
    """Confirms d = 0 results in constant annual generation and zero degradation loss for both models."""
    for model in [DegradationModel.COMPOUNDED, DegradationModel.LINEAR]:
        res = degradation_engine.evaluate_degradation(
            annual_energy=20000.0,
            degradation_model=model,
            degradation_rate=0.0,
            lifetime_years=30,
        )
        assert res.cumulative_lifetime_energy_kwh == 600000.0
        assert res.baseline_lifetime_energy_kwh == 600000.0
        assert res.lifetime_degradation_loss_kwh == 0.0
        assert res.lifetime_loss_fraction == 0.0
        for yr in res.yearly_breakdown:
            assert yr.degradation_factor == 1.0
            assert yr.annual_energy_kwh == 20000.0


# ==============================================================================
# 7. Stage 6: Parameter Validation & Exception Handling
# ==============================================================================
def test_invalid_degradation_parameters(degradation_engine):
    """Tests rigorous validation of degradation model, rate bounds, and lifetime duration."""
    # Model omitted / None
    with pytest.raises(InvalidDegradationInputError, match="degradation_model"):
        degradation_engine.evaluate_degradation(
            annual_energy=10000.0,
            degradation_model=None,
            degradation_rate=0.01,
        )

    # Unsupported model string
    with pytest.raises(InvalidDegradationInputError, match="Unsupported degradation_model"):
        degradation_engine.evaluate_degradation(
            annual_energy=10000.0,
            degradation_model="exponential",
            degradation_rate=0.01,
        )

    # Degradation rate negative without source note
    with pytest.raises(InvalidDegradationInputError, match="Negative degradation"):
        degradation_engine.evaluate_degradation(
            annual_energy=10000.0,
            degradation_model=DegradationModel.COMPOUNDED,
            degradation_rate=-0.005,
        )

    # Degradation rate non-finite
    with pytest.raises(InvalidDegradationInputError, match="degradation_rate must be finite"):
        degradation_engine.evaluate_degradation(
            annual_energy=10000.0,
            degradation_model=DegradationModel.COMPOUNDED,
            degradation_rate=float("nan"),
        )

    # Degradation rate exceeds 5%/yr (0.05)
    with pytest.raises(InvalidDegradationInputError, match="degradation_rate"):
        degradation_engine.evaluate_degradation(
            annual_energy=10000.0,
            degradation_model=DegradationModel.COMPOUNDED,
            degradation_rate=0.06,
        )

    # Lifetime years not integer
    with pytest.raises(InvalidDegradationInputError, match="lifetime_years"):
        degradation_engine.evaluate_degradation(
            annual_energy=10000.0,
            degradation_model=DegradationModel.COMPOUNDED,
            degradation_rate=0.01,
            lifetime_years=25.0,
        )

    # Lifetime years out of bounds
    with pytest.raises(InvalidDegradationInputError, match="lifetime_years"):
        degradation_engine.evaluate_degradation(
            annual_energy=10000.0,
            degradation_model=DegradationModel.COMPOUNDED,
            degradation_rate=0.01,
            lifetime_years=45,
        )

    # Negative or non-finite annual energy
    with pytest.raises(InvalidDegradationInputError, match="positive finite"):
        degradation_engine.evaluate_degradation(
            annual_energy=-100.0,
            degradation_model=DegradationModel.COMPOUNDED,
            degradation_rate=0.01,
        )


# ==============================================================================
# 8. Stage 6: Catalogue Integration & Warranty Consistency Checks
# ==============================================================================
def test_catalogue_degradation_and_warranty(degradation_engine):
    """
    Validates catalogue datasheet degradation extraction, warning generation for
    unverified model type, warranty mismatch detection, and beyond-warranty extrapolation.
    """
    catalogue = ReadOnlyPanelCatalogue()
    panel_ids = catalogue.list_panel_ids()
    assert len(panel_ids) > 0

    first_panel_id = panel_ids[0]
    panel_rec = catalogue.get_panel(first_panel_id)

    # Catalogue source requires explicit model selection (no default!)
    res = degradation_engine.evaluate_degradation(
        annual_energy=50000.0,
        degradation_model=DegradationModel.LINEAR,
        degradation_source=DegradationSource.CATALOGUE,
        panel_id=first_panel_id,
        lifetime_years=30,  # exceeds warranty if warranty is 25 yrs
    )

    assert res.degradation_source == "catalogue"
    assert res.panel_id == first_panel_id
    assert res.catalogue_unverified_model_type is True
    assert any("DEGRADATION_MODEL_TYPE_NOT_ESTABLISHED_BY_CATALOGUE" in w for w in res.warnings)
    assert res.provenance_qualification is not None

    if panel_rec.performance_warranty_years and 30 > panel_rec.performance_warranty_years:
        assert any("EXTRAPOLATED_BEYOND_WARRANTY" in w for w in res.warnings)


def test_user_vs_catalogue_source_distinction(degradation_engine):
    """Verifies user assumptions are clearly distinguished from manufacturer warranty records."""
    res_user = degradation_engine.evaluate_degradation(
        annual_energy=50000.0,
        degradation_model=DegradationModel.COMPOUNDED,
        degradation_rate=0.007,
        degradation_source=DegradationSource.USER,
        degradation_source_note="Empirical field measurement from adjacent installation",
    )

    assert res_user.degradation_source == "user"
    assert res_user.catalogue_unverified_model_type is False
    assert res_user.degradation_source_note == "Empirical field measurement from adjacent installation"
    assert not any("DEGRADATION_MODEL_TYPE_NOT_ESTABLISHED_BY_CATALOGUE" in w for w in res_user.warnings)


# ==============================================================================
# 9. End-to-End Integration: Annualization -> Degradation
# ==============================================================================
def test_annualization_degradation_end_to_end_integration(annualization_engine, degradation_engine):
    """Demonstrates seamless contract pipeline from Stage 5 AnnualEnergyResult to Stage 6 DegradationResult."""
    # 1. Complete representative annual estimation
    annual_res = annualization_engine.evaluate_annual_energy(
        scenario_type=EnergyScenarioType.REPRESENTATIVE_PERIOD,
        annual_reference_kwh=120000.0,
        evidence_status=AnnualEvidenceStatus.SCENARIO_BASED_UNVALIDATED,
    )
    assert annual_res.annual_energy_kwh == 120000.0

    # 2. Stage 5 baseline
    baseline = annualization_engine.compute_lifetime_baseline(
        annual_energy_kwh=annual_res.annual_energy_kwh,
        lifetime_years=25,
        evidence_status=annual_res.evidence_status,
    )
    assert baseline.baseline_lifetime_energy_kwh == 3000000.0

    # 3. Stage 6 degradation modeling ingesting Stage 5 AnnualEnergyResult directly
    deg_res = degradation_engine.evaluate_degradation(
        annual_energy=annual_res,
        degradation_model=DegradationModel.COMPOUNDED,
        degradation_rate=0.005,
        lifetime_years=25,
    )

    assert deg_res.initial_annual_energy_kwh == 120000.0
    assert deg_res.baseline_lifetime_energy_kwh == baseline.baseline_lifetime_energy_kwh
    assert deg_res.evidence_status == annual_res.evidence_status
    assert deg_res.cumulative_lifetime_energy_kwh < baseline.baseline_lifetime_energy_kwh
    assert math.isclose(
        deg_res.cumulative_lifetime_energy_kwh + deg_res.lifetime_degradation_loss_kwh,
        deg_res.baseline_lifetime_energy_kwh,
        rel_tol=1e-6,
    )


def test_stage6_corrections_negative_degradation_policy(degradation_engine):
    """Verifies that negative degradation is allowed only with source note and emits EXTRAPOLATED_BEYOND_WARRANTY."""
    res = degradation_engine.evaluate_degradation(
        annual_energy=10000.0,
        degradation_model=DegradationModel.COMPOUNDED,
        degradation_rate=-0.005,
        lifetime_years=25,
        degradation_source=DegradationSource.USER,
        degradation_source_note="Experimental module showing initial power stabilization/curing effect",
    )
    assert res.degradation_rate == -0.005
    assert any("EXTRAPOLATED_BEYOND_WARRANTY" in w for w in res.warnings)
    # Annual energy in year 25 is higher than year 1
    assert res.yearly_breakdown[24].annual_energy_kwh > res.yearly_breakdown[0].annual_energy_kwh


def test_stage6_corrections_bound_governance_and_linear_labeling():
    """Verifies proposed bound labeling and explicit linear model alternative assumption labeling."""
    engine_default = Phase8DegradationEngine()
    assert engine_default.degradation_bound_status == "PROPOSED_BOUND_REQUIRING_APPROVAL"

    engine_custom = Phase8DegradationEngine(max_degradation_rate=0.08)
    assert engine_custom.degradation_bound_status == "CONFIGURED_POLICY_OVERRIDE"

    res_comp = engine_default.evaluate_degradation(
        annual_energy=10000.0,
        degradation_model=DegradationModel.COMPOUNDED,
        degradation_rate=0.01,
    )
    assert res_comp.metadata["model_status"] == "SPECIFIED_ORIGINAL_FORMULA"

    res_lin = engine_default.evaluate_degradation(
        annual_energy=10000.0,
        degradation_model=DegradationModel.LINEAR,
        degradation_rate=0.01,
    )
    assert res_lin.metadata["model_status"] == "ALTERNATIVE_MODELLING_ASSUMPTION"
    assert any("LINEAR_MODEL_ALTERNATIVE_ASSUMPTION" in w for w in res_lin.warnings)


def test_stage6_corrections_warranty_tolerance_configuration():
    """Verifies configurable warranty validation tolerance and status metadata."""
    engine_tol = Phase8DegradationEngine(warranty_tolerance=0.05)
    assert engine_tol.warranty_tolerance == 0.05

    res = engine_tol.evaluate_degradation(
        annual_energy=10000.0,
        degradation_model=DegradationModel.COMPOUNDED,
        degradation_rate=0.005,
    )
    assert res.metadata["warranty_tolerance"] == 0.05
    assert res.metadata["warranty_tolerance_status"] == "CONFIGURABLE_VALIDATION_TOLERANCE_NO_ESTABLISHED_STANDARD"


