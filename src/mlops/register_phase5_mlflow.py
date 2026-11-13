"""
SolarSelect Phase 5 MLflow Experiment Tracking & Model Registry Integration.

Registers historical Phase 5 held-out test evaluation benchmarks and primary
production model candidates into a dedicated MLflow experiment without retraining
or modifying frozen DVC-managed artifacts.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional

import joblib
import mlflow
from mlflow.models import infer_signature
from mlflow.tracking import MlflowClient
import pandas as pd


EXPERIMENT_NAME = "SolarSelect-Phase5-Evaluation"
DEFAULT_TRACKING_DB = "mlflow.db"


def compute_md5(filepath: Path) -> str:
    """Compute MD5 hash of a file."""
    hasher = hashlib.md5()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    return hasher.hexdigest()


def compute_sha256(filepath: Path) -> str:
    """Compute SHA-256 hash of a file."""
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    return hasher.hexdigest()


def load_evaluation_evidence(project_root: Path) -> Dict[str, Any]:
    """Load and reconcile Phase 5 metadata and evaluation results."""
    meta_path = project_root / "models/phase5/final_model_metadata.json"
    results_path = project_root / "reports/phase5/test_evaluation_results.csv"

    if not meta_path.exists():
        raise FileNotFoundError(f"Metadata file not found: {meta_path}")
    if not results_path.exists():
        raise FileNotFoundError(f"Results CSV not found: {results_path}")

    with open(meta_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    results_df = pd.read_csv(results_path)

    # Load 29 predictive feature names
    feature_names = metadata["feature_space"]["predictive_feature_names"]

    # Verify input test data schema
    test_csv = project_root / "data/processed/unisolar/test.csv"
    if not test_csv.exists():
        raise FileNotFoundError(f"Test CSV not found: {test_csv}")

    test_df = pd.read_csv(test_csv)
    missing_feats = [feat for feat in feature_names if feat not in test_df.columns]
    if missing_feats:
        raise ValueError(f"Missing required predictive features in test.csv: {missing_feats}")

    input_example = test_df[feature_names].head(2)
    output_example = test_df["target_daily_yield"].head(2)

    return {
        "metadata": metadata,
        "results_df": results_df,
        "feature_names": feature_names,
        "input_example": input_example,
        "output_example": output_example,
    }


def build_run_specifications(evidence: Dict[str, Any], project_root: Path) -> List[Dict[str, Any]]:
    """Build exact run specifications for all 10 Phase 5 evaluation records."""
    metadata = evidence["metadata"]
    results_df = evidence["results_df"]
    feature_names = evidence["feature_names"]

    # Helper to look up metrics in results_df
    def get_metrics_row(cohort_name: str, model_name: str) -> pd.Series:
        matched = results_df[
            (results_df["cohort"].str.startswith(cohort_name)) &
            (results_df["model"] == model_name)
        ]
        if len(matched) == 0:
            raise KeyError(f"No metric row found for cohort={cohort_name}, model={model_name}")
        return matched.iloc[0]

    specs = []

    # =========================================================================
    # 1. Peer Cohort (Dataset B: 22 sites)
    # =========================================================================
    peer_et_row = get_metrics_row("Peer", "Tuned ExtraTrees")
    specs.append({
        "run_name": "peer_cohort_tuned-extra-trees_primary",
        "cohort": "peer",
        "role": "primary_candidate",
        "algorithm": "ExtraTreesRegressor",
        "params": {
            "cohort": "peer",
            "model_name": "Tuned ExtraTreesRegressor",
            "role": "primary_candidate",
            "n_estimators": 100,
            "max_depth": 12,
            "max_features": 0.8,
            "min_samples_split": 2,
            "min_samples_leaf": 1,
            "random_state": 42,
            "n_features_in": len(feature_names),
            "training_sample_count": metadata["peer_cohort_models"]["primary_model"]["training_sample_count"],
            "test_sample_count": int(peer_et_row["n_samples"]),
            "train_calendar_range": metadata["chronological_partitions"]["combined_pretest"]["calendar_range"],
            "test_calendar_range": metadata["chronological_partitions"]["test_held_out"]["calendar_range"],
            "target": "daily_specific_yield_kwh_per_kwp",
        },
        "metrics": {
            "mae": float(peer_et_row["mae"]),
            "rmse": float(peer_et_row["rmse"]),
            "r2": float(peer_et_row["r2"]),
            "bias": float(peer_et_row["bias"]),
            "mae_pct_mean": float(peer_et_row["mae_pct_mean"]),
            "target_mean": float(peer_et_row["target_mean"]),
            "target_std": float(peer_et_row["target_std"]),
            "pred_mean": float(peer_et_row["pred_mean"]),
            "pred_std": float(peer_et_row["pred_std"]),
        },
        "tags": {
            "source": "historical_evaluation",
            "phase": "Phase 5",
            "evaluation_split": "test",
            "cohort": "peer",
            "role": "primary_candidate",
            "acceptance_verdict": metadata["peer_cohort_models"]["primary_model"]["acceptance_verdict"],
            "dvc_model_path": "models/phase5/final/peer_cohort/final_extra_trees.joblib",
            "dvc_pointer_file": "models/phase5/final/peer_cohort/final_extra_trees.joblib.dvc",
            "dvc_model_md5": "420ea113a69405396faab910e25a04a5",
            "feature_count": str(len(feature_names)),
        },
        "register_model": {
            "model_path": project_root / "models/phase5/final/peer_cohort/final_extra_trees.joblib",
            "registered_name": "SolarSelect-Yield-PeerCohort",
            "alias": "champion",
            "description": (
                "Primary accepted production yield forecasting model for single-site recommendations. "
                "Tuned ExtraTreesRegressor trained on 22 peer physical sites (pre-test N=5,328). "
                "Held-out test performance: MAE=0.9050 kWh/kWp/day, RMSE=1.0700, R2=+0.2580."
            ),
            "skops_trusted_types": ["sklearn.tree._tree.Tree"],
        }
    })

    peer_blend_row = get_metrics_row("Peer", "50/50 ExtraTrees + ElasticNet Blend")
    specs.append({
        "run_name": "peer_cohort_blend-50-50_fallback",
        "cohort": "peer",
        "role": "fallback_candidate",
        "algorithm": "EnsembleBlend",
        "params": {
            "cohort": "peer",
            "model_name": "50/50 ExtraTrees + ElasticNet Ensemble Blend",
            "role": "fallback_candidate",
            "weight_extra_trees": 0.5,
            "weight_elastic_net": 0.5,
            "tree_component": "models/phase5/final/peer_cohort/final_extra_trees.joblib",
            "linear_component": "models/phase5/final/peer_cohort/final_elastic_net.joblib",
            "test_sample_count": int(peer_blend_row["n_samples"]),
            "test_calendar_range": metadata["chronological_partitions"]["test_held_out"]["calendar_range"],
            "target": "daily_specific_yield_kwh_per_kwp",
        },
        "metrics": {
            "mae": float(peer_blend_row["mae"]),
            "rmse": float(peer_blend_row["rmse"]),
            "r2": float(peer_blend_row["r2"]),
            "bias": float(peer_blend_row["bias"]),
            "mae_pct_mean": float(peer_blend_row["mae_pct_mean"]),
            "target_mean": float(peer_blend_row["target_mean"]),
            "target_std": float(peer_blend_row["target_std"]),
            "pred_mean": float(peer_blend_row["pred_mean"]),
            "pred_std": float(peer_blend_row["pred_std"]),
        },
        "tags": {
            "source": "historical_evaluation",
            "phase": "Phase 5",
            "evaluation_split": "test",
            "cohort": "peer",
            "role": "fallback_candidate",
            "acceptance_verdict": metadata["peer_cohort_models"]["fallback_model"]["acceptance_verdict"],
            "dvc_tree_component_md5": "420ea113a69405396faab910e25a04a5",
            "dvc_linear_component_md5": "1e80dd099e13b5dcd6dfcfc648d1282c",
            "feature_count": str(len(feature_names)),
        },
        "register_model": None
    })

    peer_enet_row = get_metrics_row("Peer", "Tuned ElasticNet")
    specs.append({
        "run_name": "peer_cohort_tuned-elastic-net_component",
        "cohort": "peer",
        "role": "component",
        "algorithm": "ElasticNet",
        "params": {
            "cohort": "peer",
            "model_name": "Tuned ElasticNet",
            "role": "component",
            "alpha": 0.05,
            "l1_ratio": 0.9,
            "max_iter": 5000,
            "random_state": 42,
            "n_features_in": len(feature_names),
            "test_sample_count": int(peer_enet_row["n_samples"]),
            "test_calendar_range": metadata["chronological_partitions"]["test_held_out"]["calendar_range"],
            "target": "daily_specific_yield_kwh_per_kwp",
        },
        "metrics": {
            "mae": float(peer_enet_row["mae"]),
            "rmse": float(peer_enet_row["rmse"]),
            "r2": float(peer_enet_row["r2"]),
            "bias": float(peer_enet_row["bias"]),
            "mae_pct_mean": float(peer_enet_row["mae_pct_mean"]),
            "target_mean": float(peer_enet_row["target_mean"]),
            "target_std": float(peer_enet_row["target_std"]),
            "pred_mean": float(peer_enet_row["pred_mean"]),
            "pred_std": float(peer_enet_row["pred_std"]),
        },
        "tags": {
            "source": "historical_evaluation",
            "phase": "Phase 5",
            "evaluation_split": "test",
            "cohort": "peer",
            "role": "component",
            "dvc_model_path": "models/phase5/final/peer_cohort/final_elastic_net.joblib",
            "dvc_pointer_file": "models/phase5/final/peer_cohort/final_elastic_net.joblib.dvc",
            "dvc_model_md5": "1e80dd099e13b5dcd6dfcfc648d1282c",
            "feature_count": str(len(feature_names)),
        },
        "register_model": None
    })

    peer_pers_row = get_metrics_row("Peer", "Persistence Baseline (Lag 1)")
    specs.append({
        "run_name": "peer_cohort_persistence_reference",
        "cohort": "peer",
        "role": "reference_baseline",
        "algorithm": "Persistence",
        "params": {
            "cohort": "peer",
            "model_name": "Persistence Baseline (Lag 1)",
            "role": "reference_baseline",
            "rule": "lag1_daily_yield",
            "test_sample_count": int(peer_pers_row["n_samples"]),
            "test_calendar_range": metadata["chronological_partitions"]["test_held_out"]["calendar_range"],
            "target": "daily_specific_yield_kwh_per_kwp",
        },
        "metrics": {
            "mae": float(peer_pers_row["mae"]),
            "rmse": float(peer_pers_row["rmse"]),
            "r2": float(peer_pers_row["r2"]),
            "bias": float(peer_pers_row["bias"]),
            "mae_pct_mean": float(peer_pers_row["mae_pct_mean"]),
            "target_mean": float(peer_pers_row["target_mean"]),
            "target_std": float(peer_pers_row["target_std"]),
            "pred_mean": float(peer_pers_row["pred_mean"]),
            "pred_std": float(peer_pers_row["pred_std"]),
        },
        "tags": {
            "source": "historical_evaluation",
            "phase": "Phase 5",
            "evaluation_split": "test",
            "cohort": "peer",
            "role": "reference_baseline",
        },
        "register_model": None
    })

    peer_mean_row = get_metrics_row("Peer", "Pre-test Mean Baseline")
    specs.append({
        "run_name": "peer_cohort_pretest-mean_baseline",
        "cohort": "peer",
        "role": "naive_baseline",
        "algorithm": "MeanBaseline",
        "params": {
            "cohort": "peer",
            "model_name": "Pre-test Mean Baseline",
            "role": "naive_baseline",
            "pretest_mean_value": 2.7663,
            "test_sample_count": int(peer_mean_row["n_samples"]),
            "test_calendar_range": metadata["chronological_partitions"]["test_held_out"]["calendar_range"],
            "target": "daily_specific_yield_kwh_per_kwp",
        },
        "metrics": {
            "mae": float(peer_mean_row["mae"]),
            "rmse": float(peer_mean_row["rmse"]),
            "r2": float(peer_mean_row["r2"]),
            "bias": float(peer_mean_row["bias"]),
            "mae_pct_mean": float(peer_mean_row["mae_pct_mean"]),
            "target_mean": float(peer_mean_row["target_mean"]),
            "target_std": float(peer_mean_row["target_std"]),
            "pred_mean": float(peer_mean_row["pred_mean"]),
            "pred_std": float(peer_mean_row["pred_std"]),
        },
        "tags": {
            "source": "historical_evaluation",
            "phase": "Phase 5",
            "evaluation_split": "test",
            "cohort": "peer",
            "role": "naive_baseline",
        },
        "register_model": None
    })

    # =========================================================================
    # 2. Full Cohort (Dataset A: 24 sites)
    # =========================================================================
    full_enet_row = get_metrics_row("Full", "Tuned ElasticNet")
    specs.append({
        "run_name": "full_cohort_tuned-elastic-net_primary",
        "cohort": "full",
        "role": "primary_candidate",
        "algorithm": "ElasticNet",
        "params": {
            "cohort": "full",
            "model_name": "Tuned ElasticNet",
            "role": "primary_candidate",
            "alpha": 0.05,
            "l1_ratio": 0.9,
            "max_iter": 5000,
            "random_state": 42,
            "n_features_in": len(feature_names),
            "training_sample_count": metadata["full_cohort_models"]["primary_model"]["training_sample_count"],
            "test_sample_count": int(full_enet_row["n_samples"]),
            "train_calendar_range": metadata["chronological_partitions"]["combined_pretest"]["calendar_range"],
            "test_calendar_range": metadata["chronological_partitions"]["test_held_out"]["calendar_range"],
            "target": "daily_specific_yield_kwh_per_kwp",
        },
        "metrics": {
            "mae": float(full_enet_row["mae"]),
            "rmse": float(full_enet_row["rmse"]),
            "r2": float(full_enet_row["r2"]),
            "bias": float(full_enet_row["bias"]),
            "mae_pct_mean": float(full_enet_row["mae_pct_mean"]),
            "target_mean": float(full_enet_row["target_mean"]),
            "target_std": float(full_enet_row["target_std"]),
            "pred_mean": float(full_enet_row["pred_mean"]),
            "pred_std": float(full_enet_row["pred_std"]),
        },
        "tags": {
            "source": "historical_evaluation",
            "phase": "Phase 5",
            "evaluation_split": "test",
            "cohort": "full",
            "role": "primary_candidate",
            "acceptance_verdict": metadata["full_cohort_models"]["primary_model"]["acceptance_verdict"],
            "limitations": "Campus-level tracking only; prohibited for single-site panel recommendations due to Site 19/24 unverified metering anomalies.",
            "dvc_model_path": "models/phase5/final/full_cohort/final_elastic_net.joblib",
            "dvc_pointer_file": "models/phase5/final/full_cohort/final_elastic_net.joblib.dvc",
            "dvc_model_md5": "2ea38e4cca315095f76e07d63c4c2064",
            "feature_count": str(len(feature_names)),
        },
        "register_model": {
            "model_path": project_root / "models/phase5/final/full_cohort/final_elastic_net.joblib",
            "registered_name": "SolarSelect-Yield-FullCohort",
            "alias": "campus-tracking-conditional",
            "description": (
                "Macro campus-level yield tracking model trained on all 24 campus sites (pre-test N=5,807). "
                "Tuned ElasticNet (alpha=0.05, l1_ratio=0.9). "
                "LIMITATION: Conditioned strictly on macro-campus tracking. Prohibited for single-site "
                "rooftop recommendations due to unverified metering anomalies at Site 19 and 24."
            ),
            "skops_trusted_types": None,
        }
    })

    full_blend_row = get_metrics_row("Full", "70/30 ElasticNet + ExtraTrees Blend")
    specs.append({
        "run_name": "full_cohort_blend-70-30_fallback",
        "cohort": "full",
        "role": "fallback_candidate",
        "algorithm": "EnsembleBlend",
        "params": {
            "cohort": "full",
            "model_name": "70/30 ElasticNet + ExtraTrees Ensemble Blend",
            "role": "fallback_candidate",
            "weight_elastic_net": 0.7,
            "weight_extra_trees": 0.3,
            "linear_component": "models/phase5/final/full_cohort/final_elastic_net.joblib",
            "tree_component": "models/phase5/final/full_cohort/final_extra_trees.joblib",
            "test_sample_count": int(full_blend_row["n_samples"]),
            "test_calendar_range": metadata["chronological_partitions"]["test_held_out"]["calendar_range"],
            "target": "daily_specific_yield_kwh_per_kwp",
        },
        "metrics": {
            "mae": float(full_blend_row["mae"]),
            "rmse": float(full_blend_row["rmse"]),
            "r2": float(full_blend_row["r2"]),
            "bias": float(full_blend_row["bias"]),
            "mae_pct_mean": float(full_blend_row["mae_pct_mean"]),
            "target_mean": float(full_blend_row["target_mean"]),
            "target_std": float(full_blend_row["target_std"]),
            "pred_mean": float(full_blend_row["pred_mean"]),
            "pred_std": float(full_blend_row["pred_std"]),
        },
        "tags": {
            "source": "historical_evaluation",
            "phase": "Phase 5",
            "evaluation_split": "test",
            "cohort": "full",
            "role": "fallback_candidate",
            "acceptance_verdict": metadata["full_cohort_models"]["fallback_model"]["acceptance_verdict"],
            "dvc_linear_component_md5": "2ea38e4cca315095f76e07d63c4c2064",
            "dvc_tree_component_md5": "8a723304a552c673e65485a0b2206189",
            "feature_count": str(len(feature_names)),
        },
        "register_model": None
    })

    full_et_row = get_metrics_row("Full", "Tuned ExtraTrees")
    specs.append({
        "run_name": "full_cohort_tuned-extra-trees_component",
        "cohort": "full",
        "role": "component",
        "algorithm": "ExtraTreesRegressor",
        "params": {
            "cohort": "full",
            "model_name": "Tuned ExtraTreesRegressor",
            "role": "component",
            "n_estimators": 100,
            "max_depth": 12,
            "max_features": 0.8,
            "min_samples_split": 2,
            "min_samples_leaf": 1,
            "random_state": 42,
            "n_features_in": len(feature_names),
            "test_sample_count": int(full_et_row["n_samples"]),
            "test_calendar_range": metadata["chronological_partitions"]["test_held_out"]["calendar_range"],
            "target": "daily_specific_yield_kwh_per_kwp",
        },
        "metrics": {
            "mae": float(full_et_row["mae"]),
            "rmse": float(full_et_row["rmse"]),
            "r2": float(full_et_row["r2"]),
            "bias": float(full_et_row["bias"]),
            "mae_pct_mean": float(full_et_row["mae_pct_mean"]),
            "target_mean": float(full_et_row["target_mean"]),
            "target_std": float(full_et_row["target_std"]),
            "pred_mean": float(full_et_row["pred_mean"]),
            "pred_std": float(full_et_row["pred_std"]),
        },
        "tags": {
            "source": "historical_evaluation",
            "phase": "Phase 5",
            "evaluation_split": "test",
            "cohort": "full",
            "role": "component",
            "dvc_model_path": "models/phase5/final/full_cohort/final_extra_trees.joblib",
            "dvc_pointer_file": "models/phase5/final/full_cohort/final_extra_trees.joblib.dvc",
            "dvc_model_md5": "8a723304a552c673e65485a0b2206189",
            "feature_count": str(len(feature_names)),
        },
        "register_model": None
    })

    full_pers_row = get_metrics_row("Full", "Persistence Baseline (Lag 1)")
    specs.append({
        "run_name": "full_cohort_persistence_reference",
        "cohort": "full",
        "role": "reference_baseline",
        "algorithm": "Persistence",
        "params": {
            "cohort": "full",
            "model_name": "Persistence Baseline (Lag 1)",
            "role": "reference_baseline",
            "rule": "lag1_daily_yield",
            "test_sample_count": int(full_pers_row["n_samples"]),
            "test_calendar_range": metadata["chronological_partitions"]["test_held_out"]["calendar_range"],
            "target": "daily_specific_yield_kwh_per_kwp",
        },
        "metrics": {
            "mae": float(full_pers_row["mae"]),
            "rmse": float(full_pers_row["rmse"]),
            "r2": float(full_pers_row["r2"]),
            "bias": float(full_pers_row["bias"]),
            "mae_pct_mean": float(full_pers_row["mae_pct_mean"]),
            "target_mean": float(full_pers_row["target_mean"]),
            "target_std": float(full_pers_row["target_std"]),
            "pred_mean": float(full_pers_row["pred_mean"]),
            "pred_std": float(full_pers_row["pred_std"]),
        },
        "tags": {
            "source": "historical_evaluation",
            "phase": "Phase 5",
            "evaluation_split": "test",
            "cohort": "full",
            "role": "reference_baseline",
        },
        "register_model": None
    })

    full_mean_row = get_metrics_row("Full", "Pre-test Mean Baseline")
    specs.append({
        "run_name": "full_cohort_pretest-mean_baseline",
        "cohort": "full",
        "role": "naive_baseline",
        "algorithm": "MeanBaseline",
        "params": {
            "cohort": "full",
            "model_name": "Pre-test Mean Baseline",
            "role": "naive_baseline",
            "pretest_mean_value": 3.8672,
            "test_sample_count": int(full_mean_row["n_samples"]),
            "test_calendar_range": metadata["chronological_partitions"]["test_held_out"]["calendar_range"],
            "target": "daily_specific_yield_kwh_per_kwp",
        },
        "metrics": {
            "mae": float(full_mean_row["mae"]),
            "rmse": float(full_mean_row["rmse"]),
            "r2": float(full_mean_row["r2"]),
            "bias": float(full_mean_row["bias"]),
            "mae_pct_mean": float(full_mean_row["mae_pct_mean"]),
            "target_mean": float(full_mean_row["target_mean"]),
            "target_std": float(full_mean_row["target_std"]),
            "pred_mean": float(full_mean_row["pred_mean"]),
            "pred_std": float(full_mean_row["pred_std"]),
        },
        "tags": {
            "source": "historical_evaluation",
            "phase": "Phase 5",
            "evaluation_split": "test",
            "cohort": "full",
            "role": "naive_baseline",
        },
        "register_model": None
    })

    return specs


def run_dry_run(specs: List[Dict[str, Any]], evidence: Dict[str, Any]) -> None:
    """Print complete dry-run plan without any database writes."""
    print("=" * 80)
    print("SOLARSELECT MLFLOW REGISTRATION DRY RUN (NO DATABASE WRITES)")
    print("=" * 80)
    print(f"Target Experiment: {EXPERIMENT_NAME}")
    print(f"Total Runs to Log: {len(specs)}")
    print(f"Predictive Feature Space: 29 features verified from test.csv")
    print("-" * 80)

    for i, spec in enumerate(specs, 1):
        print(f"\n[{i:02d}/10] RUN: {spec['run_name']}")
        print(f"  Cohort: {spec['cohort']} | Role: {spec['role']} | Algorithm: {spec['algorithm']}")
        print(f"  Params ({len(spec['params'])}):")
        for k, v in spec["params"].items():
            print(f"    - {k}: {v}")
        print(f"  Metrics ({len(spec['metrics'])}):")
        for k, v in spec["metrics"].items():
            print(f"    - {k}: {v}")
        print(f"  Tags ({len(spec['tags'])}):")
        for k, v in spec["tags"].items():
            print(f"    - {k}: {v}")
        if spec["register_model"]:
            rm = spec["register_model"]
            print(f"  Model Registration:")
            print(f"    - Registered Name: {rm['registered_name']}")
            print(f"    - Model File: {rm['model_path']}")
            print(f"    - Approved Alias: {rm['alias']}")
            print(f"    - Description: {rm['description']}")

    print("\n" + "=" * 80)
    print("DRY RUN COMPLETED: 0 database writes performed.")
    print("=" * 80)


def execute_registration(
    specs: List[Dict[str, Any]],
    evidence: Dict[str, Any],
    tracking_uri: str,
    project_root: Path
) -> Dict[str, Any]:
    """
    Execute controlled, idempotent database writes and model registrations.
    
    This function:
    1. Connects to the local SQLite MLflow tracking backend (mlflow.db).
    2. Retrieves or creates the dedicated experiment 'SolarSelect-Phase5-Evaluation' (Experiment ID: 2).
    3. Checks for existing runs by name to ensure complete idempotency (will not create duplicate runs).
    4. Logs parameters, evaluation metrics (MAE, RMSE, R2, bias), and tags for all 10 evaluation runs.
    5. For primary models, verifies MD5 hash against DVC pointers, logs the serialized sklearn model
       with its 29-feature signature, registers the model in the MLflow Model Registry,
       and assigns the production alias (@champion or @campus-tracking-conditional).
    """
    mlflow.set_tracking_uri(tracking_uri)
    client = MlflowClient(tracking_uri)

    # 1. Create or get experiment 'SolarSelect-Phase5-Evaluation'
    exp = mlflow.get_experiment_by_name(EXPERIMENT_NAME)
    if exp is None:
        artifact_loc = (project_root / "mlruns").resolve().as_uri()
        exp_id = mlflow.create_experiment(EXPERIMENT_NAME, artifact_location=artifact_loc)
        print(f"Created experiment '{EXPERIMENT_NAME}' (ID: {exp_id})")
    else:
        exp_id = exp.experiment_id
        print(f"Using existing experiment '{EXPERIMENT_NAME}' (ID: {exp_id})")

    # 2. Fetch existing runs in this experiment to guarantee idempotent re-runs
    existing_runs = mlflow.search_runs(experiment_ids=[exp_id])
    existing_run_names = set()
    if not existing_runs.empty and "tags.mlflow.runName" in existing_runs.columns:
        existing_run_names = set(existing_runs["tags.mlflow.runName"].dropna())

    # 3. Infer standard input/output schema signature for the 29 predictive features
    X_example = evidence["input_example"]
    y_example = evidence["output_example"]
    signature = infer_signature(X_example, y_example)

    logged_runs = []
    registered_models = []

    # 4. Iterate over each of the 10 Phase 5 run specifications
    for spec in specs:
        run_name = spec["run_name"]
        
        # Idempotency check: skip run if already registered
        if run_name in existing_run_names:
            print(f"Run '{run_name}' already exists in experiment {exp_id}. Skipping creation.")
            continue

        with mlflow.start_run(experiment_id=exp_id, run_name=run_name) as run:
            run_id = run.info.run_id
            print(f"Logging run '{run_name}' (ID: {run_id})...")

            # Log model hyperparameters and evaluation configuration
            mlflow.log_params(spec["params"])

            # Log test partition evaluation metrics (MAE, RMSE, R2, bias, sample counts)
            mlflow.log_metrics(spec["metrics"])

            # Set audit provenance tags (source=historical_evaluation, cohort, DVC pointers)
            mlflow.set_tags(spec["tags"])

            # 5. Register model in MLflow Model Registry if specified
            rm = spec["register_model"]
            if rm:
                model_path = rm["model_path"]
                if not model_path.exists():
                    raise FileNotFoundError(f"Model file not found: {model_path}")

                # Integrity check: verify MD5 hash matches authoritative DVC pointer before loading
                model_md5 = compute_md5(model_path)
                expected_md5 = spec["tags"]["dvc_model_md5"]
                if model_md5 != expected_md5:
                    raise ValueError(
                        f"MD5 mismatch for {model_path}! Expected: {expected_md5}, Actual: {model_md5}"
                    )

                # Load frozen model binary (read-only; no retraining)
                model_obj = joblib.load(model_path)

                # Log model package with exact 29-feature signature and input sample
                log_kwargs = {
                    "sk_model": model_obj,
                    "name": "model",
                    "signature": signature,
                    "input_example": X_example,
                    "registered_model_name": rm["registered_name"],
                }
                if rm.get("skops_trusted_types"):
                    log_kwargs["skops_trusted_types"] = rm["skops_trusted_types"]

                mlflow.sklearn.log_model(**log_kwargs)

                # Update registered model description & assign production alias
                reg_name = rm["registered_name"]
                alias = rm["alias"]
                desc = rm["description"]

                client.update_registered_model(name=reg_name, description=desc)

                # Retrieve latest registered version number
                versions = client.search_model_versions(f"name = '{reg_name}'")
                latest_v = max(int(v.version) for v in versions)

                # Assign alias (@champion or @campus-tracking-conditional)
                client.set_registered_model_alias(name=reg_name, alias=alias, version=latest_v)
                print(f"  Registered '{reg_name}' v{latest_v} with alias @{alias}")

                registered_models.append({
                    "name": reg_name,
                    "version": latest_v,
                    "alias": alias,
                    "run_id": run_id
                })

            logged_runs.append({
                "run_name": run_name,
                "run_id": run_id,
                "cohort": spec["cohort"],
                "role": spec["role"]
            })

    return {
        "experiment_id": exp_id,
        "logged_runs": logged_runs,
        "registered_models": registered_models
    }


def main():
    parser = argparse.ArgumentParser(description="Register SolarSelect Phase 5 models and evaluation in MLflow.")
    parser.add_argument("--dry-run", action="store_true", help="Print plan without modifying SQLite database.")
    parser.add_argument("--tracking-uri", default=None, help="Custom tracking URI (defaults to sqlite:///mlflow.db).")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[2]

    evidence = load_evaluation_evidence(project_root)
    specs = build_run_specifications(evidence, project_root)

    if args.dry_run:
        run_dry_run(specs, evidence)
        sys.exit(0)

    # Establish canonical tracking URI
    if args.tracking_uri:
        tracking_uri = args.tracking_uri
    else:
        db_path = (project_root / DEFAULT_TRACKING_DB).resolve()
        tracking_uri = f"sqlite:///{db_path.as_posix()}"

    print(f"Connecting to MLflow tracking URI: {tracking_uri}")
    result = execute_registration(specs, evidence, tracking_uri, project_root)
    print("\nRegistration complete:")
    print(f"Experiment ID: {result['experiment_id']}")
    print(f"Runs Logged: {len(result['logged_runs'])}")
    print(f"Models Registered: {len(result['registered_models'])}")


if __name__ == "__main__":
    main()
