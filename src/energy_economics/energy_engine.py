"""
SolarSelect — Phase 8: Stage 3 Energy Estimation Engine
Authoritative energy estimation and scenario handling engine.
Integrates Stage 1 foundation and Stage 2 historical replay to calculate daily energy,
preserve units and precision, enforce strict scenario boundaries, and govern unverified energy basis.
"""

from datetime import datetime, timezone
import math
from typing import Dict, Any, List, Optional, Tuple, Union
import numpy as np
import pandas as pd

from src.energy_economics.exceptions import (
    EnergyEstimationError,
    ScenarioValidationError,
    Phase5InferenceError,
    FeatureValidationError,
)
from src.energy_economics.inference import Phase5PeerCohortPredictor
from src.energy_economics.historical_replay import UNISOLARHistoricalReplayEngine
from src.energy_economics.types import (
    EnergyScenarioType,
    ScenarioEvaluationStatus,
    ReplaySampleClassification,
    HistoricalYearStatus,
    ModelVariant,
    DailyEnergyEstimate,
    SiteEnergySummary,
    EnergyAggregationSummary,
)


class Phase8EnergyEstimationEngine:
    """
    Phase 8 Stage 3 Energy Estimation Engine.
    Responsibilities:
    - Ingests validated Stage 2 predictions and applies exact daily energy arithmetic:
        E_daily = predicted_specific_yield (kWh/kWp/day) * historical_kWp (kWp)
    - Distinguishes raw mathematical energy output from accepted positive energy while operational clipping policy remains open under Decision D-4.
    - Governs explicit scenario input contracts:
        * HISTORICAL_REPLAY: Supported on UNISOLAR Peer Cohort dataset.
        * REPRESENTATIVE_PERIOD: Requires validated 29-feature continuous profile; no synthetic lag generation.
        * PROSPECTIVE_ROOF: Blocked under Blocking Issue B-2 (PREDICTION_PENDING_LAG_POLICY).
    - Governs energy basis as strictly UNVERIFIED under Blocking Issue B-1 (no losses, no double multiplication).
    - Aggregates observed-period energy only (no 365-day extrapolation or annual scaling).
    """

    SCHEMA_VERSION = "phase8-io-0.1"
    STAGE_IDENTIFIER = "STAGE_3_ENERGY_ESTIMATION"

    ENERGY_BASIS = "UNVERIFIED"
    ENERGY_BASIS_QUALIFICATION = (
        "Energy basis (AC inverter output vs DC array yield) is unverified in UNISOLAR ground truth "
        "per Blocking Issue B-1. Zero AC/DC conversion losses, system derates, temperature corrections, "
        "or tilt/orientation adjustments are applied."
    )

    SPECIFIC_YIELD_UNIT = "kWh/kWp/day"
    DAILY_ENERGY_UNIT = "kWh/day"
    TOTAL_ENERGY_UNIT = "kWh"
    CAPACITY_UNIT = "kWp"

    def __init__(
        self,
        predictor: Optional[Phase5PeerCohortPredictor] = None,
        replay_engine: Optional[UNISOLARHistoricalReplayEngine] = None,
    ) -> None:
        self.predictor = predictor or Phase5PeerCohortPredictor()
        self.replay_engine = replay_engine or UNISOLARHistoricalReplayEngine(predictor=self.predictor)

    def estimate_energy(
        self,
        scenario_type: Union[EnergyScenarioType, str],
        replay_output: Optional[Dict[str, Any]] = None,
        feature_dataset: Optional[pd.DataFrame] = None,
        representative_profile: Optional[pd.DataFrame] = None,
        prospective_configuration: Optional[Dict[str, Any]] = None,
        model_variant: Union[ModelVariant, str] = ModelVariant.PRIMARY_EXTRA_TREES,
        date_range: Optional[Tuple[str, str]] = None,
        run_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Executes energy estimation according to the designated scenario contract.

        Args:
            scenario_type: EnergyScenarioType (HISTORICAL_REPLAY, REPRESENTATIVE_PERIOD, PROSPECTIVE_ROOF).
            replay_output: Optional precomputed Stage 2 replay output dict.
            feature_dataset: Optional raw feature dataset for historical replay execution.
            representative_profile: Optional DataFrame containing complete 29-feature representative rows.
            prospective_configuration: Optional configuration dict for prospective roof assessment.
            model_variant: ModelVariant selection (primary_extra_trees, fallback_blend_50_50).
            date_range: Optional (start_date, end_date) string tuple for filtering.
            run_id: Optional run identifier.

        Returns:
            Structured Stage 3 output dictionary conforming to the Phase 8 output contract.
        """
        active_run_id = run_id or f"phase8-stage3-{int(datetime.now(timezone.utc).timestamp())}"

        # Parse and validate scenario type
        if isinstance(scenario_type, str):
            try:
                scenario_enum = EnergyScenarioType(scenario_type.upper())
            except ValueError:
                raise ScenarioValidationError(
                    f"Unsupported scenario_type: '{scenario_type}'. "
                    f"Must be one of {[e.value for e in EnergyScenarioType]}."
                )
        else:
            scenario_enum = scenario_type

        # Dispatch scenario
        if scenario_enum == EnergyScenarioType.HISTORICAL_REPLAY:
            return self._evaluate_historical_replay(
                replay_output=replay_output,
                feature_dataset=feature_dataset,
                model_variant=model_variant,
                date_range=date_range,
                run_id=active_run_id,
            )
        elif scenario_enum == EnergyScenarioType.REPRESENTATIVE_PERIOD:
            return self._evaluate_representative_period(
                representative_profile=representative_profile,
                model_variant=model_variant,
                run_id=active_run_id,
            )
        elif scenario_enum == EnergyScenarioType.PROSPECTIVE_ROOF:
            return self._evaluate_prospective_roof(
                prospective_configuration=prospective_configuration,
                run_id=active_run_id,
            )
        else:
            raise ScenarioValidationError(f"Unhandled scenario type: {scenario_enum}")

    def _evaluate_historical_replay(
        self,
        replay_output: Optional[Dict[str, Any]],
        feature_dataset: Optional[pd.DataFrame],
        model_variant: Union[ModelVariant, str],
        date_range: Optional[Tuple[str, str]],
        run_id: str,
    ) -> Dict[str, Any]:
        """Evaluates historical replay scenario using validated Stage 2 interface."""
        # 1. Obtain or generate Stage 2 replay output
        if replay_output is None:
            # Check if model_variant requires a different predictor
            variant_val = model_variant.value if isinstance(model_variant, ModelVariant) else str(model_variant)
            if variant_val != self.predictor.model_variant.value:
                active_predictor = Phase5PeerCohortPredictor(model_variant=model_variant)
                active_replay_engine = UNISOLARHistoricalReplayEngine(predictor=active_predictor)
            else:
                active_replay_engine = self.replay_engine

            # Execute replay via Stage 2 engine
            replay_output = active_replay_engine.replay(
                dataset=feature_dataset,
                date_range=date_range,
                run_id=run_id,
            )

        # 2. Extract Stage 2 records and validate provenance
        predictions = replay_output.get("predictions", [])
        if not predictions:
            raise EnergyEstimationError("Historical replay output contains zero prediction records.")

        model_provenance = replay_output.get("model_provenance", self.predictor.get_provenance())
        replay_summary = replay_output.get("replay_summary", {})

        # 3. Process individual daily energy estimates
        daily_estimates: List[Dict[str, Any]] = []
        site_metrics: Dict[int, Dict[str, Any]] = {}

        total_valid_days = 0
        total_negative_days = 0
        in_sample_records = 0
        out_of_sample_records = 0

        total_accepted_positive_energy = 0.0
        total_raw_mathematical_energy = 0.0
        in_sample_accepted_energy = 0.0
        out_of_sample_accepted_energy = 0.0
        actual_observed_total_energy = 0.0
        has_actual_targets = False

        for row in predictions:
            site_key = int(row["site_key"])
            date_str = str(row["date"])
            kwp = float(row["historical_installed_capacity_kwp"])
            y_hat = float(row["predicted_specific_yield_kwh_per_kwp_day"])
            sample_cls = str(row.get("sample_classification", ReplaySampleClassification.IN_SAMPLE.value))

            # Non-finite validation
            if math.isnan(y_hat) or math.isinf(y_hat):
                raise EnergyEstimationError(
                    f"Non-finite specific yield prediction encountered for SiteKey={site_key}, Date={date_str}."
                )
            if math.isnan(kwp) or math.isinf(kwp) or kwp <= 0.0:
                raise EnergyEstimationError(
                    f"Invalid installed capacity ({kwp}) encountered for SiteKey={site_key}, Date={date_str}."
                )

            # Daily energy calculation: E_daily = Y_hat * kWp (Exact precision)
            y_hat_rounded = round(y_hat, 6)
            kwp_rounded = round(kwp, 4)
            raw_mathematical_daily_energy = round(y_hat_rounded * kwp_rounded, 6)

            # Verification of capacity multiplication: exactly once, never twice
            existing_unclipped = row.get("raw_unclipped_daily_energy_kwh")
            if existing_unclipped is not None:
                diff = abs(float(existing_unclipped) - raw_mathematical_daily_energy)
                if diff > 1e-4:
                    raise EnergyEstimationError(
                        f"Capacity multiplication arithmetic mismatch on SiteKey={site_key}, Date={date_str}: "
                        f"expected {raw_mathematical_daily_energy}, got {existing_unclipped}."
                    )

            # Ground truth actual energy (if available)
            actual_y = row.get("actual_target_daily_yield")
            if actual_y is not None and not (math.isnan(actual_y) if isinstance(actual_y, float) else False):
                actual_y_float = float(actual_y)
                actual_daily_energy = round(actual_y_float * kwp_rounded, 6)
                has_actual_targets = True
            else:
                actual_y_float = None
                actual_daily_energy = None

            # Negative prediction handling (Decision D-4 unresolved)
            if y_hat < 0.0:
                pred_status = "NEGATIVE_PREDICTION_WARNING"
                accepted_positive_daily_energy = None
                total_negative_days += 1
            else:
                pred_status = "VALID"
                accepted_positive_daily_energy = raw_mathematical_daily_energy
                total_valid_days += 1

            if sample_cls == ReplaySampleClassification.OUT_OF_SAMPLE.value:
                out_of_sample_records += 1
                if accepted_positive_daily_energy is not None:
                    out_of_sample_accepted_energy += accepted_positive_daily_energy
            else:
                in_sample_records += 1
                if accepted_positive_daily_energy is not None:
                    in_sample_accepted_energy += accepted_positive_daily_energy

            total_raw_mathematical_energy += raw_mathematical_daily_energy
            if accepted_positive_daily_energy is not None:
                total_accepted_positive_energy += accepted_positive_daily_energy

            if actual_daily_energy is not None:
                actual_observed_total_energy += actual_daily_energy

            # Record estimate
            daily_est = DailyEnergyEstimate(
                site_key=site_key,
                date=date_str,
                historical_installed_capacity_kwp=kwp_rounded,
                sample_classification=sample_cls,
                predicted_specific_yield_kwh_per_kwp_day=y_hat_rounded,
                specific_yield_unit=self.SPECIFIC_YIELD_UNIT,
                raw_mathematical_daily_energy_kwh=raw_mathematical_daily_energy,
                accepted_positive_daily_energy_kwh=accepted_positive_daily_energy,
                daily_energy_unit=self.DAILY_ENERGY_UNIT,
                actual_target_daily_yield=round(actual_y_float, 6) if actual_y_float is not None else None,
                actual_daily_energy_kwh=actual_daily_energy,
                prediction_status=pred_status,
            )
            daily_estimates.append(daily_est.to_dict())

            # Update site metrics
            if site_key not in site_metrics:
                site_metrics[site_key] = {
                    "site_key": site_key,
                    "historical_capacity_kwp": kwp_rounded,
                    "capacity_unit": self.CAPACITY_UNIT,
                    "total_observation_days": 0,
                    "valid_prediction_days": 0,
                    "negative_prediction_days": 0,
                    "in_sample_days": 0,
                    "out_of_sample_days": 0,
                    "accepted_positive_energy_kwh": 0.0,
                    "raw_mathematical_energy_kwh": 0.0,
                    "actual_observed_energy_kwh": 0.0 if has_actual_targets else None,
                    "energy_unit": self.TOTAL_ENERGY_UNIT,
                }

            s_m = site_metrics[site_key]
            s_m["total_observation_days"] += 1
            if pred_status == "VALID":
                s_m["valid_prediction_days"] += 1
                s_m["accepted_positive_energy_kwh"] = round(
                    s_m["accepted_positive_energy_kwh"] + raw_mathematical_daily_energy, 6
                )
            else:
                s_m["negative_prediction_days"] += 1

            s_m["raw_mathematical_energy_kwh"] = round(
                s_m["raw_mathematical_energy_kwh"] + raw_mathematical_daily_energy, 6
            )

            if sample_cls == ReplaySampleClassification.OUT_OF_SAMPLE.value:
                s_m["out_of_sample_days"] += 1
            else:
                s_m["in_sample_days"] += 1

            if actual_daily_energy is not None and s_m["actual_observed_energy_kwh"] is not None:
                s_m["actual_observed_energy_kwh"] = round(
                    s_m["actual_observed_energy_kwh"] + actual_daily_energy, 6
                )

        # 4. Aggregation summary
        date_range_meta = replay_summary.get("date_range", {})
        calendar_days = replay_summary.get("calendar_days", 0)
        distinct_dates = replay_summary.get("distinct_observation_dates", 0)
        missing_dates = replay_summary.get("missing_calendar_dates", 0)
        coverage_fraction = replay_summary.get("coverage_fraction", 0.0)

        agg_summary = EnergyAggregationSummary(
            cohort=replay_summary.get("cohort", "peer_cohort"),
            scenario_type=EnergyScenarioType.HISTORICAL_REPLAY.value,
            scenario_status=ScenarioEvaluationStatus.COMPLETED.value,
            model_name=model_provenance.get("model_name", self.predictor.model_name),
            model_variant=model_provenance.get("model_variant", self.predictor.model_variant.value),
            date_range=date_range_meta,
            calendar_days=calendar_days,
            distinct_observation_dates=distinct_dates,
            missing_calendar_dates=missing_dates,
            coverage_fraction=coverage_fraction,
            n_unique_sites=len(site_metrics),
            total_daily_records=len(daily_estimates),
            valid_predictions_count=total_valid_days,
            negative_predictions_count=total_negative_days,
            in_sample_records_count=in_sample_records,
            out_of_sample_records_count=out_of_sample_records,
            accepted_positive_energy_kwh=round(total_accepted_positive_energy, 4),
            raw_mathematical_energy_kwh=round(total_raw_mathematical_energy, 4),
            in_sample_accepted_positive_energy_kwh=round(in_sample_accepted_energy, 4),
            out_of_sample_accepted_positive_energy_kwh=round(out_of_sample_accepted_energy, 4),
            actual_observed_total_energy_kwh=round(actual_observed_total_energy, 4) if has_actual_targets else None,
            energy_unit=self.TOTAL_ENERGY_UNIT,
            historical_year_status=HistoricalYearStatus.PARTIAL_PERIOD_NOT_A_FULL_YEAR.value,
            energy_basis=self.ENERGY_BASIS,
            annualization_extrapolation_applied=False,
        )

        warnings = [
            "Historical replay covers observed telemetry only (May 1, 2021 to April 23, 2022; 358 calendar days). "
            "It does NOT represent a complete 12-consecutive-calendar-month annual cycle. Annual extrapolation is strictly prohibited.",
            "Energy basis remains UNVERIFIED under Blocking Issue B-1. Zero AC/DC conversion losses, system derates, "
            "or physical losses have been applied.",
            "In-sample predictions reflect historical model reconstruction on training dates and must NOT be reported as independent validation.",
            "Historical replay is restricted to known UNISOLAR Peer Cohort rooftop installations; it does not claim unseen-site or unseen-geography generalization.",
        ]
        if total_negative_days > 0:
            warnings.append(
                f"Preserved {total_negative_days} negative specific yield predictions. Operational clipping policy remains open under Decision D-4; "
                "raw values are preserved with NEGATIVE_PREDICTION_WARNING and excluded from positive accepted energy totals without clipping."
            )

        return {
            "run_id": run_id,
            "schema_version": self.SCHEMA_VERSION,
            "stage": self.STAGE_IDENTIFIER,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "scenario_type": EnergyScenarioType.HISTORICAL_REPLAY.value,
            "scenario_status": ScenarioEvaluationStatus.COMPLETED.value,
            "energy_basis": self.ENERGY_BASIS,
            "energy_basis_qualification": self.ENERGY_BASIS_QUALIFICATION,
            "aggregation_summary": agg_summary.to_dict(),
            "site_summaries": list(site_metrics.values()),
            "daily_estimates": daily_estimates,
            "model_provenance": model_provenance,
            "warnings": warnings,
            "unresolved_inputs": [
                "B-1: AC/DC metering point confirmation (energy_basis remains UNVERIFIED; no AC/DC conversion applied)",
                "B-2: Prospective roof lag-yield policy (model prediction remains PREDICTION_PENDING_LAG_POLICY)",
                "D-2: Weather source for non-UNISOLAR sites",
                "D-4: Negative prediction clipping policy (unresolved; raw predictions preserved with warning; no physical clipping policy authorized)",
            ],
        }

    def _evaluate_representative_period(
        self,
        representative_profile: Optional[pd.DataFrame],
        model_variant: Union[ModelVariant, str],
        run_id: str,
    ) -> Dict[str, Any]:
        """Evaluates representative-period scenario when a complete 29-feature continuous profile is supplied."""
        # Check profile availability
        variant_val = model_variant.value if isinstance(model_variant, ModelVariant) else str(model_variant)
        if variant_val != self.predictor.model_variant.value:
            active_predictor = Phase5PeerCohortPredictor(model_variant=model_variant)
        else:
            active_predictor = self.predictor

        if representative_profile is None or len(representative_profile) == 0:
            return {
                "run_id": run_id,
                "schema_version": self.SCHEMA_VERSION,
                "stage": self.STAGE_IDENTIFIER,
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "scenario_type": EnergyScenarioType.REPRESENTATIVE_PERIOD.value,
                "scenario_status": ScenarioEvaluationStatus.UNAVAILABLE_INPUT_PROFILE.value,
                "energy_basis": self.ENERGY_BASIS,
                "energy_basis_qualification": self.ENERGY_BASIS_QUALIFICATION,
                "aggregation_summary": None,
                "site_summaries": [],
                "daily_estimates": [],
                "model_provenance": active_predictor.get_provenance(),
                "warnings": [
                    "Representative-period scenario requires a complete, continuous 29-feature profile with verified provenance. "
                    "Input profile was not provided. Lag features cannot be synthetically generated or imputed from future observations."
                ],
                "unresolved_inputs": [
                    "B-1: AC/DC metering point confirmation (energy_basis remains UNVERIFIED)",
                    "D-2: Representative weather profile for target site",
                ],
            }

        # Validate features via predictor
        # Checks required 29 features and non-finite values
        try:
            X_features = active_predictor.validate_features(representative_profile)
        except FeatureValidationError as e:
            raise EnergyEstimationError(f"Representative profile feature validation failed: {e}") from e

        # Ensure no recursive lag synthesis or missing capacity
        if "kWp" not in representative_profile.columns:
            raise EnergyEstimationError("Representative profile must include candidate installed DC capacity ('kWp').")

        # Predict specific yields
        raw_preds = active_predictor.predict(X_features)

        daily_estimates: List[Dict[str, Any]] = []
        total_accepted_positive_energy = 0.0
        total_raw_mathematical_energy = 0.0
        total_negative_days = 0
        total_valid_days = 0

        for i, row in representative_profile.reset_index(drop=True).iterrows():
            site_key = int(row.get("SiteKey", 0))
            date_str = str(row.get("Date", f"Day-{i+1}"))
            kwp = float(row["kWp"])
            y_hat = float(raw_preds[i])

            if math.isnan(y_hat) or math.isinf(y_hat):
                raise EnergyEstimationError(f"Non-finite prediction encountered on representative day {i+1}.")

            y_hat_rounded = round(y_hat, 6)
            kwp_rounded = round(kwp, 4)
            raw_math_energy = round(y_hat_rounded * kwp_rounded, 6)

            if y_hat < 0.0:
                pred_status = "NEGATIVE_PREDICTION_WARNING"
                accepted_pos_energy = None
                total_negative_days += 1
            else:
                pred_status = "VALID"
                accepted_pos_energy = raw_math_energy
                total_valid_days += 1

            total_raw_mathematical_energy += raw_math_energy
            if accepted_pos_energy is not None:
                total_accepted_positive_energy += accepted_pos_energy

            daily_est = DailyEnergyEstimate(
                site_key=site_key,
                date=date_str,
                historical_installed_capacity_kwp=kwp_rounded,
                sample_classification="NOT_APPLICABLE_REPRESENTATIVE_SCENARIO",
                predicted_specific_yield_kwh_per_kwp_day=y_hat_rounded,
                specific_yield_unit=self.SPECIFIC_YIELD_UNIT,
                raw_mathematical_daily_energy_kwh=raw_math_energy,
                accepted_positive_daily_energy_kwh=accepted_pos_energy,
                daily_energy_unit=self.DAILY_ENERGY_UNIT,
                prediction_status=pred_status,
            )
            daily_estimates.append(daily_est.to_dict())

        agg_summary = EnergyAggregationSummary(
            cohort="representative_scenario",
            scenario_type=EnergyScenarioType.REPRESENTATIVE_PERIOD.value,
            scenario_status=ScenarioEvaluationStatus.COMPLETED.value,
            model_name=self.predictor.model_name,
            model_variant=self.predictor.model_variant.value,
            date_range={"start": daily_estimates[0]["date"], "end": daily_estimates[-1]["date"]},
            calendar_days=len(daily_estimates),
            distinct_observation_dates=len(daily_estimates),
            missing_calendar_dates=0,
            coverage_fraction=1.0,
            n_unique_sites=1,
            total_daily_records=len(daily_estimates),
            valid_predictions_count=total_valid_days,
            negative_predictions_count=total_negative_days,
            in_sample_records_count=0,
            out_of_sample_records_count=0,
            accepted_positive_energy_kwh=round(total_accepted_positive_energy, 4),
            raw_mathematical_energy_kwh=round(total_raw_mathematical_energy, 4),
            energy_unit=self.TOTAL_ENERGY_UNIT,
            historical_year_status=HistoricalYearStatus.NOT_APPLICABLE_SCENARIO.value,
            energy_basis=self.ENERGY_BASIS,
            annualization_extrapolation_applied=False,
        )

        return {
            "run_id": run_id,
            "schema_version": self.SCHEMA_VERSION,
            "stage": self.STAGE_IDENTIFIER,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "scenario_type": EnergyScenarioType.REPRESENTATIVE_PERIOD.value,
            "scenario_status": ScenarioEvaluationStatus.COMPLETED.value,
            "energy_basis": self.ENERGY_BASIS,
            "energy_basis_qualification": self.ENERGY_BASIS_QUALIFICATION,
            "aggregation_summary": agg_summary.to_dict(),
            "site_summaries": [],
            "daily_estimates": daily_estimates,
            "model_provenance": active_predictor.get_provenance(),
            "warnings": [
                "Representative-period scenario evaluated using provided external feature profile. "
                "Energy basis remains UNVERIFIED under Blocking Issue B-1.",
                "Predictions reflect single-pass evaluation; no recursive autoregressive simulation or lag updates performed.",
            ],
            "unresolved_inputs": [
                "B-1: AC/DC metering point confirmation (energy_basis remains UNVERIFIED)",
                "D-2: Weather source provenance for representative profile",
            ],
        }

    def _evaluate_prospective_roof(
        self,
        prospective_configuration: Optional[Dict[str, Any]],
        run_id: str,
    ) -> Dict[str, Any]:
        """
        Evaluates prospective roof scenario.
        Strictly enforces that prospective prediction is blocked under Blocking Issue B-2.
        Does NOT synthesize mock lag-yield features or invoke model inference.
        """
        candidate_kwp = None
        panel_id = None
        if prospective_configuration:
            candidate_kwp = prospective_configuration.get("system_capacity_kwp") or prospective_configuration.get("candidate_kwp")
            panel_id = prospective_configuration.get("panel_id")

        return {
            "run_id": run_id,
            "schema_version": self.SCHEMA_VERSION,
            "stage": self.STAGE_IDENTIFIER,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "scenario_type": EnergyScenarioType.PROSPECTIVE_ROOF.value,
            "scenario_status": ScenarioEvaluationStatus.BLOCKED_PENDING_LAG_POLICY.value,
            "energy_basis": self.ENERGY_BASIS,
            "energy_basis_qualification": self.ENERGY_BASIS_QUALIFICATION,
            "candidate_roof_evaluation": {
                "panel_id": panel_id,
                "candidate_dc_capacity_kwp": candidate_kwp,
                "prediction_status": "PREDICTION_PENDING_LAG_POLICY",
                "estimated_annual_energy_kwh": None,
                "overall_recommendation_status": "RECOMMENDATION_NOT_EVALUATED",
            },
            "aggregation_summary": None,
            "site_summaries": [],
            "daily_estimates": [],
            "model_provenance": self.predictor.get_provenance(),
            "warnings": [
                "Prospective roof energy prediction is strictly blocked under Blocking Issue B-2. "
                "Unbuilt prospective roofs have no operational telemetry history; lag-yield features "
                "('lag1_daily_yield', 'rolling_mean_7d_yield', etc.) cannot be fabricated or recursively simulated.",
                "Zero model prediction passes were performed. Capacity support was established in Stage 1, "
                "but prospective energy prediction remains pending an authorized lag-yield policy.",
            ],
            "unresolved_inputs": [
                "B-1: AC/DC metering point confirmation (energy_basis remains UNVERIFIED)",
                "B-2: Prospective roof lag-yield policy (model prediction remains PREDICTION_PENDING_LAG_POLICY)",
                "D-2: Weather data source for target roof location",
            ],
        }
