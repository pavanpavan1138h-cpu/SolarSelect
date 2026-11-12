"""Generate drift + latency evidence into reports/phase9/monitoring/ (read-only on models and data)."""
import json
import sys
import time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import numpy as np
import pandas as pd
from fastapi.testclient import TestClient
from app.backend.core.config import Settings
from app.backend.main import create_app
from monitoring import drift
from monitoring.metrics import REGISTRY

OUT = ROOT / "reports/phase9/monitoring"
OUT.mkdir(parents=True, exist_ok=True)
names = json.loads((ROOT / "models/phase5/final_model_metadata.json").read_text())["feature_space"]["predictive_feature_names"]
base = json.loads((ROOT / "monitoring/configs/feature_baseline.json").read_text())
peer = ROOT / "data/processed/unisolar/peer_cohort"
res = {}
for split in ("train", "validation", "test"):
    df = pd.read_csv(peer / f"{split}.csv")
    cur = df.sample(min(len(df), 1000), random_state=0) if split == "train" else df
    rep = drift.feature_drift_report(base, cur)
    res[split] = {"rows": rep["current_rows"], "status": rep["status"], "max_psi": rep.get("max_psi"),
                  "top": sorted(((k, round(v["psi"], 3), round(v["out_of_training_range_fraction"], 3)) for k, v in rep["features"].items() if v["psi"] is not None), key=lambda t: -t[1])[:8],
                  "n_alert": sum(v["level"] == "ALERT" for v in rep["features"].values()),
                  "n_warn": sum(v["level"] == "WARN" for v in rep["features"].values())}
(OUT / "drift_results.json").write_text(json.dumps(res, indent=1))

ints = ("day_of_year", "month", "day_of_week", "is_weekend", "has_valid_lag1")
test = pd.read_csv(peer / "test.csv")
bodies = [{"scenario": "historical_site_day", "features": {k: (int(v) if k in ints else float(v)) for k, v in test.loc[i, names].items()}} for i in range(200)]
REGISTRY.reset()
with TestClient(create_app(Settings())) as c:
    for b in bodies:
        assert c.post("/api/v1/predict", json=b).status_code == 200
    batch = {"rows": bodies[:100]}
    for _ in range(10):
        assert c.post("/api/v1/predict/batch", json=batch).status_code == 200
    lat = {"predict_p50_ms": REGISTRY.percentile("solarselect_http_request_duration_ms", .5, route="/api/v1/predict"),
           "predict_p95_ms": REGISTRY.percentile("solarselect_http_request_duration_ms", .95, route="/api/v1/predict"),
           "predict_p99_ms": REGISTRY.percentile("solarselect_http_request_duration_ms", .99, route="/api/v1/predict"),
           "batch100_p50_ms": REGISTRY.percentile("solarselect_http_request_duration_ms", .5, route="/api/v1/predict/batch"),
           "batch100_p95_ms": REGISTRY.percentile("solarselect_http_request_duration_ms", .95, route="/api/v1/predict/batch"),
           "inference_p95_ms": REGISTRY.percentile("solarselect_inference_latency_ms", .95, variant="primary_extra_trees"),
           "requests": REGISTRY.counter_sum("solarselect_http_requests_total")}
    (OUT / "metrics_sample.prom").write_text(c.get("/metrics").text)
(OUT / "latency_results.json").write_text(json.dumps(lat, indent=1))
print(json.dumps(res, indent=1)); print(json.dumps(lat, indent=1))
