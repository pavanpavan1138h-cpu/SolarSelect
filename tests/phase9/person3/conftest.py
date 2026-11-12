"""Person 3 QA fixtures: authoritative contract comes from metadata and the frozen estimator."""
import json
import numpy as np
import pandas as pd
import pytest
from app.backend.core.config import REPOSITORY_ROOT
from src.energy_economics.inference import Phase5PeerCohortPredictor
from src.energy_economics.types import ModelVariant

METADATA_PATH = REPOSITORY_ROOT / "models/phase5/final_model_metadata.json"
TEST_CSV = REPOSITORY_ROOT / "data/processed/unisolar/peer_cohort/test.csv"
ET_PATH = REPOSITORY_ROOT / "models/phase5/final/peer_cohort/final_extra_trees.joblib"
REPORTED_ET_SHA256 = "39b4a11beb5423dff926e43b4594b7938957183daaa16f16bdea7e5dc54ecfe9"
TARGET = "target_daily_yield"

@pytest.fixture(scope="session")
def metadata():
    return json.loads(METADATA_PATH.read_text())

@pytest.fixture(scope="session")
def feature_names(metadata):
    return metadata["feature_space"]["predictive_feature_names"]

@pytest.fixture(scope="session")
def heldout():
    return pd.read_csv(TEST_CSV)

@pytest.fixture(scope="session")
def primary():
    return Phase5PeerCohortPredictor(ModelVariant.PRIMARY_EXTRA_TREES)

@pytest.fixture(scope="session")
def fallback():
    return Phase5PeerCohortPredictor(ModelVariant.FALLBACK_BLEND_50_50)

@pytest.fixture(scope="session")
def primary_predictions(primary, heldout, feature_names):
    return np.asarray(primary.predict(heldout[feature_names]), dtype=float)

@pytest.fixture
def valid_row(heldout, feature_names):
    return {k: (int(v) if float(v).is_integer() and k in
                ("day_of_year", "month", "day_of_week", "is_weekend", "has_valid_lag1") else float(v))
            for k, v in heldout.loc[0, feature_names].items()}
