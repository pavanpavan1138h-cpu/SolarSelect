"""Post-deploy smoke test (stdlib only): python scripts/verify_deployed_endpoint.py http://host:8000
Exit 0 only if health, model identity, a known prediction and the governance guard all behave."""
import json
import math
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_ET_FINGERPRINT = "39b4a11beb5423dff"[:16]

def call(base, path, body=None):
    req = urllib.request.Request(base + path, data=None if body is None else json.dumps(body).encode(),
                                 headers={"content-type": "application/json"}, method="GET" if body is None else "POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")

def main(base, wait=120):
    base = base.rstrip("/")
    deadline, checks = time.time() + wait, []
    while True:                                     # wait for readiness (model load takes seconds)
        try:
            if call(base, "/api/v1/health/ready")[0] == 200:
                break
        except OSError:
            pass
        if time.time() > deadline:
            print("FAIL: service not ready within", wait, "s"); return 1
        time.sleep(3)
    def check(name, ok):
        checks.append(ok); print(("PASS " if ok else "FAIL ") + name)
    check("liveness", call(base, "/api/v1/health/live")[1].get("status") == "LIVE")
    s, info = call(base, "/api/v1/model/info")
    check("model info: 29 features, kWh/kWp/day", s == 200 and info.get("feature_count") == 29 and info.get("units") == "kWh/kWp/day")
    check("model fingerprint matches frozen ExtraTrees", info.get("primary_artifact_fingerprint") == EXPECTED_ET_FINGERPRINT)
    req = json.loads((ROOT / "docs/backend/examples/historical_request.json").read_text())
    ref = json.loads((ROOT / "docs/backend/examples/historical_response.json").read_text())
    s, out = call(base, "/api/v1/predict", req)
    v = out.get("predicted_specific_yield_kwh_per_kwp_day")
    check("prediction finite and equal to documented reference (1e-8)", s == 200 and v is not None and math.isfinite(v)
          and abs(v - ref["predicted_specific_yield_kwh_per_kwp_day"]) <= 1e-8)
    s, out = call(base, "/api/v1/predict", {"scenario": "prospective_roof", "roof_id": "SMOKE"})
    check("lag-policy guard returns 409", s == 409 and out["error"]["code"] == "PREDICTION_PENDING_LAG_POLICY")
    check("invalid input rejected with 422", call(base, "/api/v1/predict", {"scenario": "historical_site_day", "features": {}})[0] == 422)
    check("panel catalogue available", call(base, "/api/v1/panels")[0] == 200)
    try:
        urllib.request.urlopen(base + "/metrics", timeout=10); check("metrics endpoint", True)
    except Exception:
        check("metrics endpoint", False)
    print(f"{sum(checks)}/{len(checks)} checks passed")
    return 0 if all(checks) else 1

if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"))
