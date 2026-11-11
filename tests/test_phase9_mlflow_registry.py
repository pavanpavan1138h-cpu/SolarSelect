"""
Tests for Phase 9 MLflow Experiment Tracking & Model Registry Integration.

Verifies:
- 10 historical Phase 5 evaluation records (5 peer cohort, 5 full cohort).
- Exact metric and parameter fidelity against documented reports.
- DVC lineage tags and hash linkages.
- Model registry registration and aliases (champion, campus-tracking-conditional).
- Idempotency of registration script.
- Preservation of historical Phase 1 runs in Experiment 1.
"""

from pathlib import Path
import sqlite3
import tempfile
import pytest
import mlflow
from mlflow.tracking import MlflowClient
import pandas as pd

from src.mlops.register_phase5_mlflow import (
    EXPERIMENT_NAME,
    build_run_specifications,
    execute_registration,
    load_evaluation_evidence,
    compute_md5,
)


@pytest.fixture(scope="module")
def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def evaluation_evidence(project_root: Path):
    return load_evaluation_evidence(project_root)


@pytest.fixture(scope="module")
def run_specs(evaluation_evidence, project_root: Path):
    return build_run_specifications(evaluation_evidence, project_root)


def test_evidence_and_spec_integrity(run_specs, evaluation_evidence):
    """Verify evidence loading and exact 10 run specifications."""
    assert len(evaluation_evidence["feature_names"]) == 29
    assert len(run_specs) == 10

    peer_specs = [s for s in run_specs if s["cohort"] == "peer"]
    full_specs = [s for s in run_specs if s["cohort"] == "full"]
    assert len(peer_specs) == 5
    assert len(full_specs) == 5

    # Check model registration boundaries: exactly 2 models registered
    reg_specs = [s for s in run_specs if s["register_model"] is not None]
    assert len(reg_specs) == 2

    peer_reg = next(s for s in reg_specs if s["cohort"] == "peer")
    assert peer_reg["register_model"]["registered_name"] == "SolarSelect-Yield-PeerCohort"
    assert peer_reg["register_model"]["alias"] == "champion"

    full_reg = next(s for s in reg_specs if s["cohort"] == "full")
    assert full_reg["register_model"]["registered_name"] == "SolarSelect-Yield-FullCohort"
    assert full_reg["register_model"]["alias"] == "campus-tracking-conditional"
    assert "PROHIBITED" in full_reg["register_model"]["description"].upper()


def test_metric_fidelity(run_specs):
    """Verify exact test evaluation metrics matching Phase 5 reports."""
    # Peer ExtraTrees
    peer_et = next(s for s in run_specs if s["run_name"] == "peer_cohort_tuned-extra-trees_primary")
    assert pytest.approx(peer_et["metrics"]["mae"], abs=1e-3) == 0.9050
    assert pytest.approx(peer_et["metrics"]["rmse"], abs=1e-3) == 1.0700
    assert pytest.approx(peer_et["metrics"]["r2"], abs=1e-3) == 0.2580
    assert pytest.approx(peer_et["metrics"]["bias"], abs=1e-3) == -0.1036
    assert peer_et["tags"]["source"] == "historical_evaluation"
    assert peer_et["tags"]["acceptance_verdict"] == "ACCEPTED"
    assert peer_et["tags"]["dvc_model_md5"] == "420ea113a69405396faab910e25a04a5"

    # Full ElasticNet
    full_en = next(s for s in run_specs if s["run_name"] == "full_cohort_tuned-elastic-net_primary")
    assert pytest.approx(full_en["metrics"]["mae"], abs=1e-3) == 1.1463
    assert pytest.approx(full_en["metrics"]["rmse"], abs=1e-3) == 1.9494
    assert pytest.approx(full_en["metrics"]["r2"], abs=1e-3) == 0.7407
    assert pytest.approx(full_en["metrics"]["bias"], abs=1e-3) == -0.3144
    assert full_en["tags"]["source"] == "historical_evaluation"
    assert "CONDITIONALLY ACCEPTED" in full_en["tags"]["acceptance_verdict"]
    assert full_en["tags"]["dvc_model_md5"] == "2ea38e4cca315095f76e07d63c4c2064"


