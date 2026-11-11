"""
SolarSelect Phase 5 MLflow Visualization Generator & Logger.

Generates academic-quality model evaluation visualizations for the primary
production models registered in MLflow Experiment 'SolarSelect-Phase5-Evaluation'
and attaches them as artifacts directly to the existing primary runs.

Strictly adheres to:
1. Zero model retraining and zero model file modification.
2. Direct attachment to existing MLflow run IDs (no duplicate runs).
3. Preservation of all historical MLflow runs and registered model aliases.
4. Scientific visualization conventions (residual = actual - predicted,
   Site 19/24 anomaly callouts, standardized coefficient disclaimers).
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Tuple

import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import mlflow
from mlflow.tracking import MlflowClient
import numpy as np
import pandas as pd
import seaborn as sns


EXPERIMENT_NAME = "SolarSelect-Phase5-Evaluation"
DEFAULT_TRACKING_DB = "mlflow.db"

# Reference hashes for the 8 frozen Phase 5 model artifacts (Session 57/58 baseline)
EXPECTED_MODEL_HASHES = {
    "models/phase5/final/peer_cohort/final_extra_trees.joblib": {
        "md5": "420ea113a69405396faab910e25a04a5",
        "sha256": "39b4a11beb5423dff926e43b4594b7938957183daaa16f16bdea7e5dc54ecfe9",
    },
    "models/phase5/final/peer_cohort/final_elastic_net.joblib": {
        "md5": "1e80dd099e13b5dcd6dfcfc648d1282c",
        "sha256": "422bda69e708e2129c0e1407bb6cd536971003b7f64dcc635ddc82da3acae7bb",
    },
    "models/phase5/final/full_cohort/final_elastic_net.joblib": {
        "md5": "2ea38e4cca315095f76e07d63c4c2064",
        "sha256": "93cb7b3b0a486c7e0e1f1fc974dfa9926236cb1b461d1c7321d7e315b9b4f49e",
    },
    "models/phase5/final/full_cohort/final_extra_trees.joblib": {
        "md5": "8a723304a552c673e65485a0b2206189",
        "sha256": "b0a3615a77991bc313203ae76927ad357be4faa1de38a8f2854b82d62a8dbf76",
    },
    "models/phase5/peer_cohort/tuned_extra_trees.joblib": {
        "md5": "46943896231df6fefcb0bd26580944a9",
        "sha256": "a3e258a869d4e920123f28f0db32fdf58e2e588d5ca2ad759188433a1ad9e1de",
    },
    "models/phase5/peer_cohort/tuned_elastic_net.joblib": {
        "md5": "5d9fd3f8f7875d5da4340670eef358a2",
        "sha256": "1a125ca75aaa6019cef0e0ad044504cb35081d2cf5985404f08b1293557897e0",
    },
    "models/phase5/full_cohort/tuned_elastic_net.joblib": {
        "md5": "0ba04d6bb4516c908d5d764628c9d71f",
        "sha256": "48ecb19d711b06a67e85dd83c5d21d96f8a5732b19a2b1c657a8cb22319ebc65",
    },
    "models/phase5/full_cohort/tuned_extra_trees.joblib": {
        "md5": "55136a3e3d8ac72241ace2756c5cc89d",
        "sha256": "772ec9475f611295c1b102c933ae7756bc43cacff7d102c88b4279b258c70664",
    },
}


def compute_file_hashes(filepath: Path) -> Tuple[str, str]:
    """Compute MD5 and SHA-256 hashes of a file."""
    md5_h = hashlib.md5()
    sha_h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            md5_h.update(chunk)
            sha_h.update(chunk)
    return md5_h.hexdigest(), sha_h.hexdigest()


def verify_model_immutability(project_root: Path) -> None:
    """Verify all 8 Phase 5 model artifacts match authoritative frozen hashes."""
    for rel_path, expected in EXPECTED_MODEL_HASHES.items():
        full_path = project_root / rel_path
        if not full_path.exists():
            raise FileNotFoundError(f"Required model artifact missing: {full_path}")
        actual_md5, actual_sha = compute_file_hashes(full_path)
        if actual_md5 != expected["md5"] or actual_sha != expected["sha256"]:
            raise ValueError(
                f"Model artifact integrity violation in {rel_path}!\n"
                f"Expected MD5: {expected['md5']} | Actual: {actual_md5}\n"
                f"Expected SHA-256: {expected['sha256']} | Actual: {actual_sha}"
            )


def setup_plotting_style() -> None:
    """Configure matplotlib styling for publication-grade figures."""
    style_candidate = "seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default"
    plt.style.use(style_candidate)
    plt.rcParams.update({
        "font.sans-serif": ["Helvetica", "Arial", "DejaVu Sans"],
        "axes.edgecolor": "#333333",
        "axes.linewidth": 0.8,
        "grid.color": "#e0e0e0",
        "grid.linestyle": "--",
        "grid.linewidth": 0.5,
        "figure.titlesize": 13,
        "axes.titlesize": 11,
        "axes.labelsize": 10,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "legend.fontsize": 9,
    })


# ---------------------------------------------------------------------------
# Data and Model Loading
# ---------------------------------------------------------------------------

def load_peer_cohort_data(project_root: Path) -> Tuple[pd.DataFrame, List[str], np.ndarray, np.ndarray, Any]:
    """Load Peer Cohort test data and run deterministic inference using frozen ExtraTrees."""
    test_path = project_root / "data/processed/unisolar/peer_cohort/test.csv"
    model_path = project_root / "models/phase5/final/peer_cohort/final_extra_trees.joblib"
    
    df_test = pd.read_csv(test_path)
    model = joblib.load(model_path)
    features = list(model.feature_names_in_)
    
    y_true = df_test["target_daily_yield"].values
    y_pred = model.predict(df_test[features])
    return df_test, features, y_true, y_pred, model


def load_full_cohort_data(project_root: Path) -> Tuple[pd.DataFrame, List[str], np.ndarray, np.ndarray, Any]:
    """Load Full Cohort test data and run deterministic inference using frozen ElasticNet."""
    test_path = project_root / "data/processed/unisolar/test.csv"
    model_path = project_root / "models/phase5/final/full_cohort/final_elastic_net.joblib"
    
    df_test = pd.read_csv(test_path)
    model = joblib.load(model_path)
    features = list(model.feature_names_in_)
    
    y_true = df_test["target_daily_yield"].values
    y_pred = model.predict(df_test[features])
    return df_test, features, y_true, y_pred, model


def load_reports(project_root: Path) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load evaluation CSV reports for site-wise breakdown, model comparison, and feature analysis."""
    eval_path = project_root / "reports/phase5/test_evaluation_results.csv"
    site_path = project_root / "reports/phase5/test_site_evaluation.csv"
    feat_path = project_root / "reports/phase4/feature_importance_analysis.csv"
    
    df_eval = pd.read_csv(eval_path)
    df_site = pd.read_csv(site_path)
    df_feat = pd.read_csv(feat_path)
    return df_eval, df_site, df_feat


