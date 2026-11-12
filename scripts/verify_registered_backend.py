"""Fresh loopback HTTP checks for the approved champion and frozen fallback.

Starts/stops only its own processes; never updates OpenAPI, models or registry.
"""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time

import httpx
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.backend.core.config import Settings
from app.backend.contracts import HistoricalRequest, RoofRequest
from app.backend.model_loaders import LocalFrozenModelProvider, MLflowRegistryProvider
from app.backend.prediction_service import PredictionService
from app.backend.roof_service import RoofService
from src.energy_economics.inference import Phase5PeerCohortPredictor
from src.energy_economics.types import ModelVariant


@contextmanager
def server(mode, report_dir, handoff):
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    env = os.environ.copy()
    env.update(MODEL_SOURCE="local" if mode == "local" else "mlflow",
               SOLARSELECT_ROOT=str(ROOT),
               MLFLOW_TRACKING_URI="sqlite:///" + (ROOT / handoff["database_relative_path"]).resolve().as_posix(),
               MLFLOW_MODEL_URI="models:/SolarSelect-Yield-PeerCohort@champion",
               REGISTRY_HANDOFF_FILE=str(ROOT / ("configs/registry_peer_champion.json" if mode != "unavailable" else ".person2-local/absent-handoff.json")))
    base = f"http://127.0.0.1:{port}"
    with (report_dir / f"server_{mode}.log").open("w", encoding="utf-8") as log:
        process = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.backend.main:app",
                                    "--host", "127.0.0.1", "--port", str(port)],
                                   cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT,
                                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        try:
            deadline = time.monotonic() + 55
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    raise RuntimeError(f"{mode} server exited; inspect its log")
                try:
                    if httpx.get(base + "/api/v1/health/live", timeout=1).status_code == 200:
                        break
                except httpx.TransportError:
                    pass
                time.sleep(0.2)
            else:
                raise RuntimeError(f"{mode} startup timed out")
            with httpx.Client(base_url=base, timeout=60) as client:
                yield client
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=10)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report-dir", type=Path, default=ROOT / "reports/phase9/person2/final_registry_integration")
    args = parser.parse_args()
    report_dir = args.report_dir.resolve()
    report_dir.mkdir(parents=True, exist_ok=True)
    handoff_path = ROOT / "configs/registry_peer_champion.json"
    handoff = json.loads(handoff_path.read_text())
    settings = Settings(root=ROOT, model_source="mlflow", registry_handoff=str(handoff_path),
                        model_uri="models:/SolarSelect-Yield-PeerCohort@champion",
                        tracking_uri="sqlite:///" + (ROOT / handoff["database_relative_path"]).resolve().as_posix())
    providers = {"mlflow": MLflowRegistryProvider(settings), "local": LocalFrozenModelProvider(settings)}
    fixture = ROOT / "data/processed/unisolar/peer_cohort/test.csv"
    frame = pd.read_csv(fixture, nrows=8)
    rows = frame[providers["local"].feature_names].to_dict("records")
    direct = Phase5PeerCohortPredictor(
        primary_model_path=ROOT / Phase5PeerCohortPredictor.DEFAULT_ET_PATH,
        fallback_linear_path=ROOT / Phase5PeerCohortPredictor.DEFAULT_EN_PATH,
        metadata_path=ROOT / Phase5PeerCohortPredictor.DEFAULT_METADATA_PATH)
    expected = direct.predict(frame[direct.feature_names])
    body = {"scenario": "historical_site_day", "features": rows[0]}
    roof = json.loads((ROOT / "docs/backend/examples/roof_request.json").read_text())
    openapi = json.loads((ROOT / "docs/backend/openapi.json").read_text())
    evidence = {"started_at_utc": datetime.now(timezone.utc).isoformat(), "checks": [], "parity": {},
                "fixture": str(fixture.relative_to(ROOT)), "fixture_sha256": hashlib.sha256(fixture.read_bytes()).hexdigest(),
                "reference_records": frame[["SiteKey", "Date"]].to_dict("records"),
                "absolute_tolerance": 1e-8, "relative_tolerance": 0}

    def check(client, mode, name, method, path, status, payload=None, raw=None, code=None):
        start = time.perf_counter()
        kwargs = {"content": raw, "headers": {"Content-Type": "application/json"}} if raw is not None else ({"json": payload} if payload is not None else {})
        response = client.request(method, path, **kwargs)
        elapsed = (time.perf_counter() - start) * 1000
        value = response.json() if "application/json" in response.headers.get("content-type", "") else {"html_document": True}
        passed = response.status_code == status and bool(response.headers.get("x-request-id"))
        if code:
            passed = passed and value.get("error", {}).get("code") == code
        evidence["checks"].append({"mode": mode, "name": name, "method": method, "path": path,
                                   "request": payload, "request_raw": raw, "status": response.status_code,
                                   "expected_status": status, "expected_error_code": code,
                                   "actual_response": value, "request_id": response.headers.get("x-request-id"),
                                   "response_time_ms": round(elapsed, 3), "result": "PASS" if passed else "FAIL"})
        assert passed, (mode, name, response.status_code, value)
        return value

    for mode in ("mlflow", "local"):
        with server(mode, report_dir, handoff) as client:
            for path in ("health/live", "health/ready", "model/info", "model/schema", "panels", "panels/PNL-TRINA-330W", "limitations"):
                value = check(client, mode, path, "GET", "/api/v1/" + path, 200)
                if path == "health/ready":
                    assert value["model_source"] == mode
                if path == "model/info":
                    assert value["source"] == mode and value["units"] == "kWh/kWp/day"
                    if mode == "mlflow":
                        assert value["registered_name"] == handoff["registered_name"] and value["registered_version"] == "1"
            for path in ("/docs", "/redoc", "/openapi.json"):
                value = check(client, mode, path, "GET", path, 200)
                if path == "/openapi.json":
                    assert value == openapi
            http_values = []
            for i, row in enumerate(rows):
                request = {"scenario": "historical_site_day", "features": dict(reversed(list(row.items())))}
                value = check(client, mode, f"Historical single {i}", "POST", "/api/v1/predict", 200, request)
                assert value["model"]["source"] == mode
                http_values.append(value["predicted_specific_yield_kwh_per_kwp_day"])
            batch = check(client, mode, "Ordered batch", "POST", "/api/v1/predict/batch", 200,
                          {"rows": [{"scenario": "historical_site_day", "features": row} for row in rows]})
            batch_values = [v["predicted_specific_yield_kwh_per_kwp_day"] for v in batch["results"]]
            provider_values = providers[mode].predict(rows, ModelVariant.PRIMARY_EXTRA_TREES)
            service = PredictionService(providers[mode], RoofService.limitations())
            service_values = [v["predicted_specific_yield_kwh_per_kwp_day"] for v in service.predict(
                [HistoricalRequest(scenario="historical_site_day", features=row) for row in rows], "parity")]
            for values in (http_values, batch_values, provider_values, service_values):
                assert np.allclose(values, expected, atol=1e-8, rtol=0)
            evidence["parity"][mode] = {"direct_frozen": expected.tolist(), "provider": list(provider_values),
                                         "service": service_values, "http_single": http_values, "http_batch": batch_values,
                                         "maximum_absolute_error": float(max(np.max(np.abs(np.asarray(v) - expected)) for v in (http_values, batch_values, provider_values, service_values)))}
            layout = check(client, mode, "Roof geometry", "POST", "/api/v1/roof-fit", 200, roof)["layout"]
            direct_layout = RoofService(ROOT).roof_fit(RoofRequest.model_validate(roof))
            for item in (layout, direct_layout):
                item["engine_metadata"].pop("execution_timestamp")
            assert layout == direct_layout
            for name, request, code in [
                ("Missing fields", {"scenario": "historical_site_day", "features": {"kWp": 1}}, "VALIDATION_ERROR"),
                ("Array/count input", dict(body, features=[1] * 28), "VALIDATION_ERROR"),
                ("Invalid capacity", dict(body, features=dict(rows[0], kWp=0)), "VALIDATION_ERROR"),
                ("Fractional integer", dict(body, features=dict(rows[0], day_of_year=60.25)), "VALIDATION_ERROR"),
                ("Unsupported site", dict(body, site_id="UNKNOWN"), "VALIDATION_ERROR"),
                ("Invalid timestamp", dict(body, timestamp="2022-02-30"), "VALIDATION_ERROR"),
                ("String input", dict(body, features=dict(rows[0], month="3")), "VALIDATION_ERROR"),
                ("Target leakage", dict(body, features=dict(rows[0], target_daily_yield=5)), "VALIDATION_ERROR")]:
                check(client, mode, name, "POST", "/api/v1/predict", 422, request, code=code)
            for name, raw in [("Malformed JSON", '{"scenario":'), ("NaN input", json.dumps(dict(body, features=dict(rows[0], lag1_daily_yield=float("nan"))))),
                              ("Infinity input", json.dumps(dict(body, features=dict(rows[0], lag1_daily_yield=float("inf")))) )]:
                check(client, mode, name, "POST", "/api/v1/predict", 422, raw=raw, code="VALIDATION_ERROR")
            check(client, mode, "Oversized batch", "POST", "/api/v1/predict/batch", 422, {"rows": [body] * 101}, code="VALIDATION_ERROR")
            pending = check(client, mode, "Prospective pending", "POST", "/api/v1/predict", 409,
                            {"scenario": "prospective_roof", "roof_id": "NEW"}, code="PREDICTION_PENDING_LAG_POLICY")
            assert pending["error"]["details"]["predicted_specific_yield_kwh_per_kwp_day"] is None
            check(client, mode, "Unknown panel", "GET", "/api/v1/panels/UNKNOWN", 404, code="PANEL_NOT_FOUND")
            blend = check(client, mode, "Explicit blend policy", "POST", "/api/v1/predict", 409 if mode == "mlflow" else 200,
                          dict(body, model_variant="fallback_blend_50_50"), code="MODEL_VARIANT_NOT_ENABLED" if mode == "mlflow" else None)
            if mode == "local":
                expected_blend = providers[mode].predict(rows[:1], ModelVariant.FALLBACK_BLEND_50_50)[0]
                assert abs(blend["predicted_specific_yield_kwh_per_kwp_day"] - expected_blend) <= 1e-8
    with server("unavailable", report_dir, handoff) as client:
        for path, status in (("health/live", 200), ("health/ready", 503), ("model/info", 503)):
            check(client, "unavailable", "No silent fallback " + path, "GET", "/api/v1/" + path, status)
        check(client, "unavailable", "Unavailable prediction", "POST", "/api/v1/predict", 503, body)
    evidence["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
    evidence["passed"] = len(evidence["checks"])
    evidence["failed"] = 0
    (report_dir / "live_http.json").write_text(json.dumps(evidence, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"passed_http_checks": evidence["passed"], "parity": {k: v["maximum_absolute_error"] for k, v in evidence["parity"].items()}, "openapi_unchanged": True}, indent=2))


if __name__ == "__main__":
    main()
