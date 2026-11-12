"""Fixtures for Person 2 API tests; existing Phase 7/8/9 fixtures are untouched."""
import json
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from app.backend.core.config import REPOSITORY_ROOT, Settings
from app.backend.contracts import HistoricalFeatures
from app.backend.main import create_app
from app.backend.model_loaders import LocalFrozenModelProvider

class StubProvider:
    feature_names = list(HistoricalFeatures.model_fields)
    def __init__(self, value=-0.5):
        self.value = value
    def is_ready(self):
        return True
    def validate_features(self, rows):
        return pd.DataFrame([rows]) if isinstance(rows, dict) else rows
    def predict(self, rows, variant):
        return np.array([self.value])
    def get_provenance(self, variant):
        return {"source": "test_stub", "model_variant": variant.value, "cohort": "peer_cohort"}

@pytest.fixture(scope="session")
def api_settings():
    return Settings(root=REPOSITORY_ROOT, model_source="local")

@pytest.fixture(scope="session")
def real_provider(api_settings):
    return LocalFrozenModelProvider(api_settings)

@pytest.fixture(scope="session")
def historical_rows():
    metadata = json.loads((REPOSITORY_ROOT / "models/phase5/final_model_metadata.json").read_text())
    names = metadata["feature_space"]["predictive_feature_names"]
    return pd.read_csv(REPOSITORY_ROOT / "data/processed/unisolar/peer_cohort/test.csv", nrows=8)[names].to_dict("records")

@pytest.fixture
def historical_body(historical_rows):
    return {"scenario": "historical_site_day", "features": historical_rows[0].copy()}

@pytest.fixture
def api_client(api_settings):
    with TestClient(create_app(api_settings, provider_factory=lambda _: StubProvider())) as client:
        yield client

@pytest.fixture(scope="session")
def real_client(api_settings, real_provider):
    with TestClient(create_app(api_settings, provider_factory=lambda _: real_provider)) as client:
        yield client

@pytest.fixture
def roof_body():
    return {"roof_id": "API-HISTORICAL-GEOMETRY", "length": 20.0, "width": 15.0,
            "perimeter_setback": 0.5, "panel_id": "PNL-TRINA-330W",
            "inter_panel_clearance": 0.02, "inter_row_clearance": 0.5,
            "obstacles": [{"obstacle_id": "VENT", "x": 4.0, "y": 5.0, "width": 0.4, "height": 0.5, "buffer": 0.2}]}