# ---------------------------------------------------------------------------
# Visualization Builders: Peer Cohort
# ---------------------------------------------------------------------------

def create_peer_actual_vs_predicted(y_true: np.ndarray, y_pred: np.ndarray) -> plt.Figure:
    """Create actual vs predicted scatter plot for Peer Cohort ExtraTrees."""
    fig, ax = plt.subplots(figsize=(7.5, 6.5), dpi=300)
    
    # Scatter points
    ax.scatter(
        y_true, y_pred,
        color="#1f77b4", alpha=0.5, s=26, edgecolors="none",
        label="Test Site-Days (22 Peer Sites, N = 1,128)"
    )
    
    # 45-degree identity line
    max_val = max(np.max(y_true), np.max(y_pred)) + 0.5
    min_val = min(np.min(y_true), np.min(y_pred)) - 0.2
    ax.plot([min_val, max_val], [min_val, max_val], color="#d62728", linestyle="--", linewidth=1.6, label="Ideal Calibration (y = x)")
    
    # Metrics calculation (matches documented metrics)
    mae = float(np.mean(np.abs(y_true - y_pred)))
    rmse = float(np.sqrt(np.mean((y_true - y_pred) ** 2)))
    ss_res = np.sum((y_true - y_pred) ** 2)
    ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
    r2 = float(1 - ss_res / ss_tot)
    bias = float(np.mean(y_true - y_pred))
    
    metrics_text = (
        f"Evaluation Metrics (N = {len(y_true)}):\n"
        f"  MAE:       {mae:.4f} kWh/kWp/day\n"
        f"  RMSE:      {rmse:.4f} kWh/kWp/day\n"
        f"  R²:        {r2:+.4f}\n"
        f"  Mean Bias: {bias:+.4f} kWh/kWp/day"
    )
    ax.text(
        0.05, 0.95, metrics_text,
        transform=ax.transAxes, verticalalignment="top",
        bbox=dict(boxstyle="round,pad=0.5", facecolor="#ffffff", edgecolor="#b0bec5", alpha=0.9),
        fontsize=9, family="monospace"
    )
    
    ax.set_xlim(min_val, max_val)
    ax.set_ylim(min_val, max_val)
    ax.set_xlabel("Observed Specific Daily Yield (kWh/kWp/day)")
    ax.set_ylabel("Predicted Specific Daily Yield (kWh/kWp/day)")
    ax.set_title("Peer Cohort Primary Model (Tuned ExtraTrees) — Observed vs. Predicted Yield\nHeld-Out Test Partition (2022-03-01 to 2022-04-23, N = 1,128)")
    ax.legend(loc="lower right")
    fig.tight_layout()
    return fig


