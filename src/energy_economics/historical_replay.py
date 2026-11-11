"""
SolarSelect — Phase 8: UNISOLAR Historical Replay Engine
Executes controlled historical energy replay over prepared Peer Cohort feature datasets.
Preserves site capacities, classifies in-sample vs out-of-sample periods, computes daily energy,
enforces partial-period restrictions, and preserves unverified energy basis under B-1.
"""

from datetime import datetime, timezone
import math
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Union
import uuid
import numpy as np
import pandas as pd

from src.energy_economics.exceptions import HistoricalReplayError
from src.energy_economics.inference import Phase5PeerCohortPredictor
from src.energy_economics.types import (
    ModelVariant,
    ReplaySampleClassification,
    HistoricalYearStatus,
)


class UNISOLARHistoricalReplayEngine:
    """
    Executes historical energy replay for the UNISOLAR Peer Cohort installations.
    Preserves historical site capacities and dates without extrapolating to unbuilt roofs.
    """

    DEFAULT_DATASET_PATH = Path("data/processed/unisolar/peer_cohort/features.csv")
    SCHEMA_VERSION = "phase8-io-0.1"
    STAGE_IDENTIFIER = "STAGE_2_HISTORICAL_REPLAY"

    OUT_OF_SAMPLE_START = "2022-03-01"
    OUT_OF_SAMPLE_END = "2022-04-23"

    def __init__(
        self,
        predictor: Optional[Phase5PeerCohortPredictor] = None,
        dataset_path: Optional[Union[str, Path]] = None,
    ) -> None:
        self.predictor = predictor or Phase5PeerCohortPredictor()
        self.dataset_path = Path(dataset_path or self.DEFAULT_DATASET_PATH)

    def load_dataset(self, path: Optional[Union[str, Path]] = None) -> pd.DataFrame:
        """Loads and performs schema validation on the historical feature dataset."""
        p = Path(path or self.dataset_path)
        if not p.exists():
            raise HistoricalReplayError(f"Historical replay dataset not found: {p}")

        try:
            df = pd.read_csv(p)
        except Exception as e:
            raise HistoricalReplayError(f"Failed to read dataset at {p}: {e}") from e

        required_cols = {"SiteKey", "Date"} | set(self.predictor.feature_names)
        missing_cols = required_cols - set(df.columns)
        if missing_cols:
            raise HistoricalReplayError(
                f"Historical dataset missing required columns: {sorted(list(missing_cols))}"
            )

        return df

    def replay(
        self,
        dataset: Optional[Union[pd.DataFrame, str, Path]] = None,
        site_keys: Optional[List[int]] = None,
        date_range: Optional[Tuple[str, str]] = None,
        run_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Executes historical replay over the selected UNISOLAR feature records.

        Args:
            dataset: Optional DataFrame or file path (defaults to features.csv).
            site_keys: Optional list of SiteKey identifiers to filter.
            date_range: Optional tuple of ('YYYY-MM-DD', 'YYYY-MM-DD').
            run_id: Optional unique run identifier.

        Returns:
            Structured Phase 8 historical replay output dictionary.
        """
        active_run_id = run_id or f"RUN-REPLAY-{uuid.uuid4().hex[:8].upper()}"

        if dataset is None or isinstance(dataset, (str, Path)):
            df = self.load_dataset(dataset)
        elif isinstance(dataset, pd.DataFrame):
            df = dataset.copy()
        else:
            raise HistoricalReplayError(
                f"Unsupported dataset type: '{type(dataset).__name__}'. Must be DataFrame or Path."
            )

        if df.empty:
            raise HistoricalReplayError("Historical replay dataset contains zero rows.")

        # Ensure Date is string YYYY-MM-DD
        df["Date"] = pd.to_datetime(df["Date"]).dt.strftime("%Y-%m-%d")

        # Filter by site_keys if specified
        if site_keys is not None:
            if not isinstance(site_keys, (list, tuple, set)) or len(site_keys) == 0:
                raise HistoricalReplayError("site_keys filter must be a non-empty collection of site IDs.")
            df = df[df["SiteKey"].isin(site_keys)].copy()
            if df.empty:
                raise HistoricalReplayError(f"No records found matching site_keys: {site_keys}")

        # Filter by date_range if specified
        if date_range is not None:
            if len(date_range) != 2:
                raise HistoricalReplayError("date_range must be a tuple of (start_date, end_date).")
            start_date, end_date = date_range
            df = df[(df["Date"] >= start_date) & (df["Date"] <= end_date)].copy()
            if df.empty:
                raise HistoricalReplayError(
                    f"No records found in date range: {start_date} to {end_date}"
                )

        # Validate duplicate (SiteKey, Date) pairs
        dup_mask = df.duplicated(subset=["SiteKey", "Date"], keep=False)
        if dup_mask.any():
            dup_records = df[dup_mask][["SiteKey", "Date"]].head(5).to_dict(orient="records")
            raise HistoricalReplayError(
                f"Duplicate (SiteKey, Date) combinations detected in historical replay dataset: {dup_records}"
            )

        # Sort chronologically by Date, then SiteKey
        df = df.sort_values(by=["Date", "SiteKey"]).reset_index(drop=True)

        # Validate features through Phase 5 predictor
        # Separate target if present
        actual_targets: Optional[pd.Series] = None
        if "target_daily_yield" in df.columns:
            actual_targets = pd.to_numeric(df["target_daily_yield"], errors="coerce")

        X_features = self.predictor.validate_features(df)

        # Generate model predictions: specific yield Y_hat in kWh/kWp/day
        raw_preds = self.predictor.predict(X_features)

        # Process per-row predictions and daily energy calculations
        prediction_records: List[Dict[str, Any]] = []
        negative_prediction_count = 0
        in_sample_count = 0
        out_of_sample_count = 0

        site_metrics: Dict[int, Dict[str, Any]] = {}

        for i, row in df.iterrows():
            site_key = int(row["SiteKey"])
            date_str = str(row["Date"])
            historical_kwp = float(row["kWp"])
            y_hat = float(raw_preds[i])

            actual_y = (
                float(actual_targets.iloc[i])
                if actual_targets is not None and not pd.isna(actual_targets.iloc[i])
                else None
            )

            # In-sample vs. out-of-sample labeling
            if self.OUT_OF_SAMPLE_START <= date_str <= self.OUT_OF_SAMPLE_END:
                sample_cls = ReplaySampleClassification.OUT_OF_SAMPLE.value
                out_of_sample_count += 1
            else:
                sample_cls = ReplaySampleClassification.IN_SAMPLE.value
                in_sample_count += 1

            # Negative prediction handling (Decision D-4 unresolved)
            y_hat_rounded = round(y_hat, 6)
            raw_unclipped_daily_energy = round(y_hat_rounded * historical_kwp, 6)
            if y_hat < 0.0:
                pred_status = "NEGATIVE_PREDICTION_WARNING"
                negative_prediction_count += 1
                estimated_daily_energy = None
                valid_energy = False
            else:
                pred_status = "VALID"
                estimated_daily_energy = raw_unclipped_daily_energy
                valid_energy = True

            record = {
                "site_key": site_key,
                "date": date_str,
                "historical_installed_capacity_kwp": historical_kwp,
                "sample_classification": sample_cls,
                "predicted_specific_yield_kwh_per_kwp_day": y_hat_rounded,
                "actual_target_daily_yield": round(actual_y, 6) if actual_y is not None else None,
                "estimated_daily_energy_kwh": estimated_daily_energy,
                "raw_unclipped_daily_energy_kwh": raw_unclipped_daily_energy,
                "prediction_status": pred_status,
            }
            prediction_records.append(record)

            # Update site metrics
            if site_key not in site_metrics:
                site_metrics[site_key] = {
                    "site_key": site_key,
                    "historical_capacity_kwp": historical_kwp,
                    "valid_days": 0,
                    "negative_days": 0,
                    "in_sample_days": 0,
                    "out_of_sample_days": 0,
                    "observed_period_energy_kwh": 0.0,
                }

            s_m = site_metrics[site_key]
            if valid_energy and estimated_daily_energy is not None:
                s_m["valid_days"] += 1
                s_m["observed_period_energy_kwh"] = round(
                    s_m["observed_period_energy_kwh"] + estimated_daily_energy, 6
                )
            else:
                s_m["negative_days"] += 1

            if sample_cls == ReplaySampleClassification.OUT_OF_SAMPLE.value:
                s_m["out_of_sample_days"] += 1
            else:
                s_m["in_sample_days"] += 1

        # Historical coverage calculation
        min_date = df["Date"].min()
        max_date = df["Date"].max()
        all_cal_dates = pd.date_range(min_date, max_date).strftime("%Y-%m-%d").tolist()
        calendar_days_count = len(all_cal_dates)
        distinct_observation_dates = df["Date"].nunique()
        missing_calendar_dates_count = calendar_days_count - distinct_observation_dates
        valid_prediction_days = len(prediction_records) - negative_prediction_count

        total_observed_energy_kwh = sum(
            r["estimated_daily_energy_kwh"]
            for r in prediction_records
            if r["estimated_daily_energy_kwh"] is not None
        )

        coverage_fraction = (
            round(distinct_observation_dates / calendar_days_count, 6)
            if calendar_days_count > 0
            else 0.0
        )

        global_warnings: List[str] = [
            "Historical replay covers a partial-year observation window (May 1, 2021 to April 23, 2022; 358 calendar days). It does NOT represent a validated complete 12-consecutive-calendar-month year.",
            "Energy basis remains UNVERIFIED under Blocking Issue B-1; no AC/DC conversion or loss adjustment applied.",
            "In-sample predictions reflect historical reconstruction on training dates and must not be reported as independent forecasts.",
            "Blocking Issue B-2 remains unresolved; historical replay does not authorize prospective yield prediction for unbuilt roofs.",
        ]
        if negative_prediction_count > 0:
            global_warnings.append(
                f"Detected {negative_prediction_count} negative specific yield predictions. Per Decision D-4, negative predictions are preserved with NEGATIVE_PREDICTION_WARNING and excluded from positive energy sums."
            )

        replay_output = {
            "run_id": active_run_id,
            "schema_version": self.SCHEMA_VERSION,
            "stage": self.STAGE_IDENTIFIER,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "engine_status": "SUCCESS",
            "replay_summary": {
                "cohort": "peer_cohort",
                "model_name": self.predictor.model_name,
                "model_variant": self.predictor.model_variant.value,
                "date_range": {
                    "start": min_date,
                    "end": max_date,
                },
                "calendar_days": calendar_days_count,
                "distinct_observation_dates": distinct_observation_dates,
                "missing_calendar_dates": missing_calendar_dates_count,
                "coverage_fraction": coverage_fraction,
                "n_unique_sites": df["SiteKey"].nunique(),
                "total_predictions": len(prediction_records),
                "valid_predictions_count": valid_prediction_days,
                "negative_predictions_count": negative_prediction_count,
                "in_sample_count": in_sample_count,
                "out_of_sample_count": out_of_sample_count,
                "observed_period_estimated_energy_kwh": round(total_observed_energy_kwh, 4),
                "historical_year_status": HistoricalYearStatus.PARTIAL_PERIOD_NOT_A_FULL_YEAR.value,
                "energy_basis": "UNVERIFIED",
                "annualization_extrapolation_applied": False,
            },
            "model_provenance": self.predictor.get_provenance(),
            "site_summaries": list(site_metrics.values()),
            "predictions": prediction_records,
            "warnings": global_warnings,
            "unresolved_inputs": [
                "B-1: AC/DC metering point confirmation (energy_basis remains UNVERIFIED; no AC/DC conversion applied)",
                "B-2: Prospective roof lag-yield policy (model prediction remains PREDICTION_PENDING_LAG_POLICY)",
                "D-2: Weather source for non-UNISOLAR sites",
                "D-4: Negative prediction clipping policy (unresolved; raw predictions preserved with warning)",
            ],
        }

        return replay_output
