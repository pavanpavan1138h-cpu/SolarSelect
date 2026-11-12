import json
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from app.backend.core.config import Settings, REPOSITORY_ROOT
from app.backend.main import create_app
from monitoring.metrics import REGISTRY, Registry
from tests.conftest import StubProvider

@pytest.fixture(autouse=True)
def clean_registry():
    REGISTRY.reset()
    yield

@pytest.fixture
def baseline():
    return json.loads((REPOSITORY_ROOT / "monitoring/configs/feature_baseline.json").read_text())

@pytest.fixture(scope="session")
def peer():
    base = REPOSITORY_ROOT / "data/processed/unisolar/peer_cohort"
    return {s: pd.read_csv(base / f"{s}.csv") for s in ("train", "validation", "test")}

@pytest.fixture
def mon_client(api_settings):
    with TestClient(create_app(api_settings, provider_factory=lambda _: StubProvider())) as c:
        yield c

@pytest.fixture
def valid_body(historical_body):
    return historical_body

@pytest.fixture(scope="session")
def metadata():
    return json.loads((REPOSITORY_ROOT / "models/phase5/final_model_metadata.json").read_text())