def create_peer_residual_diagnostics(y_true: np.ndarray, y_pred: np.ndarray) -> plt.Figure:
    """Create residual diagnostics (distribution + residual vs predicted) for Peer ExtraTrees."""
    residuals = y_true - y_pred  # Strict definition: actual - predicted
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5.5), dpi=300)
    
    # Left: Residual Distribution
    sns.histplot(residuals, kde=True, bins=35, color="#2ca02c", alpha=0.5, edgecolor="black", linewidth=0.5, ax=ax1)
    mean_bias = float(np.mean(residuals))
    std_err = float(np.std(residuals))
    
    ax1.axvline(0.0, color="#d62728", linestyle="--", linewidth=1.5, label="Zero Bias (e = 0)")
    ax1.axvline(mean_bias, color="#000080", linestyle=":", linewidth=1.5, label=f"Mean Bias: {mean_bias:+.4f}")
    
    stat_box = (
        f"Residual Distribution:\n"
        f"  Mean Bias: {mean_bias:+.4f}\n"
        f"  Std Dev:   {std_err:.4f}\n"
        f"  Median:    {np.median(residuals):+.4f}"
    )
    ax1.text(
        0.05, 0.95, stat_box,
        transform=ax1.transAxes, verticalalignment="top",
        bbox=dict(boxstyle="round,pad=0.5", facecolor="#ffffff", edgecolor="#b0bec5", alpha=0.9),
        fontsize=8.5, family="monospace"
    )
    ax1.set_xlabel("Residual Error: e = Actual - Predicted (kWh/kWp/day)")
    ax1.set_ylabel("Observation Count")
    ax1.set_title("Residual Error Density Distribution")
    ax1.legend(loc="upper right")
    
    # Right: Residual vs Predicted
    ax2.scatter(y_pred, residuals, color="#1f77b4", alpha=0.5, s=24, edgecolors="none")
    ax2.axhline(0.0, color="#d62728", linestyle="--", linewidth=1.5, label="Zero Reference (e = 0)")
    
    # Trend line
    sort_idx = np.argsort(y_pred)
    z = np.polyfit(y_pred, residuals, deg=2)
    p = np.poly1d(z)
    ax2.plot(y_pred[sort_idx], p(y_pred[sort_idx]), color="#ff7f0e", linewidth=2.0, label="Polynomial Trend")
    
    ax2.set_xlabel("Predicted Specific Daily Yield (kWh/kWp/day)")
    ax2.set_ylabel("Residual Error: e = Actual - Predicted (kWh/kWp/day)")
    ax2.set_title("Residual Error vs. Predicted Specific Yield")
    ax2.legend(loc="upper right")
    
    fig.suptitle(
        "Peer Cohort Primary Model (Tuned ExtraTrees) — Residual Diagnostics\n"
        "Residual Definition: e = Actual - Predicted (Held-Out Test Set, N = 1,128)",
        fontsize=12, y=1.02
    )
    fig.tight_layout()
    return fig


def create_peer_feature_importance(model: Any, df_feat: pd.DataFrame) -> plt.Figure:
    """Create feature importance plot for Peer ExtraTrees cross-referenced with Phase 4 permutation drop."""
    feature_names = list(model.feature_names_in_)
    importances = model.feature_importances_
    
    # Merge with Phase 4 permutation drop evidence
    feat_df = pd.DataFrame({"Feature": feature_names, "MDI": importances})
    feat_df = feat_df.merge(df_feat[["Feature", "Peer_ET_Perm_RMSE_Drop"]], on="Feature", how="left")
    feat_df = feat_df.sort_values("MDI", ascending=False).head(15).reset_index(drop=True)
    
    fig, ax = plt.subplots(figsize=(10.5, 6.5), dpi=300)
    y_pos = np.arange(len(feat_df))
    bars = ax.barh(y_pos, feat_df["MDI"], color="#1f77b4", alpha=0.85, edgecolor="#0d47a1", height=0.65)
    
    # Invert to place largest at top
    ax.set_yticks(y_pos)
    ax.set_yticklabels(feat_df["Feature"])
    ax.invert_yaxis()
    
    # Annotate bars with MDI and Permutation drop
    for idx, (bar, mdi_val, perm_val) in enumerate(zip(bars, feat_df["MDI"], feat_df["Peer_ET_Perm_RMSE_Drop"])):
        perm_str = f"Perm ΔRMSE: {perm_val:+.4f}" if pd.notnull(perm_val) else "N/A"
        ax.text(
            bar.get_width() + 0.002, bar.get_y() + bar.get_height() / 2,
            f"MDI: {mdi_val:.4f}  ({perm_str})",
            va="center", fontsize=8, color="#263238"
        )
    
    ax.set_xlim(0, max(feat_df["MDI"]) * 1.35)
    ax.set_xlabel("Mean Decrease in Impurity (MDI / Gini Importance)")
    ax.set_title("Peer Cohort ExtraTrees — Top 15 Predictive Features (MDI)\nCross-Referenced with Phase 4 Permutation Importance Drop")
    fig.tight_layout()
    return fig


def create_peer_site_wise_performance(df_site: pd.DataFrame) -> plt.Figure:
    """Create site-wise MAE and Bias breakdown across 22 Peer Cohort sites."""
    # Filter peer sites (where peer_et_mae is valid)
    peer_sites = df_site[df_site["peer_et_mae"].notnull()].copy()
    peer_sites["SiteKeyStr"] = peer_sites["SiteKey"].astype(str)
    
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(13.5, 7.5), dpi=300, sharex=True)
    
    x = np.arange(len(peer_sites))
    # Top: MAE
    ax1.bar(x, peer_sites["peer_et_mae"], color="#1f77b4", alpha=0.8, edgecolor="black", width=0.65)
    ax1.axhline(0.9050, color="#d62728", linestyle="--", linewidth=1.5, label="Overall Peer Test MAE (0.9050)")
    ax1.set_ylabel("MAE (kWh/kWp/day)")
    ax1.set_title("Site-Wise Mean Absolute Error (MAE)")
    ax1.legend(loc="upper right")
    
    # Bottom: Bias
    bias_colors = ["#1f77b4" if b >= 0 else "#d62728" for b in peer_sites["peer_et_bias"]]
    ax2.bar(x, peer_sites["peer_et_bias"], color=bias_colors, alpha=0.8, edgecolor="black", width=0.65)
    ax2.axhline(0.0, color="#333333", linestyle="-", linewidth=1.0)
    ax2.axhline(-0.1036, color="#000080", linestyle="--", linewidth=1.5, label="Overall Peer Test Bias (-0.1036)")
    ax2.set_ylabel("Bias: Actual - Pred (kWh/kWp/day)")
    ax2.set_xlabel("UNISOLAR Site Key")
    ax2.set_title("Site-Wise Tracking Bias (Actual - Predicted)")
    ax2.set_xticks(x)
    ax2.set_xticklabels(peer_sites["SiteKeyStr"], rotation=0)
    ax2.legend(loc="upper right")
    
    fig.suptitle("Peer Cohort (22 Sites) — Site-Wise Test Performance Benchmark\nHeld-Out Test Evaluation (March 1 – April 23, 2022)", fontsize=12, y=1.01)
    fig.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# Visualization Builders: Full Cohort
