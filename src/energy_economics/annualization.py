"""
SolarSelect — Phase 8: Stage 5 Annualization & Lifetime Energy Engine
Implements:
- Observed-period energy aggregation and calendar coverage analysis.
- Complete-year temporal validation (12 consecutive calendar months requirement).
- Explicit rejection of 365-day simple scaling and unapproved D-5 monthly coverage adjustments.
- Representative-year scenario ingestion and completeness validation.
- Constant-performance lifetime energy baseline calculation (E_lifetime = E_annual * L).
- Evidence status inheritance and strict preservation of unresolved limitations (B-1, B-2, D-4).
"""

from datetime import datetime, timezone, date
from typing import Dict, Any, List, Optional, Tuple, Union
import calendar
import math
import pandas as pd

from src.energy_economics.exceptions import (
    AnnualizationError,
    ScenarioValidationError,
)
from src.energy_economics.types import (
    HistoricalYearStatus,
    AnnualizationMethod,
    AnnualEvidenceStatus,
    AnnualEnergyResult,
    LifetimeEnergyBaseline,
    EnergyScenarioType,
    ScenarioEvaluationStatus,
)


class Phase8AnnualizationEngine:
    """
    Engine for Phase 8 Stage 5 annual energy estimation and lifetime baselines.
    Conforms strictly to the Phase 8 Mathematical Specification and Session 68 Implementation Plan.
    """

    SCHEMA_VERSION = "phase8-io-0.1"
    STAGE_IDENTIFIER = "stage5_annualization_and_lifetime_baseline"
    ENERGY_BASIS = "UNVERIFIED"
    ENERGY_BASIS_QUALIFICATION = (
        "Phase 5 model target (kWh/kWp/day) documentation states an AC kWh basis, "
        "but original raw inverter telemetry cannot independently verify whether "
        "measurements reflect AC gross, AC net, or DC metering point. "
        "Retained as UNVERIFIED under Phase 8 Blocking Issue B-1."
    )

    PROSPECTIVE_ROOF_LIMITATION = (
        "Prospective candidate roofs lack physical historical telemetry and cannot generate "
        "lagged generation features without an authorized lag policy. "
        "Prediction is strictly blocked under Blocking Issue B-2 (PREDICTION_PENDING_LAG_POLICY)."
    )

    D5_DECISION_NOTE = (
        "Coverage-adjusted monthly annualization remains NOT APPROVED under Decision D-5. "
        "Observed-period energy cannot be extrapolated to full year."
    )

    def __init__(self) -> None:
        pass

    def evaluate_annual_energy(
        self,
        stage3_output: Optional[Dict[str, Any]] = None,
        daily_estimates_df: Optional[pd.DataFrame] = None,
        scenario_type: Union[EnergyScenarioType, str] = EnergyScenarioType.HISTORICAL_REPLAY,
        annual_reference_kwh: Optional[float] = None,
        evidence_status: Optional[Union[AnnualEvidenceStatus, str]] = None,
        representative_profile: Optional[pd.DataFrame] = None,
        request_monthly_coverage_adjustment: bool = False,
    ) -> AnnualEnergyResult:
        """
        Evaluates annual energy according to Phase 8 Stage 5 methodology.

        Args:
            stage3_output: Optional output dictionary from Phase8EnergyEstimationEngine.
            daily_estimates_df: Optional DataFrame of daily estimates with 'date' and energy columns.
            scenario_type: EnergyScenarioType (HISTORICAL_REPLAY, REPRESENTATIVE_PERIOD, PROSPECTIVE_ROOF).
            annual_reference_kwh: Optional explicit annual reference value for manual scenario ingestion.
            evidence_status: Optional explicit evidence status when supplying direct annual reference.
            representative_profile: Optional DataFrame containing complete 29-feature representative rows.
            request_monthly_coverage_adjustment: If True, triggers check against Decision D-5 (NOT APPROVED).

        Returns:
            AnnualEnergyResult dataclass containing full evaluation metrics, status codes, and limitations.
        """
        # Parse scenario type
        if isinstance(scenario_type, str):
            try:
                scenario_enum = EnergyScenarioType(scenario_type.upper())
            except ValueError:
                raise ScenarioValidationError(f"Unsupported scenario_type: '{scenario_type}'")
        else:
            scenario_enum = scenario_type

        # 1. Enforce D-5 Decision Prohibition
        if request_monthly_coverage_adjustment:
            raise AnnualizationError(
                "Coverage-adjusted monthly annualization is NOT APPROVED under Decision D-5. "
                "Monthly extrapolation is prohibited."
            )

        # 2. Dispatch by Scenario Type
        if scenario_enum == EnergyScenarioType.PROSPECTIVE_ROOF:
            return self._evaluate_prospective_roof(stage3_output)

        elif scenario_enum == EnergyScenarioType.REPRESENTATIVE_PERIOD:
            return self._evaluate_representative_scenario(
                stage3_output=stage3_output,
                representative_profile=representative_profile,
                annual_reference_kwh=annual_reference_kwh,
                evidence_status=evidence_status,
            )

        elif scenario_enum == EnergyScenarioType.HISTORICAL_REPLAY:
            return self._evaluate_historical_replay(
                stage3_output=stage3_output,
                daily_estimates_df=daily_estimates_df,
            )

        raise ScenarioValidationError(f"Unhandled scenario enum: {scenario_enum}")

    def _evaluate_prospective_roof(
        self,
        stage3_output: Optional[Dict[str, Any]] = None,
    ) -> AnnualEnergyResult:
        """Handles prospective unbuilt roof evaluation under Blocking Issue B-2."""
        warnings = [
            "Prospective candidate roof evaluation is BLOCKED under Blocking Issue B-2.",
            self.PROSPECTIVE_ROOF_LIMITATION,
        ]
        limitations = [
            "B-1: AC/DC metering point confirmation (energy_basis remains UNVERIFIED)",
            "B-2: Prospective roof lag-yield policy (PREDICTION_PENDING_LAG_POLICY)",
        ]

        metadata: Dict[str, Any] = {
            "scenario_type": EnergyScenarioType.PROSPECTIVE_ROOF.value,
            "prediction_status": "PREDICTION_PENDING_LAG_POLICY",
        }
        if stage3_output and "candidate_roof_evaluation" in stage3_output:
            metadata["candidate_roof_evaluation"] = stage3_output["candidate_roof_evaluation"]

        return AnnualEnergyResult(
            annual_energy_kwh=None,
            observed_period_energy_kwh=0.0,
            annualization_method=AnnualizationMethod.NONE_OBSERVED_ONLY.value,
            historical_year_status=HistoricalYearStatus.NOT_APPLICABLE_SCENARIO.value,
            legacy_historical_year_status=HistoricalYearStatus.NOT_APPLICABLE_SCENARIO.value,
            evidence_status=AnnualEvidenceStatus.PREDICTION_BLOCKED.value,
            extrapolated=False,
            calendar_days=0,
            observation_dates_count=0,
            missing_calendar_dates=0,
            coverage_fraction=0.0,
            consecutive_complete_months=0,
            is_complete_annual_cycle=False,
            energy_basis=self.ENERGY_BASIS,
            raw_mathematical_energy_kwh=0.0,
            accepted_positive_energy_kwh=0.0,
            negative_prediction_count=0,
            warnings=warnings,
            limitations=limitations,
            metadata=metadata,
        )

    def _evaluate_representative_scenario(
        self,
        stage3_output: Optional[Dict[str, Any]] = None,
        representative_profile: Optional[pd.DataFrame] = None,
        annual_reference_kwh: Optional[float] = None,
        evidence_status: Optional[Union[AnnualEvidenceStatus, str]] = None,
    ) -> AnnualEnergyResult:
        """Handles representative-year profile scenario ingestion."""
        # Case A: stage3_output provided
        if stage3_output is not None:
            status = stage3_output.get("scenario_status")
            if status == ScenarioEvaluationStatus.UNAVAILABLE_INPUT_PROFILE.value:
                raise ScenarioValidationError(
                    "Representative-period scenario requires complete 365/366-day profile with verified provenance. "
                    "Input profile was unavailable."
                )

            agg = stage3_output.get("aggregation_summary") or {}
            accepted_kwh = float(agg.get("accepted_positive_energy_kwh", 0.0))
            raw_kwh = float(agg.get("raw_mathematical_energy_kwh", 0.0))
            cal_days = int(agg.get("calendar_days", 0))
            obs_days = int(agg.get("distinct_observation_dates", 0))
            neg_count = int(agg.get("negative_predictions_count", 0))

            if cal_days < 365:
                raise ScenarioValidationError(
                    f"Representative-period scenario requires at least 365 complete days. Found {cal_days} days."
                )

            warnings = list(stage3_output.get("warnings", []))
            warnings.append("Representative scenario annual energy represents simulated scenario, not forecast.")
            limitations = list(stage3_output.get("unresolved_inputs", []))

            return AnnualEnergyResult(
                annual_energy_kwh=accepted_kwh,
                observed_period_energy_kwh=accepted_kwh,
                annualization_method=AnnualizationMethod.REPRESENTATIVE_YEAR.value,
                historical_year_status=HistoricalYearStatus.NOT_APPLICABLE_SCENARIO.value,
                legacy_historical_year_status=HistoricalYearStatus.NOT_APPLICABLE_SCENARIO.value,
                evidence_status=AnnualEvidenceStatus.SCENARIO_BASED_UNVALIDATED.value,
                extrapolated=False,
                calendar_days=cal_days,
                observation_dates_count=obs_days,
                missing_calendar_dates=max(0, cal_days - obs_days),
                coverage_fraction=1.0 if cal_days == obs_days else obs_days / cal_days,
                consecutive_complete_months=12,
                is_complete_annual_cycle=True,
                energy_basis=self.ENERGY_BASIS,
                raw_mathematical_energy_kwh=raw_kwh,
                accepted_positive_energy_kwh=accepted_kwh,
                negative_prediction_count=neg_count,
                warnings=warnings,
                limitations=limitations,
                metadata={"scenario_type": EnergyScenarioType.REPRESENTATIVE_PERIOD.value},
            )

        # Case B: Direct annual reference provided
        if annual_reference_kwh is not None:
            if not math.isfinite(annual_reference_kwh) or annual_reference_kwh < 0:
                raise AnnualizationError(
                    f"annual_reference_kwh must be a non-negative finite number, got {annual_reference_kwh}."
                )
            ev_status = (
                evidence_status.value if isinstance(evidence_status, AnnualEvidenceStatus)
                else (str(evidence_status) if evidence_status else AnnualEvidenceStatus.SCENARIO_BASED_UNVALIDATED.value)
            )

            return AnnualEnergyResult(
                annual_energy_kwh=float(annual_reference_kwh),
                observed_period_energy_kwh=float(annual_reference_kwh),
                annualization_method=AnnualizationMethod.REPRESENTATIVE_YEAR.value,
                historical_year_status=HistoricalYearStatus.NOT_APPLICABLE_SCENARIO.value,
                legacy_historical_year_status=HistoricalYearStatus.NOT_APPLICABLE_SCENARIO.value,
                evidence_status=ev_status,
                extrapolated=False,
                calendar_days=365,
                observation_dates_count=365,
                missing_calendar_dates=0,
                coverage_fraction=1.0,
                consecutive_complete_months=12,
                is_complete_annual_cycle=True,
                energy_basis=self.ENERGY_BASIS,
                raw_mathematical_energy_kwh=float(annual_reference_kwh),
                accepted_positive_energy_kwh=float(annual_reference_kwh),
                negative_prediction_count=0,
                warnings=["Scenario-based annual reference supplied directly without daily telemetry."],
                limitations=["B-1: AC/DC metering point confirmation (energy_basis remains UNVERIFIED)"],
                metadata={"manual_scenario_reference": True},
            )

        # Case C: raw profile provided
        if representative_profile is not None:
            if len(representative_profile) < 365:
                raise ScenarioValidationError(
                    f"Representative profile has {len(representative_profile)} rows; at least 365 required."
                )
            raise ScenarioValidationError(
                "Representative profile must be evaluated through Phase8EnergyEstimationEngine.estimate_energy() "
                "before annualization."
            )

        raise ScenarioValidationError(
            "Representative-period scenario requires either stage3_output or validated annual_reference_kwh."
        )

    def _evaluate_historical_replay(
        self,
        stage3_output: Optional[Dict[str, Any]] = None,
        daily_estimates_df: Optional[pd.DataFrame] = None,
    ) -> AnnualEnergyResult:
        """Evaluates historical replay outputs against complete-year criteria."""
        dates_list: List[str] = []
        accepted_kwh: float = 0.0
        raw_kwh: float = 0.0
        neg_count: int = 0
        cal_days: int = 0
        obs_days: int = 0
        miss_days: int = 0
        coverage_frac: float = 0.0
        start_date_str: Optional[str] = None
        end_date_str: Optional[str] = None
        warnings: List[str] = []
        limitations: List[str] = [
            "B-1: AC/DC metering point confirmation (energy_basis remains UNVERIFIED; no AC/DC conversion applied)",
            "D-5: Coverage-adjusted monthly annualization is NOT APPROVED; observed energy cannot be scaled to annual",
            "Geographical transfer limitation: Model trained on Melbourne peer cohort installations only",
        ]

        # Extract data from stage3_output or daily_estimates_df
        if stage3_output is not None:
            agg = stage3_output.get("aggregation_summary") or {}
            accepted_kwh = float(agg.get("accepted_positive_energy_kwh", 0.0))
            raw_kwh = float(agg.get("raw_mathematical_energy_kwh", 0.0))
            neg_count = int(agg.get("negative_predictions_count", 0))
            cal_days = int(agg.get("calendar_days", 0))
            obs_days = int(agg.get("distinct_observation_dates", 0))
            miss_days = int(agg.get("missing_calendar_dates", 0))
            coverage_frac = float(agg.get("coverage_fraction", 0.0))
            date_range = agg.get("date_range") or {}
            start_date_str = date_range.get("start_date")
            end_date_str = date_range.get("end_date")

            # Extract distinct dates from daily_estimates if present
            daily_estimates = stage3_output.get("daily_estimates", [])
            if daily_estimates:
                dates_list = sorted(list({str(d["date"]) for d in daily_estimates if "date" in d}))
            warnings.extend(stage3_output.get("warnings", []))

        elif daily_estimates_df is not None:
            if daily_estimates_df.empty:
                raise AnnualizationError("daily_estimates_df cannot be empty.")
            if "date" not in daily_estimates_df.columns:
                raise AnnualizationError("daily_estimates_df must contain a 'date' column.")

            dates_list = sorted(list(daily_estimates_df["date"].astype(str).unique()))
            start_date_str = dates_list[0]
            end_date_str = dates_list[-1]

            d_start = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            d_end = datetime.strptime(end_date_str, "%Y-%m-%d").date()
            cal_days = (d_end - d_start).days + 1
            obs_days = len(dates_list)
            miss_days = max(0, cal_days - obs_days)
            coverage_frac = obs_days / cal_days if cal_days > 0 else 0.0

            if "accepted_positive_energy_kwh" in daily_estimates_df.columns:
                accepted_kwh = float(daily_estimates_df["accepted_positive_energy_kwh"].sum())
            elif "daily_energy_kwh" in daily_estimates_df.columns:
                # exclude negatives
                pos_mask = daily_estimates_df["daily_energy_kwh"] > 0
                accepted_kwh = float(daily_estimates_df.loc[pos_mask, "daily_energy_kwh"].sum())
            else:
                accepted_kwh = 0.0

            if "raw_mathematical_energy_kwh" in daily_estimates_df.columns:
                raw_kwh = float(daily_estimates_df["raw_mathematical_energy_kwh"].sum())
            elif "daily_energy_kwh" in daily_estimates_df.columns:
                raw_kwh = float(daily_estimates_df["daily_energy_kwh"].sum())
            else:
                raw_kwh = accepted_kwh

            if "is_negative_prediction" in daily_estimates_df.columns:
                neg_count = int(daily_estimates_df["is_negative_prediction"].sum())
            elif "daily_energy_kwh" in daily_estimates_df.columns:
                neg_count = int((daily_estimates_df["daily_energy_kwh"] < 0).sum())
        else:
            raise AnnualizationError("Either stage3_output or daily_estimates_df must be provided.")

        # Temporal completeness and consecutive calendar month check
        consecutive_complete_months, is_complete_year = self._evaluate_calendar_completeness(
            start_date_str=start_date_str,
            end_date_str=end_date_str,
            observation_dates=dates_list,
        )

        # In UNISOLAR replay or partial observation:
        # Check if missing days exist or incomplete year span
        if not is_complete_year or miss_days > 0:
            # Cannot be certified as a validated complete year
            # Simple daily scaling x 365 is forbidden
            # Monthly coverage adjustment is unapproved (D-5)
            # Therefore: annual_energy_kwh = None, historical_year_status = NOT_A_VALIDATED_COMPLETE_YEAR
            warnings.append(
                "Historical observation period does not meet the requirements for a validated complete annual cycle. "
                "Annual energy is not extrapolated (daily x 365 scaling is prohibited; D-5 monthly adjustment NOT APPROVED). "
                "Only observed-period energy is reported."
            )
            return AnnualEnergyResult(
                annual_energy_kwh=None,
                observed_period_energy_kwh=accepted_kwh,
                annualization_method=AnnualizationMethod.NONE_OBSERVED_ONLY.value,
                historical_year_status=HistoricalYearStatus.NOT_A_VALIDATED_COMPLETE_YEAR.value,
                legacy_historical_year_status=HistoricalYearStatus.PARTIAL_PERIOD_NOT_A_FULL_YEAR.value,
                evidence_status=AnnualEvidenceStatus.NOT_A_VALIDATED_COMPLETE_YEAR.value,
                extrapolated=False,
                calendar_days=cal_days,
                observation_dates_count=obs_days,
                missing_calendar_dates=miss_days,
                coverage_fraction=coverage_frac,
                consecutive_complete_months=consecutive_complete_months,
                is_complete_annual_cycle=False,
                energy_basis=self.ENERGY_BASIS,
                raw_mathematical_energy_kwh=raw_kwh,
                accepted_positive_energy_kwh=accepted_kwh,
                negative_prediction_count=neg_count,
                warnings=warnings,
                limitations=limitations,
                metadata={
                    "start_date": start_date_str,
                    "end_date": end_date_str,
                    "rejection_reason": (
                        f"Incomplete annual period: {consecutive_complete_months} consecutive complete months "
                        f"(>=12 required) and {miss_days} missing calendar dates."
                    ),
                },
            )

        # If exactly 12 complete consecutive months AND zero missing days (full observed year)
        return AnnualEnergyResult(
            annual_energy_kwh=accepted_kwh,
            observed_period_energy_kwh=accepted_kwh,
            annualization_method=AnnualizationMethod.FULL_OBSERVED_YEAR.value,
            historical_year_status=HistoricalYearStatus.VALIDATED_COMPLETE_YEAR.value,
            legacy_historical_year_status=HistoricalYearStatus.VALIDATED_COMPLETE_YEAR.value,
            evidence_status=AnnualEvidenceStatus.VALIDATED_COMPLETE_ANNUAL.value,
            extrapolated=False,
            calendar_days=cal_days,
            observation_dates_count=obs_days,
            missing_calendar_dates=0,
            coverage_fraction=1.0,
            consecutive_complete_months=12,
            is_complete_annual_cycle=True,
            energy_basis=self.ENERGY_BASIS,
            raw_mathematical_energy_kwh=raw_kwh,
            accepted_positive_energy_kwh=accepted_kwh,
            negative_prediction_count=neg_count,
            warnings=warnings,
            limitations=limitations,
            metadata={"start_date": start_date_str, "end_date": end_date_str},
        )

    def _evaluate_calendar_completeness(
        self,
        start_date_str: Optional[str],
        end_date_str: Optional[str],
        observation_dates: List[str],
    ) -> Tuple[int, bool]:
        """
        Determines the count of consecutive complete calendar months and complete-year qualification.
        A complete calendar month starts on day 1 and ends on the last calendar day of that month.
        A complete annual cycle requires >= 12 consecutive complete calendar months.
        """
        if not start_date_str or not end_date_str:
            return 0, False

        try:
            d_start = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            d_end = datetime.strptime(end_date_str, "%Y-%m-%d").date()
        except ValueError:
            return 0, False

        if d_end < d_start:
            return 0, False

        # Identify all calendar months in span
        # For each (year, month), check if complete (starts on 1st, ends on last day)
        current_year = d_start.year
        current_month = d_start.month
        end_year = d_end.year
        end_month = d_end.month

        complete_months_count = 0
        while (current_year < end_year) or (current_year == end_year and current_month <= end_month):
            days_in_month = calendar.monthrange(current_year, current_month)[1]
            month_start = date(current_year, current_month, 1)
            month_end = date(current_year, current_month, days_in_month)

            # Check if this entire calendar month falls within [d_start, d_end]
            if month_start >= d_start and month_end <= d_end:
                complete_months_count += 1
            else:
                # partial month at boundary
                pass

            if current_month == 12:
                current_year += 1
                current_month = 1
            else:
                current_month += 1

        is_complete_year = complete_months_count >= 12
        return complete_months_count, is_complete_year

    def compute_lifetime_baseline(
        self,
        annual_energy_kwh: Optional[float],
        lifetime_years: int = 25,
        evidence_status: Optional[str] = None,
        warnings: Optional[List[str]] = None,
        limitations: Optional[List[str]] = None,
    ) -> LifetimeEnergyBaseline:
        """
        Computes the unadjusted constant-performance lifetime energy baseline:
            E_lifetime_baseline = E_annual * lifetime_years
        Inherits the evidence status and limitations from the annual reference.
        Strictly forbids physical degradation or financial discounting in this baseline.
        """
        # Validate lifetime_years
        if not isinstance(lifetime_years, int) or isinstance(lifetime_years, bool):
            raise AnnualizationError(
                f"lifetime_years must be an integer, got {type(lifetime_years).__name__}: {lifetime_years}"
            )
        if lifetime_years < 1 or lifetime_years > 40:
            raise AnnualizationError(
                f"lifetime_years must be between 1 and 40 years, got {lifetime_years}."
            )

        active_warnings = list(warnings or [])
        active_limitations = list(limitations or [])

        # If annual_energy_kwh is None (partial historical replay or blocked prospective roof)
        if annual_energy_kwh is None:
            status = evidence_status or AnnualEvidenceStatus.PARTIAL_RESULT_UNVALIDATED.value
            active_warnings.append(
                "Baseline lifetime energy cannot be computed because annual energy reference is unavailable "
                "or incomplete. Constant-performance baseline is reported as null (PARTIAL_RESULT)."
            )
            return LifetimeEnergyBaseline(
                lifetime_years=lifetime_years,
                annual_reference_kwh=None,
                baseline_lifetime_energy_kwh=None,
                evidence_status=status,
                energy_basis=self.ENERGY_BASIS,
                degradation_applied=False,
                discounting_applied=False,
                warnings=active_warnings,
                limitations=active_limitations,
                metadata={"status": "NULL_ANNUAL_REFERENCE"},
            )

        # Validate annual_energy_kwh numerical validity
        if not math.isfinite(annual_energy_kwh) or annual_energy_kwh < 0:
            raise AnnualizationError(
                f"annual_energy_kwh must be a non-negative finite number, got {annual_energy_kwh}."
            )

        # Arithmetic calculation: strictly E_annual * L
        baseline_kwh = float(annual_energy_kwh * lifetime_years)
        status = evidence_status or AnnualEvidenceStatus.UNVALIDATED_REFERENCE_ONLY.value

        active_limitations.append(
            "Baseline calculation assumes constant nominal performance with zero physical degradation. "
            "For degradation-adjusted lifetime energy, consult Stage 6 degradation engine."
        )

        return LifetimeEnergyBaseline(
            lifetime_years=lifetime_years,
            annual_reference_kwh=float(annual_energy_kwh),
            baseline_lifetime_energy_kwh=baseline_kwh,
            evidence_status=status,
            energy_basis=self.ENERGY_BASIS,
            degradation_applied=False,
            discounting_applied=False,
            warnings=active_warnings,
            limitations=active_limitations,
            metadata={
                "annual_reference_kwh": annual_energy_kwh,
                "lifetime_years": lifetime_years,
                "calculation": f"{annual_energy_kwh:.2f} kWh/yr * {lifetime_years} yrs = {baseline_kwh:.2f} kWh",
            },
        )

