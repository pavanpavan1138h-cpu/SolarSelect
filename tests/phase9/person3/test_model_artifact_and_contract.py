"""Artifact identity, 29-feature contract and target-leakage QA."""
import hashlib
import json
import pandas as pd
import pytest
from app.backend.contracts import HistoricalFeatures
from app.backend.model_loaders import digest
from src.energy_economics.exceptions import FeatureValidationError
from src.energy_economics.inference import Phase5PeerCohortPredictor
from tests.phase9.person3.conftest import ET_PATH, REPORTED_ET_SHA256, TARGET

def test_extra_trees_hash_matches_handoff_and_manifest():
    assert digest(ET_PATH) == REPORTED_ET_SHA256
    manifest = json.loads((ET_PATH.parents[3].parent / "app/backend/model_loaders/frozen_manifest.json").read_text())
    assert manifest["models/phase5/final/peer_cohort/final_extra_trees.joblib"] == REPORTED_ET_SHA256

def test_exactly_29_features_and_no_duplicates(feature_names):
    assert len(feature_names) == 29 == len(set(feature_names))

def test_estimator_order_matches_metadata_and_http_schema(primary, feature_names):
    assert primary.feature_names == feature_names
    assert list(HistoricalFeatures.model_fields) == feature_names

def test_no_target_or_leakage_names_among_predictors(feature_names):
    banned = {c.lower() for c in Phase5PeerCohortPredictor.EXCLUDED_TARGET_COLUMNS} | {"target_daily_yield"}
    assert not banned & {f.lower() for f in feature_names}
    assert not any(f.lower().startswith(("target", "actual")) for f in feature_names)

def test_dataset_has_target_but_features_are_separate(heldout, feature_names):
    assert TARGET in heldout.columns and TARGET not in feature_names
    assert set(feature_names) <= set(heldout.columns)

@pytest.mark.parametrize("leak", ["target_daily_yield", "target", "y", "SolarGeneration", "actual_target_daily_yield"])
def test_leakage_columns_never_influence_predictor_output(primary, heldout, feature_names, leak):
    """Finding F-3: the library strips (not rejects) target columns, despite its docstring. The
    guarantee QA can enforce is that a leaked value cannot change the prediction; the HTTP layer
    additionally rejects such fields (extra=forbid, see test_input_robustness)."""
    import numpy as np
    clean = heldout[feature_names].iloc[:5].copy()
    leaked = clean.copy()
    leaked[leak] = 1e6
    assert list(primary.validate_features(leaked).columns) == feature_names
    np.testing.assert_allclose(primary.predict(leaked), primary.predict(clean), rtol=0, atol=1e-12)

def test_predictor_rejects_missing_feature(primary, heldout, feature_names):
    with pytest.raises(FeatureValidationError):
        primary.validate_features(heldout[feature_names].iloc[:2].drop(columns=["kWp"]))

def test_heldout_split_provenance(heldout, metadata):
    assert len(heldout) == metadata["chronological_partitions"]["test_held_out"]["peer_cohort_samples"] == 1128
    assert set(heldout["split"]) == {"test"}
    assert heldout["Date"].min() >= "2022-03-01" and heldout["Date"].max() <= "2022-04-23"
    assert not heldout[feature_names_present(heldout)].isna().any().any()

def feature_names_present(df):
    return [c for c in df.columns if c not in ("SiteKey", "Date", "split")]

def test_no_train_test_row_overlap(heldout):
    from app.backend.core.config import REPOSITORY_ROOT
    train = pd.read_csv(REPOSITORY_ROOT / "data/processed/unisolar/peer_cohort/train.csv", usecols=["SiteKey", "Date"])
    val = pd.read_csv(REPOSITORY_ROOT / "data/processed/unisolar/peer_cohort/validation.csv", usecols=["SiteKey", "Date"])
    key = lambda d: set(zip(d.SiteKey, d.Date))
    assert not key(heldout) & (key(train) | key(val))
