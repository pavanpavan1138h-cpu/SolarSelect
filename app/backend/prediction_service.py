"""HTTP prediction adapter; all model arithmetic remains in the existing predictor."""
import numpy as np
import pandas as pd
from app.backend.core.errors import APIError

class PredictionService:
    def __init__(self, provider, limitations):
        self.provider, self.limitations = provider, limitations

    def predict(self, rows, request_id):
        # Validate every row first (all-or-nothing), then run ONE model call per variant instead of one per row.
        frames = [self.provider.validate_features(row.features.model_dump()) for row in rows]
        by_variant = {}
        for i, row in enumerate(rows):
            by_variant.setdefault(row.model_variant, []).append(i)
        results = [None] * len(rows)
        for variant, idx in by_variant.items():
            batch = pd.concat([frames[i] for i in idx], ignore_index=True)
            raw = np.asarray(self.provider.predict(batch, variant), dtype=float)
            if raw.shape != (len(idx),) or not np.isfinite(raw).all():
                raise APIError(503, "INVALID_MODEL_OUTPUT", "Model did not produce one finite specific-yield prediction per row.")
            provenance = self.provider.get_provenance(variant)
            for i, value in zip(idx, raw.tolist()):
                results[i] = dict(predicted_specific_yield_kwh_per_kwp_day=value,
                                  prediction_status="NEGATIVE_PREDICTION_WARNING" if value < 0 else "PREDICTION_AVAILABLE",
                                  model=provenance, request_id=request_id, limitations=self.limitations)
        return results  # request order preserved
