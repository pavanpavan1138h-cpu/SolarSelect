"""
SolarSelect — Phase 8: Types, Enums, and Dataclasses
Authoritative domain models and status codes for Phase 8 Foundation Layer.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, List, Optional, Tuple, Union


class CapacitySupportStatus(str, Enum):
    """Categorical marginal capacity support status codes per Phase 8 specification."""
    SUPPORTED_WITHIN_OBSERVED_DISTRIBUTION = "SUPPORTED_WITHIN_OBSERVED_DISTRIBUTION"
    SPARSE_TRAINING_SUPPORT = "SPARSE_TRAINING_SUPPORT"
    OUT_OF_TRAINING_RANGE = "OUT_OF_TRAINING_RANGE"
    CAPACITY_DISTRIBUTION_UNAVAILABLE = "CAPACITY_DISTRIBUTION_UNAVAILABLE"


class CapacityEligibility(str, Enum):
    """Capacity eligibility status codes reflecting marginal univariate support."""
    CAPACITY_ELIGIBLE = "CAPACITY_ELIGIBLE"
    CAPACITY_FLAGGED_SPARSE = "CAPACITY_FLAGGED_SPARSE"
    CAPACITY_INELIGIBLE_OUT_OF_RANGE = "CAPACITY_INELIGIBLE_OUT_OF_RANGE"
    CAPACITY_INELIGIBLE_UNAVAILABLE = "CAPACITY_INELIGIBLE_UNAVAILABLE"


class OverallRecommendationEligibility(str, Enum):
    """Multi-gate composite recommendation eligibility verdict across all lifecycle gates."""
    RECOMMENDATION_ELIGIBLE = "RECOMMENDATION_ELIGIBLE"
    RECOMMENDATION_FLAGGED = "RECOMMENDATION_FLAGGED"
    RECOMMENDATION_INELIGIBLE = "RECOMMENDATION_INELIGIBLE"
    RECOMMENDATION_NOT_EVALUATED = "RECOMMENDATION_NOT_EVALUATED"


class GeometricFeasibility(str, Enum):
    """Geometric feasibility status inherited from Phase 7."""
    FEASIBLE = "FEASIBLE"
    INFEASIBLE = "INFEASIBLE"


class CatalogueValidity(str, Enum):
    """Catalogue record validity based on Phase 6 physical and electrical schema."""
    VALID = "VALID"
    INVALID = "INVALID"


class PredictionAvailability(str, Enum):
    """Model inference readiness status."""
    PREDICTION_AVAILABLE = "PREDICTION_AVAILABLE"
    PREDICTION_UNAVAILABLE = "PREDICTION_UNAVAILABLE"
    PREDICTION_PENDING_LAG_POLICY = "PREDICTION_PENDING_LAG_POLICY"


class ElectricalCompatibility(str, Enum):
    """Electrical sizing and string configuration compatibility status."""
    COMPATIBLE = "COMPATIBLE"
    INCOMPATIBLE = "INCOMPATIBLE"
    NOT_EVALUATED_INSUFFICIENT_SPECIFICATIONS = "NOT_EVALUATED_INSUFFICIENT_SPECIFICATIONS"


class EconomicFeasibility(str, Enum):
    """Budget and lifecycle economic feasibility status."""
    PASS = "PASS"
    FAIL = "FAIL"
    NOT_EVALUATED_MISSING_COSTS = "NOT_EVALUATED_MISSING_COSTS"


class ReplaySampleClassification(str, Enum):
    """Classification of historical replay observations relative to model training window."""
    IN_SAMPLE = "IN_SAMPLE"
    OUT_OF_SAMPLE = "OUT_OF_SAMPLE"


class ModelVariant(str, Enum):
    """Authorized model variant for Phase 5 Peer Cohort inference."""
    PRIMARY_EXTRA_TREES = "primary_extra_trees"
    FALLBACK_BLEND_50_50 = "fallback_blend_50_50"


class HistoricalYearStatus(str, Enum):
    """Status of historical observation period relative to full annual completeness."""
    VALIDATED_COMPLETE_YEAR = "VALIDATED_COMPLETE_YEAR"
    PARTIAL_PERIOD_NOT_A_FULL_YEAR = "PARTIAL_PERIOD_NOT_A_FULL_YEAR"
    NOT_A_VALIDATED_COMPLETE_YEAR = "NOT_A_VALIDATED_COMPLETE_YEAR"
    NOT_APPLICABLE_SCENARIO = "NOT_APPLICABLE_SCENARIO"

    @classmethod
    def is_incomplete(cls, status: Union["HistoricalYearStatus", str]) -> bool:
        """Determines if a status represents an incomplete or unvalidated annual period."""
        val = status.value if isinstance(status, cls) else str(status)
        return val in {cls.PARTIAL_PERIOD_NOT_A_FULL_YEAR.value, cls.NOT_A_VALIDATED_COMPLETE_YEAR.value}

    @classmethod
    def is_complete(cls, status: Union["HistoricalYearStatus", str]) -> bool:
        """Determines if a status represents a validated complete year."""
        val = status.value if isinstance(status, cls) else str(status)
        return val == cls.VALIDATED_COMPLETE_YEAR.value

    @classmethod
    def normalize_spec_status(cls, status: Union["HistoricalYearStatus", str]) -> "HistoricalYearStatus":
        """
        Normalizes legacy or spec statuses to canonical specification status.
        Maps PARTIAL_PERIOD_NOT_A_FULL_YEAR -> NOT_A_VALIDATED_COMPLETE_YEAR.
        """
        val = status.value if isinstance(status, cls) else str(status)
        if val == cls.PARTIAL_PERIOD_NOT_A_FULL_YEAR.value:
            return cls.NOT_A_VALIDATED_COMPLETE_YEAR
        if val in cls._value2member_map_:
            return cls(val)
        raise ValueError(f"Unknown HistoricalYearStatus: '{status}'")


class AnnualizationMethod(str, Enum):
    """Annualization methods specified in Phase 8 Math Spec Section 4.3."""
    NONE_OBSERVED_ONLY = "none_observed_only"
    FULL_OBSERVED_YEAR = "full_observed_year"
    MONTHLY_COVERAGE_ADJUSTED = "monthly_coverage_adjusted"
    REPRESENTATIVE_YEAR = "representative_year"
    FUTURE_YEAR_SCENARIO = "future_year"


class AnnualEvidenceStatus(str, Enum):
    """Evidence status classifications for annual energy metrics."""
    VALIDATED_COMPLETE_ANNUAL = "VALIDATED_COMPLETE_ANNUAL"
    NOT_A_VALIDATED_COMPLETE_YEAR = "NOT_A_VALIDATED_COMPLETE_YEAR"
    UNVALIDATED_REFERENCE_ONLY = "UNVALIDATED_REFERENCE_ONLY"
    PARTIAL_RESULT_UNVALIDATED = "PARTIAL_RESULT_UNVALIDATED"
    PREDICTION_BLOCKED = "PREDICTION_BLOCKED"
    SCENARIO_BASED_UNVALIDATED = "SCENARIO_BASED_UNVALIDATED"


class DegradationModel(str, Enum):
    """Explicit degradation models supported in Phase 8 Stage 6."""
    COMPOUNDED = "compounded"
    LINEAR = "linear"


class DegradationSource(str, Enum):
    """Source classification for degradation parameters."""
    CATALOGUE = "catalogue"
    USER = "user"
    ASSUMPTION = "assumption"


class EnergyScenarioType(str, Enum):
    """Explicit scenario input modes supported by Phase 8 Stage 3."""
    HISTORICAL_REPLAY = "HISTORICAL_REPLAY"
    REPRESENTATIVE_PERIOD = "REPRESENTATIVE_PERIOD"
    PROSPECTIVE_ROOF = "PROSPECTIVE_ROOF"


class ScenarioEvaluationStatus(str, Enum):
    """Status of scenario evaluation."""
    COMPLETED = "COMPLETED"
    UNAVAILABLE_INPUT_PROFILE = "UNAVAILABLE_INPUT_PROFILE"
    BLOCKED_PENDING_LAG_POLICY = "BLOCKED_PENDING_LAG_POLICY"
    FAILED_VALIDATION = "FAILED_VALIDATION"



@dataclass(frozen=True)
class TrainingDistributionMetrics:
    """Authoritative Peer Cohort training-capacity distribution metrics (22 sites)."""
    n_sites: int = 22
    min_kwp: float = 21.39
    q1_kwp: float = 39.99
    median_kwp: float = 53.96
    mean_kwp: float = 96.86
    sample_std_kwp: float = 124.59
    pop_std_kwp: float = 121.72
    q3_kwp: float = 82.91
    max_kwp: float = 539.80
    core_band_kwp: Tuple[float, float] = (21.39, 100.00)
    sparse_band_kwp: Tuple[float, float] = (100.00, 539.80)
    unique_site_capacities: Tuple[float, ...] = (
        21.39, 24.00, 24.70, 29.76, 31.00, 31.20, 39.90, 40.27, 43.80, 48.00,
        53.76, 54.15, 62.10, 68.00, 75.00, 78.40, 84.42, 94.00, 99.84, 167.97,
        384.12, 539.80
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "n_sites": self.n_sites,
            "min_kwp": self.min_kwp,
            "q1_kwp": self.q1_kwp,
            "median_kwp": self.median_kwp,
            "mean_kwp": self.mean_kwp,
            "sample_std_kwp": self.sample_std_kwp,
            "pop_std_kwp": self.pop_std_kwp,
            "q3_kwp": self.q3_kwp,
            "max_kwp": self.max_kwp,
            "core_band_kwp": list(self.core_band_kwp),
            "sparse_band_kwp": list(self.sparse_band_kwp),
        }


@dataclass(frozen=True)
class CapacitySupportResult:
    """Result of marginal training-capacity support evaluation."""
    status: CapacitySupportStatus
    candidate_kwp: float
    capacity_eligibility: CapacityEligibility
    training_distribution: Optional[TrainingDistributionMetrics] = None
    warning: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "candidate_kwp": self.candidate_kwp,
            "capacity_eligibility": self.capacity_eligibility.value,
            "training_distribution": self.training_distribution.to_dict() if self.training_distribution else None,
            "warning": self.warning,
        }


@dataclass(frozen=True)
class FeasibilityResult:
    """Comprehensive feasibility verdict bundle across all evaluation stages."""
    geometric: GeometricFeasibility
    catalogue: CatalogueValidity
    capacity_support_status: CapacitySupportStatus
    capacity_eligibility: CapacityEligibility
    prediction_availability: PredictionAvailability
    electrical: ElectricalCompatibility
    electrical_checks: List[Dict[str, Any]] = field(default_factory=list)
    economic: EconomicFeasibility = EconomicFeasibility.NOT_EVALUATED_MISSING_COSTS
    first_failed_stage: Optional[str] = None
    overall_recommendation_eligibility: OverallRecommendationEligibility = (
        OverallRecommendationEligibility.RECOMMENDATION_NOT_EVALUATED
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "geometric": self.geometric.value,
            "catalogue": self.catalogue.value,
            "capacity_support_status": self.capacity_support_status.value,
            "capacity_eligibility": self.capacity_eligibility.value,
            "prediction_availability": self.prediction_availability.value,
            "electrical": self.electrical.value,
            "electrical_checks": self.electrical_checks,
            "economic": self.economic.value,
            "first_failed_stage": self.first_failed_stage,
            "overall_recommendation_eligibility": self.overall_recommendation_eligibility.value,
        }


@dataclass(frozen=True)
class DailyEnergyEstimate:
    """Record of a single daily energy estimate with explicit units and precision."""
    site_key: int
    date: str
    historical_installed_capacity_kwp: float
    sample_classification: str
    predicted_specific_yield_kwh_per_kwp_day: float
    raw_mathematical_daily_energy_kwh: float
    accepted_positive_daily_energy_kwh: Optional[float]
    prediction_status: str
    specific_yield_unit: str = "kWh/kWp/day"
    daily_energy_unit: str = "kWh/day"
    actual_target_daily_yield: Optional[float] = None
    actual_daily_energy_kwh: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "site_key": self.site_key,
            "date": self.date,
            "historical_installed_capacity_kwp": self.historical_installed_capacity_kwp,
            "sample_classification": self.sample_classification,
            "predicted_specific_yield_kwh_per_kwp_day": self.predicted_specific_yield_kwh_per_kwp_day,
            "specific_yield_unit": self.specific_yield_unit,
            "raw_mathematical_daily_energy_kwh": self.raw_mathematical_daily_energy_kwh,
            "accepted_positive_daily_energy_kwh": self.accepted_positive_daily_energy_kwh,
            "daily_energy_unit": self.daily_energy_unit,
            "actual_target_daily_yield": self.actual_target_daily_yield,
            "actual_daily_energy_kwh": self.actual_daily_energy_kwh,
            "prediction_status": self.prediction_status,
        }


@dataclass(frozen=True)
class SiteEnergySummary:
    """Observed-period energy summary for a single site."""
    site_key: int
    historical_capacity_kwp: float
    capacity_unit: str = "kWp"
    total_observation_days: int = 0
    valid_prediction_days: int = 0
    negative_prediction_days: int = 0
    in_sample_days: int = 0
    out_of_sample_days: int = 0
    accepted_positive_energy_kwh: float = 0.0
    raw_mathematical_energy_kwh: float = 0.0
    actual_observed_energy_kwh: Optional[float] = None
    energy_unit: str = "kWh"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "site_key": self.site_key,
            "historical_capacity_kwp": self.historical_capacity_kwp,
            "capacity_unit": self.capacity_unit,
            "total_observation_days": self.total_observation_days,
            "valid_prediction_days": self.valid_prediction_days,
            "negative_prediction_days": self.negative_prediction_days,
            "in_sample_days": self.in_sample_days,
            "out_of_sample_days": self.out_of_sample_days,
            "accepted_positive_energy_kwh": self.accepted_positive_energy_kwh,
            "raw_mathematical_energy_kwh": self.raw_mathematical_energy_kwh,
            "actual_observed_energy_kwh": self.actual_observed_energy_kwh,
            "energy_unit": self.energy_unit,
        }


@dataclass(frozen=True)
class EnergyAggregationSummary:
    """Aggregated observed-period energy summary across all sites."""
    cohort: str = "peer_cohort"
    scenario_type: str = "HISTORICAL_REPLAY"
    scenario_status: str = "COMPLETED"
    model_name: str = ""
    model_variant: str = "primary_extra_trees"
    date_range: Dict[str, str] = field(default_factory=dict)
    calendar_days: int = 0
    distinct_observation_dates: int = 0
    missing_calendar_dates: int = 0
    coverage_fraction: float = 0.0
    n_unique_sites: int = 0
    total_daily_records: int = 0
    valid_predictions_count: int = 0
    negative_predictions_count: int = 0
    in_sample_records_count: int = 0
    out_of_sample_records_count: int = 0
    accepted_positive_energy_kwh: float = 0.0
    raw_mathematical_energy_kwh: float = 0.0
    in_sample_accepted_positive_energy_kwh: float = 0.0
    out_of_sample_accepted_positive_energy_kwh: float = 0.0
    actual_observed_total_energy_kwh: Optional[float] = None
    energy_unit: str = "kWh"
    historical_year_status: str = "PARTIAL_PERIOD_NOT_A_FULL_YEAR"
    energy_basis: str = "UNVERIFIED"
    annualization_extrapolation_applied: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cohort": self.cohort,
            "scenario_type": self.scenario_type,
            "scenario_status": self.scenario_status,
            "model_name": self.model_name,
            "model_variant": self.model_variant,
            "date_range": self.date_range,
            "calendar_days": self.calendar_days,
            "distinct_observation_dates": self.distinct_observation_dates,
            "missing_calendar_dates": self.missing_calendar_dates,
            "coverage_fraction": self.coverage_fraction,
            "n_unique_sites": self.n_unique_sites,
            "total_daily_records": self.total_daily_records,
            "valid_predictions_count": self.valid_predictions_count,
            "negative_predictions_count": self.negative_predictions_count,
            "in_sample_records_count": self.in_sample_records_count,
            "out_of_sample_records_count": self.out_of_sample_records_count,
            "accepted_positive_energy_kwh": self.accepted_positive_energy_kwh,
            "raw_mathematical_energy_kwh": self.raw_mathematical_energy_kwh,
            "in_sample_accepted_positive_energy_kwh": self.in_sample_accepted_positive_energy_kwh,
            "out_of_sample_accepted_positive_energy_kwh": self.out_of_sample_accepted_positive_energy_kwh,
            "actual_observed_total_energy_kwh": self.actual_observed_total_energy_kwh,
            "energy_unit": self.energy_unit,
            "historical_year_status": self.historical_year_status,
            "energy_basis": self.energy_basis,
            "annualization_extrapolation_applied": self.annualization_extrapolation_applied,
        }


@dataclass(frozen=True)
class AnnualEnergyResult:
    """Standardized output container for Phase 8 Stage 5 annual energy estimation."""
    annual_energy_kwh: Optional[float]
    observed_period_energy_kwh: float
    annualization_method: str
    historical_year_status: str
    evidence_status: str
    extrapolated: bool
    calendar_days: int
    observation_dates_count: int
    missing_calendar_dates: int
    coverage_fraction: float
    consecutive_complete_months: int
    is_complete_annual_cycle: bool
    energy_basis: str
    raw_mathematical_energy_kwh: float
    accepted_positive_energy_kwh: float
    negative_prediction_count: int
    max_monthly_scaling_factor: Optional[float] = None
    monthly_coverage: Dict[str, float] = field(default_factory=dict)
    legacy_historical_year_status: str = "PARTIAL_PERIOD_NOT_A_FULL_YEAR"
    warnings: List[str] = field(default_factory=list)
    limitations: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "annual_energy_kwh": self.annual_energy_kwh,
            "observed_period_energy_kwh": self.observed_period_energy_kwh,
            "annualization_method": self.annualization_method,
            "historical_year_status": self.historical_year_status,
            "legacy_historical_year_status": self.legacy_historical_year_status,
            "evidence_status": self.evidence_status,
            "extrapolated": self.extrapolated,
            "calendar_days": self.calendar_days,
            "observation_dates_count": self.observation_dates_count,
            "missing_calendar_dates": self.missing_calendar_dates,
            "coverage_fraction": self.coverage_fraction,
            "consecutive_complete_months": self.consecutive_complete_months,
            "is_complete_annual_cycle": self.is_complete_annual_cycle,
            "energy_basis": self.energy_basis,
            "raw_mathematical_energy_kwh": self.raw_mathematical_energy_kwh,
            "accepted_positive_energy_kwh": self.accepted_positive_energy_kwh,
            "negative_prediction_count": self.negative_prediction_count,
            "max_monthly_scaling_factor": self.max_monthly_scaling_factor,
            "monthly_coverage": self.monthly_coverage,
            "warnings": self.warnings,
            "limitations": self.limitations,
            "metadata": self.metadata,
        }


@dataclass(frozen=True)
class LifetimeEnergyBaseline:
    """Constant-performance unadjusted lifetime baseline container."""
    lifetime_years: int
    annual_reference_kwh: Optional[float]
    baseline_lifetime_energy_kwh: Optional[float]
    evidence_status: str
    energy_basis: str = "UNVERIFIED"
    degradation_applied: bool = False
    discounting_applied: bool = False
    calculation_formula: str = "E_lifetime_baseline = E_annual * lifetime_years"
    warnings: List[str] = field(default_factory=list)
    limitations: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "lifetime_years": self.lifetime_years,
            "annual_reference_kwh": self.annual_reference_kwh,
            "baseline_lifetime_energy_kwh": self.baseline_lifetime_energy_kwh,
            "evidence_status": self.evidence_status,
            "energy_basis": self.energy_basis,
            "degradation_applied": self.degradation_applied,
            "discounting_applied": self.discounting_applied,
            "calculation_formula": self.calculation_formula,
            "warnings": self.warnings,
            "limitations": self.limitations,
            "metadata": self.metadata,
        }


@dataclass(frozen=True)
class YearlyDegradationRecord:
    """Individual yearly energy record under degradation."""
    operating_year: int
    calendar_year: Optional[int]
    degradation_factor: float
    annual_energy_kwh: float
    cumulative_energy_kwh: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "operating_year": self.operating_year,
            "calendar_year": self.calendar_year,
            "degradation_factor": self.degradation_factor,
            "annual_energy_kwh": self.annual_energy_kwh,
            "cumulative_energy_kwh": self.cumulative_energy_kwh,
        }


@dataclass(frozen=True)
class DegradationResult:
    """Comprehensive result of Stage 6 degradation modeling."""
    degradation_model: str
    degradation_rate: float
    degradation_rate_pct: float
    degradation_source: str
    degradation_source_note: Optional[str]
    lifetime_years: int
    initial_annual_energy_kwh: float
    cumulative_lifetime_energy_kwh: float
    baseline_lifetime_energy_kwh: float
    lifetime_degradation_loss_kwh: float
    lifetime_loss_fraction: float
    yearly_breakdown: List[YearlyDegradationRecord]
    evidence_status: str
    energy_basis: str = "UNVERIFIED"
    start_year: Optional[int] = None
    catalogue_unverified_model_type: bool = False
    panel_id: Optional[str] = None
    performance_warranty_years: Optional[float] = None
    end_of_warranty_power_pct: Optional[float] = None
    warranty_consistency_checked: bool = False
    warranty_consistency_warning: Optional[str] = None
    provenance_qualification: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    limitations: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "degradation_model": self.degradation_model,
            "degradation_rate": self.degradation_rate,
            "degradation_rate_pct": self.degradation_rate_pct,
            "degradation_source": self.degradation_source,
            "degradation_source_note": self.degradation_source_note,
            "lifetime_years": self.lifetime_years,
            "start_year": self.start_year,
            "initial_annual_energy_kwh": self.initial_annual_energy_kwh,
            "cumulative_lifetime_energy_kwh": self.cumulative_lifetime_energy_kwh,
            "baseline_lifetime_energy_kwh": self.baseline_lifetime_energy_kwh,
            "lifetime_degradation_loss_kwh": self.lifetime_degradation_loss_kwh,
            "lifetime_loss_fraction": self.lifetime_loss_fraction,
            "yearly_breakdown": [r.to_dict() for r in self.yearly_breakdown],
            "evidence_status": self.evidence_status,
            "energy_basis": self.energy_basis,
            "catalogue_unverified_model_type": self.catalogue_unverified_model_type,
            "panel_id": self.panel_id,
            "performance_warranty_years": self.performance_warranty_years,
            "end_of_warranty_power_pct": self.end_of_warranty_power_pct,
            "warranty_consistency_checked": self.warranty_consistency_checked,
            "warranty_consistency_warning": self.warranty_consistency_warning,
            "provenance_qualification": self.provenance_qualification,
            "warnings": self.warnings,
            "limitations": self.limitations,
            "metadata": self.metadata,
        }


# ==============================================================================
# Stage 7: Cost & Financial Types
# ==============================================================================
class CostCategory(str, Enum):
    """Categorical classification of expenditures."""
    CAPEX = "CAPEX"
    OPEX = "OPEX"


class LCOECapexBasis(str, Enum):
    """Initial outlay basis for Levelized Cost of Energy."""
    NET = "net"
    GROSS = "gross"


class RateBasis(str, Enum):
    """Accounting convention for interest rates, escalation, and discounting."""
    REAL = "real"
    NOMINAL = "nominal"


class PaybackStatus(str, Enum):
    """Status classification for investment payback calculation."""
    ACHIEVED = "ACHIEVED"
    NOT_ACHIEVED_WITHIN_LIFETIME = "NOT_ACHIEVED_WITHIN_LIFETIME"
    NOT_APPLICABLE_NONPOSITIVE_NET_CAPEX = "NOT_APPLICABLE_NONPOSITIVE_NET_CAPEX"
    NOT_EVALUATED_MISSING_TARIFFS = "NOT_EVALUATED_MISSING_TARIFFS"


@dataclass(frozen=True)
class CostItem:
    """Individual itemized expenditure record with provenance and accounting attributes."""
    name: str
    category: str  # CAPEX or OPEX
    subcategory: str  # panels, inverter, mounting, bos, labour, permits, taxes, subsidies, maintenance, etc.
    amount: float
    currency: str
    price_date: Optional[str] = None
    price_basis: Optional[str] = None
    source: str = ""
    quantity: float = 1.0
    unit: str = "item"
    tax_included: bool = True
    replacement_year: Optional[int] = None
    escalation_rate: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "category": self.category,
            "subcategory": self.subcategory,
            "amount": self.amount,
            "currency": self.currency,
            "price_date": self.price_date,
            "price_basis": self.price_basis,
            "source": self.source,
            "quantity": self.quantity,
            "unit": self.unit,
            "tax_included": self.tax_included,
            "replacement_year": self.replacement_year,
            "escalation_rate": self.escalation_rate,
        }


@dataclass(frozen=True)
class SystemCostResult:
    """Aggregated system cost structure distinguishing gross CAPEX, subsidies, and net CAPEX."""
    c_gross: Optional[float]
    s_upfront: float
    c_net: Optional[float]
    currency: str
    rate_basis: str
    capex_items: List[CostItem]
    opex_items: List[CostItem]
    annual_base_opex: float
    opex_escalation_rate: float
    replacement_schedule: Dict[int, float]
    residual_value: float
    warnings: List[str] = field(default_factory=list)
    missing_inputs: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "c_gross": self.c_gross,
            "s_upfront": self.s_upfront,
            "c_net": self.c_net,
            "currency": self.currency,
            "rate_basis": self.rate_basis,
            "capex_items": [c.to_dict() for c in self.capex_items],
            "opex_items": [o.to_dict() for o in self.opex_items],
            "annual_base_opex": self.annual_base_opex,
            "opex_escalation_rate": self.opex_escalation_rate,
            "replacement_schedule": self.replacement_schedule,
            "residual_value": self.residual_value,
            "warnings": self.warnings,
            "missing_inputs": self.missing_inputs,
        }


@dataclass(frozen=True)
class CashFlowYear:
    """Annual financial ledger entry for operating year t."""
    operating_year: int
    calendar_year: Optional[int]
    generated_energy_kwh: float
    self_consumed_energy_kwh: Optional[float]
    exported_energy_kwh: Optional[float]
    purchase_tariff: Optional[float]
    export_tariff: Optional[float]
    savings_amount: Optional[float]
    export_revenue: Optional[float]
    recurring_incentives: float
    base_opex: float
    replacement_cost: float
    residual_value: float
    net_cash_flow: float
    discount_factor: float
    discounted_cash_flow: float
    cumulative_cash_flow: float
    cumulative_discounted_cash_flow: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "operating_year": self.operating_year,
            "calendar_year": self.calendar_year,
            "generated_energy_kwh": self.generated_energy_kwh,
            "self_consumed_energy_kwh": self.self_consumed_energy_kwh,
            "exported_energy_kwh": self.exported_energy_kwh,
            "purchase_tariff": self.purchase_tariff,
            "export_tariff": self.export_tariff,
            "savings_amount": self.savings_amount,
            "export_revenue": self.export_revenue,
            "recurring_incentives": self.recurring_incentives,
            "base_opex": self.base_opex,
            "replacement_cost": self.replacement_cost,
            "residual_value": self.residual_value,
            "net_cash_flow": self.net_cash_flow,
            "discount_factor": self.discount_factor,
            "discounted_cash_flow": self.discounted_cash_flow,
            "cumulative_cash_flow": self.cumulative_cash_flow,
            "cumulative_discounted_cash_flow": self.cumulative_discounted_cash_flow,
        }


@dataclass(frozen=True)
class FinancialEvaluationResult:
    """Comprehensive financial metrics and lifecycle cash-flow ledger."""
    currency: str
    rate_basis: str
    discount_rate: float
    lifetime_years: int
    financial_capex_basis: str
    lcoe_capex_basis: str
    c_gross: Optional[float]
    s_upfront: float
    c_net: Optional[float]
    npv: Optional[float]
    simple_payback_years: Optional[float]
    simple_payback_integer_year: Optional[int]
    simple_payback_status: str
    discounted_payback_years: Optional[float]
    discounted_payback_integer_year: Optional[int]
    discounted_payback_status: str
    lcoe_per_kwh: Optional[float]
    annual_base_opex: float
    lifetime_nominal_opex: float
    lifetime_discounted_opex: float
    cash_flows: List[CashFlowYear]
    evidence_status: str
    energy_basis: str = "UNVERIFIED"
    warnings: List[str] = field(default_factory=list)
    limitations: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "currency": self.currency,
            "rate_basis": self.rate_basis,
            "discount_rate": self.discount_rate,
            "lifetime_years": self.lifetime_years,
            "financial_capex_basis": self.financial_capex_basis,
            "lcoe_capex_basis": self.lcoe_capex_basis,
            "c_gross": self.c_gross,
            "s_upfront": self.s_upfront,
            "c_net": self.c_net,
            "npv": self.npv,
            "simple_payback_years": self.simple_payback_years,
            "simple_payback_integer_year": self.simple_payback_integer_year,
            "simple_payback_status": self.simple_payback_status,
            "discounted_payback_years": self.discounted_payback_years,
            "discounted_payback_integer_year": self.discounted_payback_integer_year,
            "discounted_payback_status": self.discounted_payback_status,
            "lcoe_per_kwh": self.lcoe_per_kwh,
            "annual_base_opex": self.annual_base_opex,
            "lifetime_nominal_opex": self.lifetime_nominal_opex,
            "lifetime_discounted_opex": self.lifetime_discounted_opex,
            "cash_flows": [cf.to_dict() for cf in self.cash_flows],
            "evidence_status": self.evidence_status,
            "energy_basis": self.energy_basis,
            "warnings": self.warnings,
            "limitations": self.limitations,
            "metadata": self.metadata,
        }


# ==============================================================================
# Stage 8: Electrical & Feasibility Types
# ==============================================================================
@dataclass(frozen=True)
class ModuleElectricalSpecs:
    """Authoritative module-level nameplate electrical specifications."""
    voc_v: float
    isc_a: float
    vmp_v: float
    imp_a: float
    max_system_voltage_v: float
    max_series_fuse_rating_a: float
    voc_temp_coefficient_pct_per_c: float
    isc_temp_coefficient_pct_per_c: float
    vmp_temp_coefficient_pct_per_c: Optional[float] = None
    rated_power_wp: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "voc_v": self.voc_v,
            "isc_a": self.isc_a,
            "vmp_v": self.vmp_v,
            "imp_a": self.imp_a,
            "max_system_voltage_v": self.max_system_voltage_v,
            "max_series_fuse_rating_a": self.max_series_fuse_rating_a,
            "voc_temp_coefficient_pct_per_c": self.voc_temp_coefficient_pct_per_c,
            "isc_temp_coefficient_pct_per_c": self.isc_temp_coefficient_pct_per_c,
            "vmp_temp_coefficient_pct_per_c": self.vmp_temp_coefficient_pct_per_c,
            "rated_power_wp": self.rated_power_wp,
        }


@dataclass(frozen=True)
class InverterSpecs:
    """Authoritative inverter electrical specifications."""
    inverter_model: str
    rated_ac_power_kw: float
    max_dc_input_power_kw: float
    max_dc_input_voltage_v: float
    mppt_min_voltage_v: float
    mppt_max_voltage_v: float
    max_input_current_per_mppt_a: float
    max_short_circuit_current_per_mppt_a: float
    n_mppt_inputs: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "inverter_model": self.inverter_model,
            "rated_ac_power_kw": self.rated_ac_power_kw,
            "max_dc_input_power_kw": self.max_dc_input_power_kw,
            "max_dc_input_voltage_v": self.max_dc_input_voltage_v,
            "mppt_min_voltage_v": self.mppt_min_voltage_v,
            "mppt_max_voltage_v": self.mppt_max_voltage_v,
            "max_input_current_per_mppt_a": self.max_input_current_per_mppt_a,
            "max_short_circuit_current_per_mppt_a": self.max_short_circuit_current_per_mppt_a,
            "n_mppt_inputs": self.n_mppt_inputs,
        }


@dataclass(frozen=True)
class StringDesign:
    """Design configuration for stringing layout and operating site temperatures."""
    modules_per_string: int
    n_strings: int
    parallel_strings_per_mppt: int
    min_design_temperature_c: float
    max_design_temperature_c: float
    max_cell_temperature_c: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "modules_per_string": self.modules_per_string,
            "n_strings": self.n_strings,
            "parallel_strings_per_mppt": self.parallel_strings_per_mppt,
            "min_design_temperature_c": self.min_design_temperature_c,
            "max_design_temperature_c": self.max_design_temperature_c,
            "max_cell_temperature_c": self.max_cell_temperature_c,
        }


@dataclass(frozen=True)
class ElectricalCheckResult:
    """Detailed verdict and calculation report for an individual electrical engineering check."""
    check_name: str
    status: str  # PASS, FAIL, NOT_EVALUATED
    calculated_value: Optional[float]
    threshold_value: Optional[float]
    unit: str
    details: str
    missing_inputs: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "check_name": self.check_name,
            "status": self.status,
            "calculated_value": self.calculated_value,
            "threshold_value": self.threshold_value,
            "unit": self.unit,
            "details": self.details,
            "missing_inputs": self.missing_inputs,
        }


@dataclass(frozen=True)
class ElectricalCompatibilityResult:
    """Aggregate electrical evaluation report across all engineering checks."""
    overall_status: str  # COMPATIBLE, INCOMPATIBLE, NOT_EVALUATED_INSUFFICIENT_SPECIFICATIONS
    checks: List[ElectricalCheckResult]
    dc_ac_ratio: Optional[float] = None
    warnings: List[str] = field(default_factory=list)
    missing_specifications: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall_status": self.overall_status,
            "checks": [c.to_dict() for c in self.checks],
            "dc_ac_ratio": self.dc_ac_ratio,
            "warnings": self.warnings,
            "missing_specifications": self.missing_specifications,
            "metadata": self.metadata,
        }


# ==============================================================================
# Stage 9: Ranking Types (Pareto & Weighted)
# ==============================================================================
class ParetoStatus(str, Enum):
    """Categorical status of candidate in Pareto dominance evaluation."""
    RANKED = "RANKED"
    NOT_COMPARABLE_MISSING_OBJECTIVE = "NOT_COMPARABLE_MISSING_OBJECTIVE"
    NOT_EVALUATED_UNRESOLVED_GATES = "NOT_EVALUATED_UNRESOLVED_GATES"
    EXCLUDED_INELIGIBLE = "EXCLUDED_INELIGIBLE"
    EXCLUDED_UNSUPPORTED_CAPACITY = "EXCLUDED_UNSUPPORTED_CAPACITY"
    EXTRAPOLATED_CAPACITY_QUARANTINED = "EXTRAPOLATED_CAPACITY_QUARANTINED"


class WeightedRankingStatus(str, Enum):
    """Categorical status of candidate in multi-criteria weighted scoring."""
    RANKED = "RANKED"
    EXCLUDED_MISSING_CRITERION = "EXCLUDED_MISSING_CRITERION"
    EXCLUDED_INELIGIBLE = "EXCLUDED_INELIGIBLE"
    EXCLUDED_UNSUPPORTED_CAPACITY = "EXCLUDED_UNSUPPORTED_CAPACITY"
    EXCLUDED_UNRESOLVED_GATES = "EXCLUDED_UNRESOLVED_GATES"


class RecommendationBasis(str, Enum):
    """Authoritative decision basis selecting the leading recommendation."""
    PARETO = "pareto"
    WEIGHTED = "weighted"
    ENERGY_ONLY = "energy_only"
    NONE = "none"


@dataclass(frozen=True)
class ParetoCandidateResult:
    """Individual candidate ranking output under Pareto dominance."""
    configuration_id: str
    pareto_rank: Optional[int]
    pareto_status: str
    is_non_dominated: bool
    annual_energy_kwh: Optional[float]
    cost_objective_value: Optional[float]
    cost_objective_name: str
    sparse_support_flag: bool = False
    dominated_by: List[str] = field(default_factory=list)
    dominates: List[str] = field(default_factory=list)
    exclusion_reason: Optional[str] = None
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "configuration_id": self.configuration_id,
            "pareto_rank": self.pareto_rank,
            "pareto_status": self.pareto_status,
            "is_non_dominated": self.is_non_dominated,
            "annual_energy_kwh": self.annual_energy_kwh,
            "cost_objective_value": self.cost_objective_value,
            "cost_objective_name": self.cost_objective_name,
            "sparse_support_flag": self.sparse_support_flag,
            "dominated_by": self.dominated_by,
            "dominates": self.dominates,
            "exclusion_reason": self.exclusion_reason,
            "warnings": self.warnings,
        }


@dataclass(frozen=True)
class ParetoRankingResult:
    """Aggregate multi-objective Pareto ranking report."""
    pareto_set: List[str]  # configuration_ids on frontier 1
    fronts: List[List[str]]  # frontier layers [front1, front2, ...]
    candidates: Dict[str, ParetoCandidateResult]
    cost_objective_name: str
    cost_objective_direction: str  # minimize
    energy_only_mode: bool = False
    quarantined_annex: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pareto_set": self.pareto_set,
            "fronts": self.fronts,
            "candidates": {k: v.to_dict() for k, v in self.candidates.items()},
            "cost_objective_name": self.cost_objective_name,
            "cost_objective_direction": self.cost_objective_direction,
            "energy_only_mode": self.energy_only_mode,
            "quarantined_annex": self.quarantined_annex,
            "warnings": self.warnings,
            "metadata": self.metadata,
        }


@dataclass(frozen=True)
class WeightedCandidateResult:
    """Individual candidate ranking output under weighted multi-criteria scoring."""
    configuration_id: str
    weighted_rank: Optional[int]
    weighted_score: Optional[float]
    weighted_status: str
    raw_criteria_values: Dict[str, Optional[float]]
    normalized_criteria_values: Dict[str, Optional[float]]
    sparse_support_flag: bool = False
    exclusion_reason: Optional[str] = None
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "configuration_id": self.configuration_id,
            "weighted_rank": self.weighted_rank,
            "weighted_score": self.weighted_score,
            "weighted_status": self.weighted_status,
            "raw_criteria_values": self.raw_criteria_values,
            "normalized_criteria_values": self.normalized_criteria_values,
            "sparse_support_flag": self.sparse_support_flag,
            "exclusion_reason": self.exclusion_reason,
            "warnings": self.warnings,
        }


@dataclass(frozen=True)
class WeightedRankingResult:
    """Aggregate weighted ranking output and reproducibility specification."""
    ranked_order: List[str]  # configuration_ids ordered by rank
    candidates: Dict[str, WeightedCandidateResult]
    weights: Dict[str, float]
    criteria_directions: Dict[str, str]
    normalisation_bounds: Dict[str, Dict[str, float]]
    non_discriminatory_criteria: List[str]
    excluded_candidates: List[Dict[str, Any]]
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ranked_order": self.ranked_order,
            "candidates": {k: v.to_dict() for k, v in self.candidates.items()},
            "weights": self.weights,
            "criteria_directions": self.criteria_directions,
            "normalisation_bounds": self.normalisation_bounds,
            "non_discriminatory_criteria": self.non_discriminatory_criteria,
            "excluded_candidates": self.excluded_candidates,
            "warnings": self.warnings,
            "metadata": self.metadata,
        }


# ==============================================================================
# Stage 10: Recommendation & Explanation Types
# ==============================================================================
@dataclass(frozen=True)
class RecommendationExplanation:
    """Structured rationale explaining selection, exclusions, trade-offs, and caveats."""
    summary: str
    selection_rationale: str
    non_selected_rationales: Dict[str, str]
    pareto_vs_weighted_alignment: str
    alignment_status: str  # CONSENSUS, DIVERGENT, NOT_APPLICABLE
    tradeoff_analysis: str
    caveats: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "summary": self.summary,
            "selection_rationale": self.selection_rationale,
            "non_selected_rationales": self.non_selected_rationales,
            "pareto_vs_weighted_alignment": self.pareto_vs_weighted_alignment,
            "alignment_status": self.alignment_status,
            "tradeoff_analysis": self.tradeoff_analysis,
            "caveats": self.caveats,
        }


@dataclass(frozen=True)
class RecommendationResult:
    """Authoritative Stage 10 decision outcome conforming to Section 6 schema."""
    configuration_id: Optional[str]
    basis: str  # pareto, weighted, energy_only, none
    overall_recommendation_eligibility: str
    explanation: RecommendationExplanation
    caveats: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "configuration_id": self.configuration_id,
            "basis": self.basis,
            "overall_recommendation_eligibility": self.overall_recommendation_eligibility,
            "explanation": self.explanation.to_dict(),
            "caveats": self.caveats,
            "metadata": self.metadata,
        }