# ---------------------------------------------------------------------------

def create_full_actual_vs_predicted(df_test: pd.DataFrame, y_pred: np.ndarray) -> plt.Figure:
    """Create actual vs predicted scatter plot for Full Cohort ElasticNet with anomaly callouts."""
    fig, ax = plt.subplots(figsize=(8.5, 7.5), dpi=300)
    y_true = df_test["target_daily_yield"].values
    
    # Separate peer sites, site 19, site 24
    mask_19 = df_test["SiteKey"] == 19
    mask_24 = df_test["SiteKey"] == 24
    mask_peer = (~mask_19) & (~mask_24)
    
    # Normal peer sites
    ax.scatter(
        y_true[mask_peer], y_pred[mask_peer],
        color="#1f77b4", alpha=0.45, s=26, edgecolors="none",
        label=f"Peer Sites (22 Sites, N = {np.sum(mask_peer)})"
    )
    # Site 24 anomaly
    ax.scatter(
        y_true[mask_24], y_pred[mask_24],
        color="#ff7f0e", marker="^", s=55, alpha=0.9, edgecolors="black", linewidths=0.5,
        label=f"Site 24 Metering Anomaly (N = {np.sum(mask_24)}, Actual Mean ~5.38)"
    )
    # Site 19 anomaly
    ax.scatter(
        y_true[mask_19], y_pred[mask_19],
        color="#d62728", marker="D", s=65, alpha=0.9, edgecolors="black", linewidths=0.5,
        label=f"Site 19 Metering Anomaly (N = {np.sum(mask_19)}, Actual Mean ~19.00)"
    )
    
    # 45-degree calibration line
    min_val, max_val = -0.5, 35.0
    ax.plot([min_val, max_val], [min_val, max_val], color="#d62728", linestyle="--", linewidth=1.5, label="Ideal Calibration (y = x)")
    
    # Documented test metrics box (upper left - completely clear of data points)
    metrics_text = (
        "Full Cohort Test Metrics (N = 1,232):\n"
        "  MAE:       1.1463 kWh/kWp/day\n"
        "  RMSE:      1.9494 kWh/kWp/day\n"
        "  R²:        +0.7407\n"
        "  Mean Bias: -0.3144 kWh/kWp/day\n"
        "─────────────────────────────\n"
        "Site 19: MAE = 6.3208 | Bias = -3.0097\n"
        "Site 24: MAE = 1.8560 | Bias = -0.0093"
    )
    ax.text(
        0.04, 0.96, metrics_text,
        transform=ax.transAxes, verticalalignment="top", horizontalalignment="left",
        bbox=dict(boxstyle="round,pad=0.5", facecolor="#ffffff", edgecolor="#cbd5e1", alpha=0.95),
        fontsize=8.5, family="monospace"
    )
    
    # Legend cleanly placed in empty lower-right quadrant above warning banner
    ax.legend(
        loc="lower right", bbox_to_anchor=(0.96, 0.20),
        framealpha=0.95, facecolor="#ffffff", edgecolor="#cbd5e1", fontsize=8.5
    )
    
    # Operational Warning Box positioned in completely open lower-right corner
    warning_text = (
        "OPERATIONAL WARNING / DOCUMENTED LIMITATION:\n"
        "Sites 19 & 24 represent unverified metering anomalies (up to 492% STC yield).\n"
        "Model conditionally approved strictly for macro campus-level tracking.\n"
        "Strictly prohibited for single-site rooftop panel recommendations."
    )
    ax.text(
        0.96, 0.04, warning_text,
        transform=ax.transAxes, verticalalignment="bottom", horizontalalignment="right",
        bbox=dict(boxstyle="round,pad=0.5", facecolor="#fef9c3", edgecolor="#eab308", alpha=0.95),
        fontsize=8.0, weight="bold", color="#991b1b"
    )
    
    ax.set_xlim(min_val, max_val)
    ax.set_ylim(min_val, max_val)
    ax.set_xlabel("Observed Specific Daily Yield (kWh/kWp/day)", fontsize=10.5)
    ax.set_ylabel("Predicted Specific Daily Yield (kWh/kWp/day)", fontsize=10.5)
    ax.set_title(
        "Full Cohort Primary Model (Tuned ElasticNet) — Observed vs. Predicted Yield\n"
        "Held-Out Test Partition with Metering Anomalies Highlighted (N = 1,232)",
        fontsize=12, pad=12
    )
    fig.tight_layout()
    return fig


