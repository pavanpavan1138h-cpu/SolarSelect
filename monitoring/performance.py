"""Outcome-based (concept-drift / performance) monitoring. Only meaningful once actual yields arrive."""
import numpy as np

def evaluate(predictions, actuals, reference):
    """reference: dict with mae, rmse, bias (Person 1 test_metrics). Returns None if there are no labels yet."""
    y, p = np.asarray(actuals, float), np.asarray(predictions, float)
    if len(y) == 0:
        return {"status": "NO_LABELS", "n": 0}
    e = p - y
    mae, rmse = float(np.abs(e).mean()), float(np.sqrt((e ** 2).mean()))
    return {"status": "OK", "n": int(len(y)), "mae": mae, "rmse": rmse, "bias_pred_minus_actual": float(e.mean()),
            "mae_ratio_to_reference": mae / reference["mae"], "rmse_ratio_to_reference": rmse / reference["rmse"]}
