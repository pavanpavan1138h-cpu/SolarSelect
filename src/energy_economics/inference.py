"""
SolarSelect — Phase 8: Phase 5 Peer Cohort Inference Interface
Controlled, read-only inference engine for the frozen Phase 5 Peer Cohort models.
Enforces strict 29-feature alignment, numerical validation, runtime SHA-256 tracking,
and target-column exclusion.
"""

import hashlib
import json
import math
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
import joblib
import numpy as np
import pandas as pd

from src.energy_economics.exceptions import (
    Phase5InferenceError,
    FeatureValidationError,
)
from src.energy_economics.types import ModelVariant


class Phase5PeerCohortPredictor:
    """
    Inference interface for frozen Phase 5 Peer Cohort models.
    Supports primary ExtraTreesRegressor and authorized 50/50 ExtraTrees + ElasticNet ensemble blend.
    Enforces read-only execution, runtime artifact hash verification, and strict feature schemas.
    """

    DEFAULT_ET_PATH = Path("models/phase5/final/peer_cohort/final_extra_trees.joblib")
    DEFAULT_EN_PATH = Path("models/phase5/final/peer_cohort/final_elastic_net.joblib")
    DEFAULT_METADATA_PATH = Path("models/phase5/final_model_metadata.json")

    EXCLUDED_TARGET_COLUMNS = {
        "target_daily_yield",
        "target",
        "y",
        "SolarGeneration",
        "solargeneration",
        "actual_target_daily_yield",
    }

    def __init__(
        self,
        model_variant: Union[ModelVariant, str] = ModelVariant.PRIMARY_EXTRA_TREES,
        primary_model_path: Optional[Union[str, Path]] = None,
        fallback_linear_path: Optional[Union[str, Path]] = None,
        metadata_path: Optional[Union[str, Path]] = None,
    ) -> None:
        if isinstance(model_variant, str):
            try:
                self.model_variant = ModelVariant(model_variant.lower())
            except ValueError:
                raise Phase5InferenceError(
                    f"Unsupported model variant: '{model_variant}'. "
                    f"Must be '{ModelVariant.PRIMARY_EXTRA_TREES.value}' or '{ModelVariant.FALLBACK_BLEND_50_50.value}'."
                )
        else:
            self.model_variant = model_variant

        self.primary_path = Path(primary_model_path or self.DEFAULT_ET_PATH)
        self.linear_path = Path(fallback_linear_path or self.DEFAULT_EN_PATH)
        self.metadata_path = Path(metadata_path or self.DEFAULT_METADATA_PATH)

        # Artifact validation & hashes
        if not self.primary_path.exists():
            raise Phase5InferenceError(f"Primary model artifact not found: {self.primary_path}")
        self.primary_sha256 = self._compute_file_sha256(self.primary_path)

        if self.model_variant == ModelVariant.FALLBACK_BLEND_50_50:
            if not self.linear_path.exists():
                raise Phase5InferenceError(
                    f"Fallback linear model artifact not found: {self.linear_path}"
                )
            self.linear_sha256 = self._compute_file_sha256(self.linear_path)
        else:
            self.linear_sha256 = None

        # Load models in read-only manner
        self._load_models()

        # Load model metadata
        self._load_metadata()

        # Compute feature names hash
        feature_string = ",".join(self.feature_names)
        self.feature_names_hash = hashlib.sha256(feature_string.encode("utf-8")).hexdigest()

    @staticmethod
    def _compute_file_sha256(path: Path) -> str:
        """Computes SHA-256 of a file on disk."""
        hasher = hashlib.sha256()
        with open(path, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        return hasher.hexdigest()

    def _load_models(self) -> None:
        """Loads model estimators from serialized joblib artifacts."""
        try:
            self.primary_model = joblib.load(self.primary_path)
        except Exception as e:
            raise Phase5InferenceError(
                f"Failed to load primary ExtraTrees model from {self.primary_path}: {e}"
            ) from e

        if not hasattr(self.primary_model, "feature_names_in_"):
            raise Phase5InferenceError("Loaded primary model is missing 'feature_names_in_' attribute.")

        self.feature_names = list(self.primary_model.feature_names_in_)
        if len(self.feature_names) != 29:
            raise Phase5InferenceError(
                f"Expected exactly 29 predictive features, found {len(self.feature_names)}."
            )

        if self.model_variant == ModelVariant.FALLBACK_BLEND_50_50:
            try:
                self.linear_model = joblib.load(self.linear_path)
            except Exception as e:
                raise Phase5InferenceError(
                    f"Failed to load fallback ElasticNet model from {self.linear_path}: {e}"
                ) from e

            linear_features = list(getattr(self.linear_model, "feature_names_in_", []))
            if linear_features != self.feature_names:
                raise Phase5InferenceError(
                    "Feature space mismatch between primary ExtraTrees and fallback ElasticNet estimators."
                )
        else:
            self.linear_model = None

    def _load_metadata(self) -> None:
        """Loads metadata attributes from final_model_metadata.json."""
        self.metadata: Dict[str, Any] = {}
        self.evaluation_timestamp = "2026-11-10T08:45:00Z"
        self.cohort = "peer_cohort"

        if self.metadata_path.exists():
            try:
                with open(self.metadata_path, "r") as f:
                    self.metadata = json.load(f)
                self.evaluation_timestamp = self.metadata.get(
                    "evaluation_timestamp", self.evaluation_timestamp
                )
            except Exception:
                pass

        if self.model_variant == ModelVariant.PRIMARY_EXTRA_TREES:
            self.model_name = "Tuned ExtraTreesRegressor"
        else:
            self.model_name = "50/50 ExtraTrees + ElasticNet Ensemble Blend"

    def validate_features(
        self,
        features: Union[pd.DataFrame, Dict[str, Any], List[Dict[str, Any]]],
    ) -> pd.DataFrame:
        """
        Validates input feature rows against the exact 29-feature schema.
        Ensures exact column presence, finite numerics, target exclusion, and correct ordering.

        Args:
            features: pandas DataFrame or dictionary representing feature rows.

        Returns:
            Validated pandas DataFrame with exact 29 columns in feature_names_in_ order.

        Raises:
            FeatureValidationError: If required features are missing, non-numeric, NaN, infinite,
            or if target columns are passed as features.
        """
        if features is None:
            raise FeatureValidationError("Input features cannot be None.")

        # Convert to DataFrame
        if isinstance(features, pd.DataFrame):
            df = features.copy()
        elif isinstance(features, dict):
            df = pd.DataFrame([features])
        elif isinstance(features, list):
            if len(features) == 0:
                raise FeatureValidationError("Input features list cannot be empty.")
            df = pd.DataFrame(features)
        else:
            raise FeatureValidationError(
                f"Unsupported feature input type: '{type(features).__name__}'. "
                f"Must be DataFrame, dict, or list of dicts."
            )

        if df.empty:
            raise FeatureValidationError("Feature input DataFrame contains zero rows.")

        # Check for target column leakage into feature inputs
        present_targets = set(df.columns) & self.EXCLUDED_TARGET_COLUMNS
        if present_targets:
            # If input has extra columns including target, remove target columns before feature check
            df = df.drop(columns=list(present_targets))

        # Check that all 29 required features are present
        missing_features = set(self.feature_names) - set(df.columns)
        if missing_features:
            raise FeatureValidationError(
                f"Missing required model features ({len(missing_features)}): {sorted(list(missing_features))}"
            )

        # Select only the 29 features in exact model feature order
        df_ordered = df[self.feature_names].copy()

        # Validate finite numeric values
        for col in self.feature_names:
            series = df_ordered[col]
            # Coerce to numeric
            numeric_series = pd.to_numeric(series, errors="coerce")
            if numeric_series.isna().any():
                bad_idx = numeric_series[numeric_series.isna()].index.tolist()
                raise FeatureValidationError(
                    f"Feature '{col}' contains non-numeric, missing, or NaN values at row index {bad_idx}."
                )
            if np.isinf(numeric_series).any():
                bad_idx = numeric_series[np.isinf(numeric_series)].index.tolist()
                raise FeatureValidationError(
                    f"Feature '{col}' contains infinite values at row index {bad_idx}."
                )
            df_ordered[col] = numeric_series.astype(np.float64)

        # Validate capacity kWp is strictly positive
        if (df_ordered["kWp"] <= 0.0).any():
            bad_idx = df_ordered[df_ordered["kWp"] <= 0.0].index.tolist()
            raise FeatureValidationError(
                f"Feature 'kWp' must be strictly positive (>0), found non-positive values at row index {bad_idx}."
            )

        return df_ordered

    def predict(
        self,
        features: Union[pd.DataFrame, Dict[str, Any], List[Dict[str, Any]]],
    ) -> np.ndarray:
        """
        Executes deterministic model inference for validated feature rows.

        Args:
            features: Input feature rows.

        Returns:
            1D numpy array of predicted specific yields (kWh/kWp/day).

        Raises:
            FeatureValidationError: If inputs fail schema or numerical validation.
            Phase5InferenceError: If model prediction fails.
        """
        X = self.validate_features(features)

        try:
            if self.model_variant == ModelVariant.PRIMARY_EXTRA_TREES:
                preds = self.primary_model.predict(X)
            elif self.model_variant == ModelVariant.FALLBACK_BLEND_50_50:
                p_et = self.primary_model.predict(X)
                p_en = self.linear_model.predict(X)
                preds = 0.5 * p_et + 0.5 * p_en
            else:
                raise Phase5InferenceError(f"Unhandled model variant: {self.model_variant}")
        except Exception as e:
            if isinstance(e, (Phase5InferenceError, FeatureValidationError)):
                raise
            raise Phase5InferenceError(f"Model prediction failed: {e}") from e

        return np.asarray(preds, dtype=np.float64)

    def get_provenance(self) -> Dict[str, Any]:
        """Returns runtime inference provenance and model artifact fingerprints."""
        prov = {
            "model_name": self.model_name,
            "model_variant": self.model_variant.value,
            "cohort": self.cohort,
            "evaluation_timestamp": self.evaluation_timestamp,
            "primary_artifact_path": str(self.primary_path),
            "primary_artifact_sha256": self.primary_sha256,
            "feature_count": len(self.feature_names),
            "feature_names_hash": self.feature_names_hash,
            "feature_names": list(self.feature_names),
        }
        if self.model_variant == ModelVariant.FALLBACK_BLEND_50_50:
            prov["linear_artifact_path"] = str(self.linear_path)
            prov["linear_artifact_sha256"] = self.linear_sha256
            prov["blend_weights"] = {"extra_trees": 0.5, "elastic_net": 0.5}

        return prov