def create_full_residual_diagnostics(df_test: pd.DataFrame, y_pred: np.ndarray) -> plt.Figure:
    """Create residual diagnostics for Full Cohort ElasticNet distinguishing anomalies."""
    y_true = df_test["target_daily_yield"].values
    residuals = y_true - y_pred  # Strict definition: actual - predicted
    
    mask_19 = df_test["SiteKey"] == 19
    mask_24 = df_test["SiteKey"] == 24
    mask_peer = (~mask_19) & (~mask_24)
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14.5, 5.8), dpi=300)
    
    # Left: Residual Error Distribution
    sns.histplot(residuals[mask_peer], kde=True, bins=35, color="#1f77b4", alpha=0.45, label="Peer Sites (22 Sites, N=1,128)", ax=ax1)
    sns.histplot(residuals[mask_24], kde=False, bins=15, color="#ff7f0e", alpha=0.75, label="Site 24 (Anomaly, N=52)", ax=ax1)
    sns.histplot(residuals[mask_19], kde=False, bins=15, color="#d62728", alpha=0.75, label="Site 19 (Anomaly, N=52)", ax=ax1)
    
    ax1.axvline(0.0, color="#1e293b", linestyle="--", linewidth=1.5, label="Zero Reference (e = 0)")
    ax1.axvline(-0.3144, color="#000080", linestyle=":", linewidth=1.5, label="Overall Bias (-0.3144)")
    
    # Stat box at upper left (clear of central peak)
    stat_box = (
        "Residual Summary (N = 1,232):\n"
        "  Mean Bias: -0.3144\n"
        "  Std Error:  1.9239\n"
        "  Median:    -0.2745"
    )
    ax1.text(
        0.04, 0.96, stat_box,
        transform=ax1.transAxes, verticalalignment="top", horizontalalignment="left",
        bbox=dict(boxstyle="round,pad=0.5", facecolor="#ffffff", edgecolor="#cbd5e1", alpha=0.95),
        fontsize=8.5, family="monospace"
    )
    
    ax1.set_xlabel("Residual Error: e = Actual - Predicted (kWh/kWp/day)", fontsize=10)
    ax1.set_ylabel("Observation Count", fontsize=10)
    ax1.set_title("Residual Error Distribution (e = Actual - Predicted)", fontsize=11, pad=10)
    ax1.legend(loc="upper right", framealpha=0.95, facecolor="#ffffff", edgecolor="#cbd5e1", fontsize=8.5)
    
    # Right: Residual Error vs. Predicted Specific Yield
    ax2.scatter(y_pred[mask_peer], residuals[mask_peer], color="#1f77b4", alpha=0.40, s=24, edgecolors="none", label="Peer Sites (22 Sites)")
    ax2.scatter(y_pred[mask_24], residuals[mask_24], color="#ff7f0e", marker="^", s=50, alpha=0.9, edgecolors="black", linewidths=0.5, label="Site 24")
    ax2.scatter(y_pred[mask_19], residuals[mask_19], color="#d62728", marker="D", s=60, alpha=0.9, edgecolors="black", linewidths=0.5, label="Site 19")
    
    ax2.axhline(0.0, color="#1e293b", linestyle="--", linewidth=1.5, label="Zero Reference (e = 0)")
    
    # Set Y limits to cleanly include Site 19 while providing empty pocket for lower-left legend
    ax2.set_ylim(-20.0, 9.5)
    ax2.set_xlabel("Predicted Specific Daily Yield (kWh/kWp/day)", fontsize=10)
    ax2.set_ylabel("Residual Error: e = Actual - Predicted (kWh/kWp/day)", fontsize=10)
    ax2.set_title("Residual Error vs. Predicted Specific Yield", fontsize=11, pad=10)
    ax2.legend(loc="lower left", framealpha=0.95, facecolor="#ffffff", edgecolor="#cbd5e1", fontsize=8.5)
    
    fig.suptitle(
        "Full Cohort Primary Model (Tuned ElasticNet) — Residual Diagnostics\n"
        "Residual Definition: e = Actual - Predicted (N = 1,232, Quarantined Test Set)",
        fontsize=12, y=1.02
    )
    fig.tight_layout()
    return fig


def create_full_feature_coefficients(model: Any) -> plt.Figure:
    """Create feature coefficient plot for Full Cohort ElasticNet."""
    feature_names = list(model.feature_names_in_)
    coefficients = model.coef_
    
    df = pd.DataFrame({"Feature": feature_names, "Coefficient": coefficients})
    df["AbsCoef"] = df["Coefficient"].abs()
    df = df.sort_values("AbsCoef", ascending=False).head(15).reset_index(drop=True)
    
    fig, ax = plt.subplots(figsize=(12.0, 7.5), dpi=300)
    fig.subplots_adjust(left=0.28, right=0.92, top=0.88, bottom=0.15)
    y_pos = np.arange(len(df))
    colors = ["#15803d" if c >= 0 else "#b91c1c" for c in df["Coefficient"]]
    
    bars = ax.barh(y_pos, df["Coefficient"], color=colors, alpha=0.85, edgecolor="#1e293b", height=0.62)
    ax.axvline(0.0, color="#1e293b", linestyle="-", linewidth=1.2)
    
    # Symmetric X-axis around zero
    max_abs = max(df["AbsCoef"])
    x_limit = max_abs * 1.30
    ax.set_xlim(-x_limit, x_limit)
    
    ax.set_yticks(y_pos)
    ax.set_yticklabels(df["Feature"], fontsize=9.5)
    ax.invert_yaxis()
    
    # Label bars with signed value
    for bar, val in zip(bars, df["Coefficient"]):
        if val >= 0:
            x_pos = val + 0.02
            ha = "left"
        else:
            x_pos = val - 0.02
            ha = "right"
            
        if abs(val) >= 0.01:
            txt = f"{val:+.3f}"
        elif abs(val) >= 0.0001:
            txt = f"{val:+.4f}"
        else:
            txt = f"{val:+.2e}"
            
        ax.text(x_pos, bar.get_y() + bar.get_height() / 2, txt, va="center", ha=ha, fontsize=8.5, weight="bold", color="#1e293b")
    
    # Prominent disclaimer note
    disclaimer = (
        "Methodological Notice: Standardized coefficients reflect conditional linear associations under pre-test\n"
        "feature standardization and ElasticNet L1/L2 regularization; they do NOT represent isolated physical causal effects."
    )
    ax.text(
        0.5, -0.14, disclaimer,
        transform=ax.transAxes, ha="center", va="top",
        bbox=dict(boxstyle="round,pad=0.5", facecolor="#f8fafc", edgecolor="#cbd5e1", alpha=0.95),
        fontsize=8.5, style="italic", color="#334155"
    )
    
    ax.set_xlabel("ElasticNet Standardized Regression Coefficient (β)", fontsize=10.5)
    ax.set_title(
        "Full Cohort ElasticNet — Top 15 Standardized Regression Coefficients (β)\n"
        "Features Ranked by Absolute Magnitude (|β|); Signs Preserve Direction of Conditional Association",
        fontsize=12, pad=12
    )
    return fig


