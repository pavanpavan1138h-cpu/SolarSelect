"""Feature and prediction drift. Feature drift is NOT concept drift: performance needs outcome labels (see performance.py)."""
import json
import threading
from collections import deque
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats

MIN_SAMPLES = 100                  # below this, PSI/KS are reported as INSUFFICIENT_DATA rather than guessed
PSI_BINS = 10

def psi(reference, current, bins=PSI_BINS):
    """Population Stability Index with reference-quantile bins; returns None if either sample is too small/degenerate."""
    ref, cur = np.asarray(reference, float), np.asarray(current, float)
    ref, cur = ref[np.isfinite(ref)], cur[np.isfinite(cur)]
    if len(ref) < MIN_SAMPLES or len(cur) < MIN_SAMPLES:
        return None
    edges = np.unique(np.quantile(ref, np.linspace(0, 1, bins + 1)))
    if len(edges) < 3:
        return None                # (near-)constant feature: PSI undefined
    edges[0], edges[-1] = -np.inf, np.inf
    eps = 1e-4
    p = np.maximum(np.histogram(ref, edges)[0] / len(ref), eps)
    q = np.maximum(np.histogram(cur, edges)[0] / len(cur), eps)
    return float(np.sum((q - p) * np.log(q / p)))

def ks(reference, current):
    ref, cur = np.asarray(reference, float), np.asarray(current, float)
    ref, cur = ref[np.isfinite(ref)], cur[np.isfinite(cur)]
    if len(ref) < MIN_SAMPLES or len(cur) < MIN_SAMPLES:
        return None
    r = stats.ks_2samp(ref, cur)
    return {"statistic": float(r.statistic), "p_value": float(r.pvalue)}

def build_baseline(train_csv, feature_names, path=None):
    """Reference summary of the TRAINING distribution (quantile grid + range) - no raw rows stored."""
    df = pd.read_csv(train_csv)
    q = np.linspace(0, 1, 101)
    base = {"source": str(Path(train_csv).name), "rows": int(len(df)), "features": {
        f: {"min": float(df[f].min()), "max": float(df[f].max()), "mean": float(df[f].mean()),
            "std": float(df[f].std()), "quantiles": [float(v) for v in np.quantile(df[f], q)]} for f in feature_names}}
    if path:
        Path(path).write_text(json.dumps(base, indent=1))
    return base

def sample_from_quantiles(quantiles):
    """Reference sample reconstructed from the stored quantile grid (101 pts, uniformly weighted)."""
    return np.asarray(quantiles, float)

class FeatureWindow:
    """Bounded rolling window of validated inference rows (aggregate monitoring only)."""
    def __init__(self, size=2000):
        self._rows, self._lock = deque(maxlen=size), threading.Lock()

    def add(self, frame):
        with self._lock:
            self._rows.extend(frame.to_dict("records"))

    def frame(self):
        with self._lock:
            return pd.DataFrame(list(self._rows))

def feature_drift_report(baseline, current_frame, psi_warn=0.1, psi_alert=0.25):
    """PSI/KS per feature vs training reference. 0.10/0.25 are the conventional PSI bands, kept configurable."""
    out = {"current_rows": int(len(current_frame)), "features": {}, "status": "OK"}
    if len(current_frame) < MIN_SAMPLES:
        out["status"] = "INSUFFICIENT_DATA"
        return out
    worst = 0.0
    for name, ref in baseline["features"].items():
        if name not in current_frame:
            continue
        cur = current_frame[name].to_numpy()
        ref_sample = np.repeat(sample_from_quantiles(ref["quantiles"]), 10)    # 1010 pts
        p, k = psi(ref_sample, cur), ks(ref_sample, cur)
        oor = float(((cur < ref["min"]) | (cur > ref["max"])).mean())
        level = "INSUFFICIENT_DATA" if p is None else "ALERT" if p >= psi_alert else "WARN" if p >= psi_warn else "OK"
        out["features"][name] = {"psi": p, "ks": k, "out_of_training_range_fraction": oor, "level": level}
        worst = max(worst, p or 0.0)
    out["max_psi"] = worst
    levels = {v["level"] for v in out["features"].values()}
    out["status"] = "ALERT" if "ALERT" in levels else "WARN" if "WARN" in levels else "OK"
    return out

def prediction_drift(reference_predictions, current_predictions, psi_warn=0.1, psi_alert=0.25):
    p = psi(reference_predictions, current_predictions)
    level = "INSUFFICIENT_DATA" if p is None else "ALERT" if p >= psi_alert else "WARN" if p >= psi_warn else "OK"
    return {"psi": p, "ks": ks(reference_predictions, current_predictions), "level": level}
