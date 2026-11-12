"""HTTP prediction adapter; all model arithmetic remains in the existing predictor."""
import math
import numpy as np
from app.backend.core.errors import APIError

class PredictionService:
    def __init__(self, provider, limitations):
        self.provider, self.limitations = provider, limitations

    def predict(self, rows, request_id):
        results = []
        # Preserve request order; each row selects its variant explicitly.
        for row in rows:
            x = self.provider.validate_features(row.features.model_dump())
            raw = np.asarray(self.provider.predict(x, row.model_variant), dtype=float)
            if raw.shape != (1,) or not math.isfinite(float(raw[0])):
                raise APIError(503, "INVALID_MODEL_OUTPUT", "Model did not produce one finite specific-yield prediction.")
            value = float(raw[0])
            results.append(dict(predicted_specific_yield_kwh_per_kwp_day=value,
                                prediction_status="NEGATIVE_PREDICTION_WARNING" if value < 0 else "PREDICTION_AVAILABLE",
                                model=self.provider.get_provenance(row.model_variant),
                                request_id=request_id, limitations=self.limitations))
        return results