def create_full_site_wise_performance(df_site: pd.DataFrame) -> plt.Figure:
    """Create site-wise MAE and Bias breakdown across all 24 Full Cohort sites."""
    full_sites = df_site.copy()
    full_sites["SiteKeyStr"] = full_sites["SiteKey"].astype(str)
    
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14.0, 7.5), dpi=300, sharex=True)
    x = np.arange(len(full_sites))
    
    # Bar colors highlighting Site 19 and 24
    colors_mae = []
    for k in full_sites["SiteKey"]:
        if k == 19:
            colors_mae.append("#d62728")
        elif k == 24:
            colors_mae.append("#ff7f0e")
        else:
            colors_mae.append("#1f77b4")
            
    ax1.bar(x, full_sites["full_enet_mae"], color=colors_mae, alpha=0.85, edgecolor="black", width=0.65)
    ax1.axhline(1.1463, color="#000080", linestyle="--", linewidth=1.5, label="Overall Full Test MAE (1.1463)")
    ax1.set_ylabel("MAE (kWh/kWp/day)")
    ax1.set_title("Site-Wise Mean Absolute Error (MAE) Across All 24 Sites")
    
    # Annotate Site 19 and 24
    idx_19 = full_sites.index[full_sites["SiteKey"] == 19].tolist()[0]
    idx_24 = full_sites.index[full_sites["SiteKey"] == 24].tolist()[0]
    ax1.text(idx_19, full_sites.loc[idx_19, "full_enet_mae"] + 0.15, "Site 19 (MAE: 6.32)", ha="center", fontsize=8, weight="bold", color="#b71c1c")
    ax1.text(idx_24, full_sites.loc[idx_24, "full_enet_mae"] + 0.15, "Site 24 (MAE: 1.86)", ha="center", fontsize=8, weight="bold", color="#e65100")
    ax1.legend(loc="upper right")
    
    # Bottom: Bias
    colors_bias = []
    for k, b in zip(full_sites["SiteKey"], full_sites["full_enet_bias"]):
        if k == 19:
            colors_bias.append("#d62728")
        elif k == 24:
            colors_bias.append("#ff7f0e")
        else:
            colors_bias.append("#1f77b4" if b >= 0 else "#90caf9")
            
    ax2.bar(x, full_sites["full_enet_bias"], color=colors_bias, alpha=0.85, edgecolor="black", width=0.65)
    ax2.axhline(0.0, color="#333333", linestyle="-", linewidth=1.0)
    ax2.axhline(-0.3144, color="#000080", linestyle="--", linewidth=1.5, label="Overall Full Test Bias (-0.3144)")
    ax2.set_ylabel("Bias: Actual - Pred (kWh/kWp/day)")
    ax2.set_xlabel("UNISOLAR Site Key")
    ax2.set_title("Site-Wise Tracking Bias (Actual - Predicted)")
    ax2.set_xticks(x)
    ax2.set_xticklabels(full_sites["SiteKeyStr"], rotation=0)
    ax2.legend(loc="lower right")
    
    fig.suptitle("Full Cohort (24 Sites) — Site-Wise Test Performance Benchmark\nProminently Highlighting Metering Anomalies at Sites 19 & 24", fontsize=12, y=1.01)
    fig.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# Cross-Cohort Model Comparison
# ---------------------------------------------------------------------------

