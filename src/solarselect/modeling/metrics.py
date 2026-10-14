"""Evaluation metrics for 15-minute-ahead plant AC power forecasts."""
from __future__ import annotations

import numpy as np


def safe_mape(y_true, y_pred, min_actual: float) -> float:
    """MAPE (%) computed only where |actual| >= min_actual.

    Solar output is ~0 at night, so plain MAPE divides by zero. Returns NaN
    if no point meets the threshold.
    """
    y_true, y_pred = np.asarray(y_true, float), np.asarray(y_pred, float)
    m = np.abs(y_true) >= min_actual
    if not m.any():
        return float("nan")
    return float(np.mean(np.abs((y_true[m] - y_pred[m]) / y_true[m])) * 100)


def regression_metrics(y_true, y_pred, daytime_mask=None, min_actual: float = 1000.0) -> dict:
    """MAE, RMSE, R2, safe MAPE, bias (all data), plus daytime-only MAE/RMSE/bias.

    bias = mean(pred - actual); positive means over-forecasting.
    """
    y_true, y_pred = np.asarray(y_true, float), np.asarray(y_pred, float)
    err = y_pred - y_true
    ss_tot = float(np.sum((y_true - y_true.mean()) ** 2))
    out = {
        "mae": float(np.mean(np.abs(err))),
        "rmse": float(np.sqrt(np.mean(err**2))),
        "r2": float(1 - np.sum(err**2) / ss_tot) if ss_tot > 0 else float("nan"),
        "safe_mape": safe_mape(y_true, y_pred, min_actual),
        "bias": float(err.mean()),
        "n": int(len(y_true)),
    }
    if daytime_mask is not None:
        d = np.asarray(daytime_mask, bool)
        if d.any():
            out["day_mae"] = float(np.mean(np.abs(err[d])))
            out["day_rmse"] = float(np.sqrt(np.mean(err[d] ** 2)))
            out["day_bias"] = float(err[d].mean())
            out["day_n"] = int(d.sum())
    return out
