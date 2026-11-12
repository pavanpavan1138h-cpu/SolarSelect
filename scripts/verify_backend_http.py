"""Reproducible real HTTP verification. Run against a separately launched local server."""
import argparse
import copy
import importlib.metadata
import json
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
import sys
import numpy as np
import pandas as pd
import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.backend.model_loaders import digest
from src.energy_economics.inference import Phase5PeerCohortPredictor
from src.energy_economics.types import ModelVariant
from app.backend.core.config import Settings
from app.backend.contracts import HistoricalRequest, RoofRequest
from app.backend.model_loaders import LocalFrozenModelProvider
from app.backend.prediction_service import PredictionService
from app.backend.roof_service import RoofService

def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--report-dir", type=Path, default=ROOT / "reports/phase9")
    parser.add_argument("--failure-base-url", help="Separately launched service with missing artifacts")
    parser.add_argument("--registry-base-url", help="Separately launched MLflow-mode service without handoff")
    args = parser.parse_args()
    base = args.base_url.rstrip("/")
    docs, reports = ROOT / "docs/backend", args.report_dir.resolve()
    metadata = json.loads((ROOT / "models/phase5/final_model_metadata.json").read_text())
    names = metadata["feature_space"]["predictive_feature_names"]
    fixture = ROOT / "data/processed/unisolar/peer_cohort/test.csv"
    frame = pd.read_csv(fixture, nrows=8)
    rows = frame[names].to_dict("records")
    body = {"scenario": "historical_site_day", "features": rows[0]}
    roof = {"roof_id": "API-VERIFIED-ROOF", "length": 20.0, "width": 15.0,
            "perimeter_setback": 0.5, "panel_id": "PNL-TRINA-330W",
            "orientation_override": "both", "inter_panel_clearance": 0.02,
            "inter_row_clearance": 0.5,
            "obstacles": [{"obstacle_id": "VENT", "x": 4.0, "y": 5.0,
                           "width": 0.4, "height": 0.5, "buffer": 0.2}]}
    cases = []
    for name, path in [
        ("Liveness", "/api/v1/health/live"), ("Readiness", "/api/v1/health/ready"),
        ("Model info", "/api/v1/model/info"), ("Feature schema", "/api/v1/model/schema"),
        ("Limitations", "/api/v1/limitations"), ("Panels", "/api/v1/panels"),
        ("Panel detail", "/api/v1/panels/PNL-TRINA-330W"),
        ("Swagger", "/docs"), ("ReDoc", "/redoc"), ("OpenAPI", "/openapi.json")]:
        cases.append((name, "GET", path, None, 200))
    cases.extend([
        ("Prediction", "POST", "/api/v1/predict", body, 200),
        ("Explicit blend", "POST", "/api/v1/predict", dict(body, model_variant="fallback_blend_50_50"), 200),
        ("Batch prediction", "POST", "/api/v1/predict/batch",
         {"rows": [{"scenario": "historical_site_day", "features": row} for row in rows]}, 200),
        ("Prospective pending", "POST", "/api/v1/predict", {"scenario": "prospective_roof", "roof_id": "NEW"}, 409),
        ("Roof fit", "POST", "/api/v1/roof-fit", roof, 200),
        ("Unknown panel", "GET", "/api/v1/panels/UNKNOWN", None, 404),
    ])
    for field, value in [("target_daily_yield", 2), ("kWp", 0), ("lat", 91), ("lag1_daily_yield", "missing")]:
        bad = copy.deepcopy(body)
        bad["features"][field] = value
        cases.append((f"Reject {field}", "POST", "/api/v1/predict", bad, 422))
    missing = copy.deepcopy(body)
    del missing["features"]["lag7_daily_yield"]
    cases.append(("Reject missing feature", "POST", "/api/v1/predict", missing, 422))
    invalid_roof = dict(roof, perimeter_setback=10)
    cases.append(("Reject consumed roof", "POST", "/api/v1/roof-fit", invalid_roof, 422))
    for field, value in [("SiteKey", 999999), ("site_id", "UNKNOWN"),
                         ("Date", "2022-02-30"), ("timestamp", "not-a-timestamp")]:
        for location in ("request", "features"):
            bad = copy.deepcopy(body)
            (bad if location == "request" else bad["features"])[field] = value
            cases.append((f"Reject unsupported {location} {field}", "POST", "/api/v1/predict", bad, 422))
    cases.append(("Reject oversized batch (101)", "POST", "/api/v1/predict/batch", {"rows": [body] * 101}, 422))
    for field, value in [("has_valid_lag1", 0.5), ("day_of_year", 367), ("is_weekend", 1)]:
        bad = copy.deepcopy(body)
        bad["features"][field] = value
        cases.append((f"Reject invalid {field}", "POST", "/api/v1/predict", bad, 422))
    items, evidence, responses = [], [], {}
    expectations = {
        "Liveness": "200 LIVE without requiring model readiness",
        "Readiness": "200 READY with initialized local model, catalogue and geometry",
        "Model info": "29-feature peer primary, local source, kWh/kWp/day, offline metrics",
        "Feature schema": "Exact 29 estimator-ordered names with units/constraints",
        "Limitations": "Expose B-1/B-2 and unchanged governance statuses",
        "Panels": "12 catalogue entries; all missing prices remain null",
        "Panel detail": "Verified PNL-TRINA-330W entry with null price",
        "Prediction": "Finite raw primary historical yield with local peer provenance",
        "Explicit blend": "Explicit fallback_blend_50_50 provenance; no silent model change",
        "Batch prediction": "Eight results in request order, all with primary provenance",
        "Prospective pending": "409 PREDICTION_PENDING_LAG_POLICY and null numerical prediction",
        "Roof fit": "Official Phase 7 layout and geometric-only/not-evaluated statuses",
        "Unknown panel": "404 PANEL_NOT_FOUND in stable envelope",
    }
    started_at = datetime.now(timezone.utc).isoformat()
    with httpx.Client(base_url=base, timeout=60) as client:
        for name, method, path, payload, expected in cases:
            start = time.perf_counter()
            response = client.request(method, path, json=payload) if payload is not None else client.request(method, path)
            elapsed = (time.perf_counter() - start) * 1000
            assert response.status_code == expected, (name, response.status_code, response.text)
            value = response.json() if "application/json" in response.headers.get("content-type", "") else {"html_document": True, "bytes": len(response.content)}
            if expected >= 400:
                assert set(value) == {"error", "request_id"}
                assert value["request_id"] == response.headers["x-request-id"]
            if name == "Liveness":
                assert value["status"] == "LIVE"
            elif name == "Readiness":
                assert value["status"] == "READY" and value["model_source"] == "local"
            elif name == "Model info":
                assert value["feature_count"] == 29 and value["cohort"] == "peer_cohort"
                assert value["source"] == "local" and value["units"] == "kWh/kWp/day"
                assert value["model_variant"] == "primary_extra_trees" and "offline_test_metrics" in value
            elif name == "Feature schema":
                assert value["feature_count"] == 29 and value["ordered_feature_names"] == names
                assert len(value["fields"]) == 29
            elif name == "Limitations":
                assert {"B-1", "B-2"}.issubset({v["id"] for v in value["limitations"]})
                assert value["prospective_status"] == "PREDICTION_PENDING_LAG_POLICY"
            elif name == "Panels":
                assert value["count"] == len(value["panels"]) == 12
                assert all(p["price_per_module"] is None and p["price_per_wp"] is None for p in value["panels"])
            elif name == "Panel detail":
                assert value["panel_id"] == "PNL-TRINA-330W" and value["price_per_module"] is None
            elif name in ("Prediction", "Explicit blend"):
                assert np.isfinite(value["predicted_specific_yield_kwh_per_kwp_day"])
                assert value["model"]["model_variant"] == payload.get("model_variant", "primary_extra_trees")
                assert value["model"]["source"] == "local" and value["model"]["cohort"] == "peer_cohort"
            elif name == "Batch prediction":
                assert len(value["results"]) == 8
                assert all(v["model"]["model_variant"] == "primary_extra_trees" for v in value["results"])
            elif name == "Prospective pending":
                assert value["error"]["code"] == "PREDICTION_PENDING_LAG_POLICY"
                assert value["error"]["details"]["predicted_specific_yield_kwh_per_kwp_day"] is None
            elif name == "Roof fit":
                assert "placements" in value["layout"]
                assert value["recommendation_status"] == "RECOMMENDATION_NOT_EVALUATED"
                assert value["electrical_status"] == "NOT_EVALUATED_INSUFFICIENT_SPECIFICATIONS"
            elif name == "Unknown panel":
                assert value["error"]["code"] == "PANEL_NOT_FOUND"
            evidence.append({"name": name, "method": method, "path": path,
                             "status": response.status_code, "request_id": response.headers.get("x-request-id"),
                             "error_code": value.get("error", {}).get("code"),
                             "url": base + path, "request": payload, "actual_response": value,
                             "expected_status": expected, "expected_behavior": expectations.get(name, "Reject invalid input with structured 422; documentation routes serve HTML/JSON with 200"),
                             "response_time_ms": round(elapsed, 3), "result": "PASS"})
            responses[name] = value
            request = {"method": method, "url": "{{base_url}}" + path}
            if payload is not None:
                request.update(header=[{"key": "Content-Type", "value": "application/json"}],
                               body={"mode": "raw", "raw": json.dumps(payload, indent=2),
                                     "options": {"raw": {"language": "json"}}})
            test = [f"pm.test('Expected HTTP {expected}', function () {{ pm.response.to.have.status({expected}); }});"]
            if expected >= 400:
                test.append("pm.test('Structured error', function () { const b=pm.response.json(); pm.expect(b.error.code).to.be.a('string'); pm.expect(b.request_id).to.be.a('string'); });")
            items.append({"name": name, "request": request,
                          "event": [{"listen": "test", "script": {"type": "text/javascript", "exec": test}}]})
        parity = {}
        service = PredictionService(LocalFrozenModelProvider(Settings(root=ROOT, model_source="local")), RoofService.limitations())
        for variant in ModelVariant:
            direct = Phase5PeerCohortPredictor(variant,
                primary_model_path=ROOT / Phase5PeerCohortPredictor.DEFAULT_ET_PATH,
                fallback_linear_path=ROOT / Phase5PeerCohortPredictor.DEFAULT_EN_PATH,
                metadata_path=ROOT / Phase5PeerCohortPredictor.DEFAULT_METADATA_PATH)
            expected = direct.predict(frame[names])
            service_results = service.predict([
                HistoricalRequest(scenario="historical_site_day", features=row, model_variant=variant)
                for row in rows], "direct-service-parity")
            service_values = np.array([v["predicted_specific_yield_kwh_per_kwp_day"] for v in service_results])
            r = client.post("/api/v1/predict/batch", json={"rows": [
                {"scenario": "historical_site_day", "features": dict(reversed(list(row.items()))),
                 "model_variant": variant.value} for row in rows]})
            r.raise_for_status()
            actual = np.array([v["predicted_specific_yield_kwh_per_kwp_day"] for v in r.json()["results"]])
            delta = float(np.max(np.abs(actual-expected)))
            assert delta <= 1e-8
            service_delta = float(np.max(np.abs(service_values-expected)))
            http_service_delta = float(np.max(np.abs(actual-service_values)))
            assert service_delta <= 1e-8 and http_service_delta <= 1e-8
            parity[variant.value] = {"rows": 8, "max_abs_error": delta, "absolute_tolerance": 1e-8,
                                    "relative_tolerance": 0, "direct": expected.tolist(), "http": actual.tolist(),
                                    "service": service_values.tolist(), "service_direct_max_error": service_delta,
                                    "http_service_max_error": http_service_delta,
                                    "reference_records": frame[["SiteKey", "Date"]].to_dict("records")}
        # Syntax/nonfinite failures must be sent as raw bodies, not JSON-encoded strings.
        raw_cases = [("Malformed JSON", '{"scenario":', "json_invalid"),
                     ("NaN input", json.dumps(dict(body, features=dict(rows[0], lag1_daily_yield=float("nan")))), "finite_number"),
                     ("Infinity input", json.dumps(dict(body, features=dict(rows[0], lag1_daily_yield=float("inf")))), "finite_number")]
        for name, raw, expected_type in raw_cases:
            start = time.perf_counter()
            response = client.post("/api/v1/predict", content=raw, headers={"Content-Type": "application/json"})
            elapsed = (time.perf_counter() - start) * 1000
            value = response.json()
            assert response.status_code == 422 and value["error"]["code"] == "VALIDATION_ERROR"
            assert any(e["type"] == expected_type for e in value["error"]["details"])
            evidence.append({"name": name, "method": "POST", "path": "/api/v1/predict",
                             "url": base + "/api/v1/predict", "request_raw": raw, "actual_response": value,
                             "status": response.status_code, "expected_status": 422,
                             "expected_behavior": "Reject invalid JSON/numeric input in stable error envelope",
                             "response_time_ms": round(elapsed, 3), "result": "PASS",
                             "request_id": response.headers.get("x-request-id"), "error_code": value["error"]["code"]})
            items.append({"name": name, "request": {"method": "POST", "url": "{{base_url}}/api/v1/predict",
                          "header": [{"key": "Content-Type", "value": "application/json"}],
                          "body": {"mode": "raw", "raw": raw}},
                          "event": [{"listen": "test", "script": {"type": "text/javascript", "exec": [
                              "pm.test('Rejected with 422', function () { pm.response.to.have.status(422); });"]}}]})
        direct_layout = RoofService(ROOT).roof_fit(RoofRequest.model_validate(roof))
        actual_layout = copy.deepcopy(responses["Roof fit"]["layout"])
        # Separate calls have different audit timestamps; every other official field must agree.
        for layout in (direct_layout, actual_layout):
            layout["engine_metadata"].pop("execution_timestamp")
        assert actual_layout == direct_layout
    for mode, target in (("missing_artifacts", args.failure_base_url), ("registry_no_handoff", args.registry_base_url)):
        if not target:
            continue
        for path, expected in (("/api/v1/health/live", 200), ("/api/v1/health/ready", 503),
                               ("/api/v1/model/info", 503)):
            start = time.perf_counter()
            r = httpx.get(target.rstrip("/") + path, timeout=15)
            elapsed = (time.perf_counter() - start) * 1000
            value = r.json()
            assert r.status_code == expected
            if path.endswith("ready"):
                expected_code = "BLOCKED_PENDING_PERSON1_REGISTRY_HANDOFF" if mode == "registry_no_handoff" else "INITIALIZATION_FAILED"
                assert value["error"]["details"]["model"] == expected_code
            evidence.append({"name": mode + " " + path, "method": "GET", "path": path,
                             "url": target.rstrip("/") + path, "request": None, "actual_response": value,
                             "status": r.status_code, "expected_status": expected,
                             "expected_behavior": "Liveness independent of model; unavailable model fails readiness and info",
                             "response_time_ms": round(elapsed, 3), "result": "PASS",
                             "request_id": r.headers.get("x-request-id"), "error_code": value.get("error", {}).get("code")})
    db = sqlite3.connect((ROOT / "mlflow.db").as_uri() + "?mode=ro", uri=True)
    counts = {t: db.execute("select count(*) from " + t).fetchone()[0] for t in
              ("experiments", "runs", "registered_models", "model_versions", "registered_model_aliases")}
    db.close()
    write(docs / "openapi.json", responses["OpenAPI"])
    write(docs / "postman_collection.json", {
        "info": {"name": "SolarSelect local frozen-model API", "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"},
        "variable": [{"key": "base_url", "value": base}], "item": items})
    for filename, value in [("historical_request.json", body), ("historical_response.json", responses["Prediction"]),
                            ("roof_request.json", roof), ("roof_response.json", responses["Roof fit"]),
                            ("batch_request.json", {"rows": [{"scenario": "historical_site_day", "features": r} for r in rows]})]:
        write(docs / "examples" / filename, value)
    write(reports / "person2_live_http_evidence.json",
          {"base_url": base, "checks": evidence, "responses": responses, "parity": parity,
           "started_at_utc": started_at, "finished_at_utc": datetime.now(timezone.utc).isoformat(),
           "roof_direct_parity_excluding_execution_timestamp": True,
           "fixture": "data/processed/unisolar/peer_cohort/test.csv",
           "fixture_sha256": digest(fixture), "first_row_site": int(frame.iloc[0]["SiteKey"]),
           "first_row_date": str(frame.iloc[0]["Date"]), "registry_read_only_counts": counts,
           "registry_status": "BLOCKED_PENDING_PERSON1_REGISTRY_HANDOFF",
           "packages": {p: importlib.metadata.version(p) for p in
                        ("fastapi", "pydantic", "uvicorn", "httpx", "scikit-learn", "pandas", "numpy", "pytest", "streamlit")}})
    print(json.dumps({"http_checks_passed": len(evidence), "parity": parity,
                      "registry_counts": counts}, indent=2))

if __name__ == "__main__":
    main()