def create_cohort_model_comparison(df_eval: pd.DataFrame) -> plt.Figure:
    """Create multi-panel comparison across all 10 evaluation approaches in Phase 5."""
    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(16.5, 6.0), dpi=300)
    
    # Color mapping based on role
    role_colors = {
        "Primary Candidate": "#2ca02c",  # Green
        "Fallback Candidate": "#1f77b4", # Blue
        "Component": "#9467bd",          # Purple
        "Reference": "#7f7f7f",          # Gray
        "Baseline": "#bcbd22",           # Yellow-Green
    }
    
    # Labels with cohort context
    df_eval["DisplayLabel"] = df_eval["cohort"].apply(lambda c: "Peer: " if "Peer" in c else "Full: ") + df_eval["model"]
    y_pos = np.arange(len(df_eval))
    bar_colors = [role_colors.get(r, "#7f7f7f") for r in df_eval["role"]]
    
    # Panel 1: MAE
    bars1 = ax1.barh(y_pos, df_eval["mae"], color=bar_colors, alpha=0.85, edgecolor="black", height=0.65)
    ax1.set_yticks(y_pos)
    ax1.set_yticklabels(df_eval["DisplayLabel"], fontsize=8.5)
    ax1.invert_yaxis()
    ax1.set_xlabel("MAE (kWh/kWp/day) [Lower is Better]")
    ax1.set_title("Test Mean Absolute Error")
    for bar, val in zip(bars1, df_eval["mae"]):
        ax1.text(bar.get_width() + 0.03, bar.get_y() + bar.get_height() / 2, f"{val:.4f}", va="center", fontsize=7.5)
    ax1.set_xlim(0, max(df_eval["mae"]) * 1.18)
    
    # Panel 2: RMSE
    bars2 = ax2.barh(y_pos, df_eval["rmse"], color=bar_colors, alpha=0.85, edgecolor="black", height=0.65)
    ax2.set_yticks(y_pos)
    ax2.set_yticklabels([])
    ax2.invert_yaxis()
    ax2.set_xlabel("RMSE (kWh/kWp/day) [Lower is Better]")
    ax2.set_title("Test Root Mean Squared Error")
    for bar, val in zip(bars2, df_eval["rmse"]):
        ax2.text(bar.get_width() + 0.05, bar.get_y() + bar.get_height() / 2, f"{val:.4f}", va="center", fontsize=7.5)
    ax2.set_xlim(0, max(df_eval["rmse"]) * 1.18)
    
    # Panel 3: R2
    bars3 = ax3.barh(y_pos, df_eval["r2"], color=bar_colors, alpha=0.85, edgecolor="black", height=0.65)
    ax3.set_yticks(y_pos)
    ax3.set_yticklabels([])
    ax3.invert_yaxis()
    ax3.axvline(0.0, color="#333333", linestyle="-", linewidth=0.8)
    ax3.set_xlabel("R² Score [Higher is Better]")
    ax3.set_title("Test Coefficient of Determination (R²)")
    for bar, val in zip(bars3, df_eval["r2"]):
        x_p = bar.get_width() + (0.02 if val >= 0 else -0.08)
        ax3.text(x_p, bar.get_y() + bar.get_height() / 2, f"{val:+.4f}", va="center", fontsize=7.5)
    ax3.set_xlim(min(df_eval["r2"]) - 0.1, max(df_eval["r2"]) + 0.18)
    
    # Custom legend for roles
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor="#2ca02c", edgecolor="black", label="Primary Candidate"),
        Patch(facecolor="#1f77b4", edgecolor="black", label="Fallback Candidate"),
        Patch(facecolor="#9467bd", edgecolor="black", label="Component Model"),
        Patch(facecolor="#7f7f7f", edgecolor="black", label="Reference Baseline"),
        Patch(facecolor="#bcbd22", edgecolor="black", label="Pre-Test Mean Baseline"),
    ]
    fig.legend(handles=legend_elements, loc="lower center", ncol=5, bbox_to_anchor=(0.5, -0.04), fontsize=9)
    
    fig.suptitle("SolarSelect Phase 5 — Multi-Model Test Evaluation Benchmark\nCross-Cohort Performance Across 10 Model Formulations on Quarantined Test Set", fontsize=12, y=1.02)
    fig.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# MLflow Runner and Artifact Logger
# ---------------------------------------------------------------------------

def find_primary_runs(client: MlflowClient, exp_id: str) -> Tuple[str, str]:
    """Find exact primary run IDs for Peer and Full cohort models in Experiment."""
    runs = client.search_runs(exp_id)
    peer_run_id: Optional[str] = None
    full_run_id: Optional[str] = None
    
    for r in runs:
        role = r.data.tags.get("role", "")
        cohort = r.data.tags.get("cohort", "")
        if role == "primary_candidate":
            if cohort == "peer":
                peer_run_id = r.info.run_id
            elif cohort == "full":
                full_run_id = r.info.run_id
                
    if not peer_run_id or not full_run_id:
        raise RuntimeError(f"Could not locate both primary runs in Experiment {exp_id} (found peer: {peer_run_id}, full: {full_run_id})")
        
    return peer_run_id, full_run_id