def test_isolated_execution_and_registry(run_specs, evaluation_evidence, project_root: Path):
    """Test full execution, model logging, registry and aliasing on isolated temporary DB."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_mlflow.db"
        tracking_uri = f"sqlite:///{db_path.as_posix()}"
        client = MlflowClient(tracking_uri)

        # 1. First execution
        result = execute_registration(run_specs, evaluation_evidence, tracking_uri, project_root)
        assert len(result["logged_runs"]) == 10
        assert len(result["registered_models"]) == 2

        # 2. Check registered models & aliases
        peer_mv = client.get_model_version_by_alias("SolarSelect-Yield-PeerCohort", "champion")
        assert str(peer_mv.version) == "1"

        full_mv = client.get_model_version_by_alias("SolarSelect-Yield-FullCohort", "campus-tracking-conditional")
        assert str(full_mv.version) == "1"

        # 3. Load models via registry and verify prediction
        X_sample = evaluation_evidence["input_example"]
        peer_model = mlflow.sklearn.load_model("models:/SolarSelect-Yield-PeerCohort@champion")
        peer_preds = peer_model.predict(X_sample)
        assert len(peer_preds) == 2
        assert all(p > 0 for p in peer_preds)

        full_model = mlflow.sklearn.load_model("models:/SolarSelect-Yield-FullCohort@campus-tracking-conditional")
        full_preds = full_model.predict(X_sample)
        assert len(full_preds) == 2
        assert all(p > 0 for p in full_preds)

        # 4. Test idempotency on subsequent execution
        result_2 = execute_registration(run_specs, evaluation_evidence, tracking_uri, project_root)
        assert len(result_2["logged_runs"]) == 0
        assert len(result_2["registered_models"]) == 0

        # Total runs should still be exactly 10
        runs = client.search_runs(experiment_ids=[result["experiment_id"]])
        assert len(runs) == 10


def test_historical_runs_preservation(project_root: Path):
    """Verify that existing historical runs in mlflow.db remain intact and unmutated."""
    db_file = project_root / "mlflow.db"
    assert db_file.exists()

    conn = sqlite3.connect(f"file:{db_file.as_posix()}?mode=ro", uri=True)
    cur = conn.cursor()

    # Verify Experiment 1 exists
    cur.execute("SELECT experiment_id, name, lifecycle_stage FROM experiments WHERE experiment_id = 1;")
    exp1 = cur.fetchone()
    assert exp1 is not None
    assert exp1[1] == "SolarSelect-Forecasting"
    assert exp1[2] == "active"

    # Verify all 8 historical runs exist
    cur.execute("SELECT count(*) FROM runs WHERE experiment_id = 1 AND status = 'FINISHED';")
    count = cur.fetchone()[0]
    assert count == 8

    conn.close()


def test_logged_visualization_artifacts(project_root: Path):
    """Verify that academic evaluation visualizations are attached to existing primary runs in mlflow.db."""
    db_file = project_root / "mlflow.db"
    assert db_file.exists()

    client = MlflowClient(f"sqlite:///{db_file.as_posix()}")
    exp = client.get_experiment_by_name(EXPERIMENT_NAME)
    assert exp is not None

    runs = client.search_runs(exp.experiment_id)
    assert len(runs) == 10

    peer_run = next(r for r in runs if r.data.tags.get("role") == "primary_candidate" and r.data.tags.get("cohort") == "peer")
    full_run = next(r for r in runs if r.data.tags.get("role") == "primary_candidate" and r.data.tags.get("cohort") == "full")

    # Expected artifacts for peer primary run
    peer_artifacts = {a.path for a in client.list_artifacts(peer_run.info.run_id, "visualizations")}
    expected_peer = {
        "visualizations/actual_vs_predicted.png",
        "visualizations/residual_diagnostics.png",
        "visualizations/feature_importance.png",
        "visualizations/site_wise_performance.png",
        "visualizations/cohort_model_comparison.png",
    }
    assert expected_peer.issubset(peer_artifacts)

    # Expected artifacts for full primary run
    full_artifacts = {a.path for a in client.list_artifacts(full_run.info.run_id, "visualizations")}
    expected_full = {
        "visualizations/actual_vs_predicted.png",
        "visualizations/residual_diagnostics.png",
        "visualizations/feature_coefficients.png",
        "visualizations/site_wise_performance.png",
        "visualizations/cohort_model_comparison.png",
    }
    assert expected_full.issubset(full_artifacts)


def test_model_artifact_immutability(project_root: Path):
    """Verify that all 8 Phase 5 model artifacts match authoritative frozen baseline hashes."""
    from src.mlops.log_phase5_visualizations import verify_model_immutability
    verify_model_immutability(project_root)


