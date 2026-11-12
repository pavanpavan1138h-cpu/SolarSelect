"""Build monitoring/configs/feature_baseline.json from the TRAINING split (quantile summaries only)."""
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from monitoring.drift import build_baseline

names = json.loads((ROOT / "models/phase5/final_model_metadata.json").read_text())["feature_space"]["predictive_feature_names"]
base = build_baseline(ROOT / "data/processed/unisolar/peer_cohort/train.csv", names, ROOT / "monitoring/configs/feature_baseline.json")
print(f"baseline rows={base['rows']} features={len(base['features'])}")