def log_visualizations(
    project_root: Path,
    tracking_uri: str,
    dry_run: bool = False,
    output_dir: Optional[Path] = None,
    experiment_name: str = EXPERIMENT_NAME,
    cohort: str = "all",
) -> Dict[str, Any]:
    """Generate and log Phase 5 evaluation visualizations to MLflow runs."""
    setup_plotting_style()
    
    print("=" * 70)
    print("SolarSelect — Phase 5 Model Evaluation Visualization Generation")
    print(f"Mode: {'DRY RUN (No MLflow writes)' if dry_run else 'LIVE LOGGING'}")
    print(f"Tracking URI: {tracking_uri}")
    print(f"Target Cohort: {cohort.upper()}")
    print("=" * 70)
    
    # 1. Preflight Model Verification
    print("\n[Step 1/5] Verifying model artifact immutability before execution...")
    verify_model_immutability(project_root)
    print("  ✓ All 8 Phase 5 model binaries match frozen baseline SHA-256 and MD5 hashes.")
    
    # 2. Data and Reports Loading
    print("\n[Step 2/5] Loading test data, reports, and frozen models...")
    df_peer, peer_feats, y_peer_true, y_peer_pred, peer_model = load_peer_cohort_data(project_root)
    df_full, full_feats, y_full_true, y_full_pred, full_model = load_full_cohort_data(project_root)
    df_eval, df_site, df_feat = load_reports(project_root)
    print(f"  ✓ Peer Cohort: N = {len(df_peer)} test observations, {len(peer_feats)} features.")
    print(f"  ✓ Full Cohort: N = {len(df_full)} test observations, {len(full_feats)} features.")
    print(f"  ✓ Evaluation reports loaded ({len(df_eval)} model records, {len(df_site)} site records).")
    
    # 3. Figure Generation
    print("\n[Step 3/5] Rendering publication-grade visualization figures...")
    figures: Dict[str, Dict[str, plt.Figure]] = {"peer": {}, "full": {}}
    
    if cohort in ("all", "peer"):
        figures["peer"] = {
            "visualizations/actual_vs_predicted.png": create_peer_actual_vs_predicted(y_peer_true, y_peer_pred),
            "visualizations/residual_diagnostics.png": create_peer_residual_diagnostics(y_peer_true, y_peer_pred),
            "visualizations/feature_importance.png": create_peer_feature_importance(peer_model, df_feat),
            "visualizations/site_wise_performance.png": create_peer_site_wise_performance(df_site),
            "visualizations/cohort_model_comparison.png": create_cohort_model_comparison(df_eval),
        }
        print(f"  ✓ Rendered {len(figures['peer'])} Peer Cohort figures.")
        
    if cohort in ("all", "full"):
        figures["full"] = {
            "visualizations/actual_vs_predicted.png": create_full_actual_vs_predicted(df_full, y_full_pred),
            "visualizations/residual_diagnostics.png": create_full_residual_diagnostics(df_full, y_full_pred),
            "visualizations/feature_coefficients.png": create_full_feature_coefficients(full_model),
            "visualizations/site_wise_performance.png": create_full_site_wise_performance(df_site),
            "visualizations/cohort_model_comparison.png": create_cohort_model_comparison(df_eval),
        }
        print(f"  ✓ Rendered {len(figures['full'])} Full Cohort figures.")
    
    # Save locally if requested
    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)
        if figures["peer"]:
            peer_dir = output_dir / "peer_cohort"
            peer_dir.mkdir(exist_ok=True)
            for art_path, fig in figures["peer"].items():
                fname = Path(art_path).name
                fig.savefig(peer_dir / fname, dpi=300, bbox_inches="tight")
        if figures["full"]:
            full_dir = output_dir / "full_cohort"
            full_dir.mkdir(exist_ok=True)
            for art_path, fig in figures["full"].items():
                fname = Path(art_path).name
                fig.savefig(full_dir / fname, dpi=300, bbox_inches="tight")
        print(f"  ✓ Saved local image copies to {output_dir}")
        
    # 4. MLflow Logging (if not dry run)
    logged_summary: Dict[str, Any] = {}
    if not dry_run:
        print("\n[Step 4/5] Logging visualization artifacts to MLflow primary runs...")
        mlflow.set_tracking_uri(tracking_uri)
        client = MlflowClient()
        exp = client.get_experiment_by_name(experiment_name)
        if not exp:
            raise RuntimeError(f"Experiment '{experiment_name}' not found!")
            
        peer_run_id, full_run_id = find_primary_runs(client, exp.experiment_id)
        
        # Log Peer Figures if requested
        if cohort in ("all", "peer") and figures["peer"]:
            print(f"  Peer Primary Run ID: {peer_run_id}")
            with mlflow.start_run(run_id=peer_run_id):
                for art_name, fig in figures["peer"].items():
                    mlflow.log_figure(fig, art_name)
                    print(f"    Logged {art_name} -> Run {peer_run_id}")
            logged_summary["peer_run_id"] = peer_run_id
            logged_summary["peer_artifacts"] = list(figures["peer"].keys())
                
        # Log Full Figures if requested
        if cohort in ("all", "full") and figures["full"]:
            print(f"  Full Primary Run ID: {full_run_id}")
            with mlflow.start_run(run_id=full_run_id):
                for art_name, fig in figures["full"].items():
                    mlflow.log_figure(fig, art_name)
                    print(f"    Logged {art_name} -> Run {full_run_id}")
            logged_summary["full_run_id"] = full_run_id
            logged_summary["full_artifacts"] = list(figures["full"].keys())
    else:
        print("\n[Step 4/5] [DRY RUN] Skipping MLflow artifact upload.")
        if figures["peer"]:
            logged_summary["peer_artifacts"] = list(figures["peer"].keys())
        if figures["full"]:
            logged_summary["full_artifacts"] = list(figures["full"].keys())
        
    # Close figures
    for group in figures.values():
        for fig in group.values():
            plt.close(fig)
            
    # 5. Postflight Model Verification
    print("\n[Step 5/5] Verifying model artifact immutability after execution...")
    verify_model_immutability(project_root)
    print("  ✓ Zero model mutation confirmed: all 8 model binaries retain original hashes.")
    
    print("\n" + "=" * 70)
    print("Visualization processing completed successfully.")
    print("=" * 70)
    return logged_summary


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="SolarSelect Phase 5 MLflow Visualization Logger")
    parser.add_argument("--dry-run", action="store_true", help="Perform figure generation without writing to MLflow")
    parser.add_argument("--tracking-uri", default=f"sqlite:///{DEFAULT_TRACKING_DB}", help="MLflow tracking URI")
    parser.add_argument("--output-dir", type=Path, default=None, help="Directory to save generated PNG images locally")
    parser.add_argument("--experiment-name", default=EXPERIMENT_NAME, help="Dedicated MLflow experiment name")
    parser.add_argument(
        "--cohort",
        choices=["all", "full", "peer"],
        default="all",
        help="Target cohort runs to update (default: 'all'; choose 'full' to update only full cohort artifacts)",
    )
    return parser.parse_args()


def main() -> None:
    """CLI entrypoint."""
    args = parse_args()
    project_root = Path(__file__).resolve().parent.parent.parent
    try:
        log_visualizations(
            project_root=project_root,
            tracking_uri=args.tracking_uri,
            dry_run=args.dry_run,
            output_dir=args.output_dir,
            experiment_name=args.experiment_name,
            cohort=args.cohort,
        )
    except Exception as exc:
        print(f"\n[ERROR] Visualization logging failed: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
