import numpy as np
import pandas as pd
import pytest
from src.energy_economics.inference import Phase5PeerCohortPredictor
from src.energy_economics.types import ModelVariant
from app.backend.core.config import REPOSITORY_ROOT
from app.backend.contracts import HistoricalRequest
from app.backend.prediction_service import PredictionService

@pytest.mark.parametrize("variant", list(ModelVariant))
def test_real_frozen_parity(real_client, real_provider, historical_rows, variant):
    direct = Phase5PeerCohortPredictor(
        variant,
        primary_model_path=REPOSITORY_ROOT / Phase5PeerCohortPredictor.DEFAULT_ET_PATH,
        fallback_linear_path=REPOSITORY_ROOT / Phase5PeerCohortPredictor.DEFAULT_EN_PATH,
        metadata_path=REPOSITORY_ROOT / Phase5PeerCohortPredictor.DEFAULT_METADATA_PATH)
    expected = direct.predict(pd.DataFrame(historical_rows))
    service_results = PredictionService(real_provider, []).predict([
        HistoricalRequest(scenario="historical_site_day", features=row, model_variant=variant)
        for row in historical_rows
    ], "service-parity-test")
    through_service = [r["predicted_specific_yield_kwh_per_kwp_day"] for r in service_results]
    assert np.allclose(through_service, expected, rtol=0, atol=1e-8)
    actual = []
    for row in historical_rows:
        result = real_client.post("/api/v1/predict", json={
            "scenario": "historical_site_day", "model_variant": variant.value,
            "features": dict(reversed(list(row.items())))})
        assert result.status_code == 200, result.text
        actual.append(result.json()["predicted_specific_yield_kwh_per_kwp_day"])
        assert result.json()["model"]["model_variant"] == variant.value
    assert np.allclose(actual, expected, rtol=0, atol=1e-8)
    assert np.allclose(actual, through_service, rtol=0, atol=1e-8)
    if variant == ModelVariant.FALLBACK_BLEND_50_50:
        x = direct.validate_features(historical_rows)
        blend = 0.5 * direct.primary_model.predict(x) + 0.5 * direct.linear_model.predict(x)
        assert np.allclose(actual, blend, rtol=0, atol=1e-8)
