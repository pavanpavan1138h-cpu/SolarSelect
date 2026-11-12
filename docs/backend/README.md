# SolarSelect local HTTP backend

Run commands from the SolarSelect repository directory (the directory containing requirements.txt), not the outer ZIP folder. The inherited team base declares Python 3.13.9 in .python-version and pins its dependencies in requirements.txt. Person 2's Windows verification used the available Python 3.12.14 environment; Python 3.13.9 execution has not been verified here. Frozen artifacts use scikit-learn 1.7.2, and the existing Streamlit UI uses 1.51.0. Those team pins are preserved; HTTPX is added for API/client verification.

## Setup and launch

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn app.backend.main:app --host 127.0.0.1 --port 8000 --reload
```

macOS/Linux:

```bash
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn app.backend.main:app --host 127.0.0.1 --port 8000 --reload
```

Start the unchanged frontend independently in a second terminal:

```powershell
python -m streamlit run app/frontend/main.py --server.address 127.0.0.1 --server.port 8501
```

If Python is absent from PATH, invoke your installed interpreter by absolute path to create the environment. Verification used the existing project virtual environment; its absolute interpreter path is not a repository prerequisite. Do not regenerate datasets or train models to start this backend.

Swagger: [localhost docs](http://127.0.0.1:8000/docs). ReDoc: [localhost ReDoc](http://127.0.0.1:8000/redoc). Machine-readable schema: [localhost OpenAPI](http://127.0.0.1:8000/openapi.json).

## Version 1 contract

| Method | Route | Behavior |
|---|---|---|
| GET | /api/v1/health/live | Process liveness, even when models cannot load |
| GET | /api/v1/health/ready | 200 only with usable provider and initialized catalogue/geometry; otherwise 503 |
| GET | /api/v1/model/info | Primary model provenance, safe fingerprints, offline_test_metrics |
| GET | /api/v1/model/schema | Actual estimator-ordered 29 fields, units, definitions and constraints |
| GET | /api/v1/limitations | B-1/B-2, geography, capacity support, commercial/electrical gaps, geometry scope |
| POST | /api/v1/predict | One explicitly historical row, or a prospective pending-policy request |
| POST | /api/v1/predict/batch | 1–100 historical requests, in order, each selecting its own variant |
| GET | /api/v1/panels | All 12 immutable panel entries and provenance qualification |
| GET | /api/v1/panels/{panel_id} | One entry; missing prices remain JSON null |
| POST | /api/v1/roof-fit | Official Phase 7 2D layout under layout, with approval/governance context |

Request and nested feature objects reject extra fields. Numeric inputs must be finite JSON numbers; strings, booleans, target fields and missing predictors fail 422. Calendar and indicator consistency is checked; no weather transformations or imputation are performed. Field ordering by name does not change model ordering. No site IDs or target columns belong inside features.

Batch validation is all-or-nothing. A failure returns one error envelope, no partial results; details locate rows with zero-based indexes. Runtime failure also returns no partial batch response. The service does not convert specific yield to annual energy or invent finance/recommendations.

The caller must supply a genuine prepared historical row from an observed site, including its authentic provenance and original installed capacity. The API cannot independently prove measurement authenticity from 29 numbers. Existing prepared datasets can include documented historical training-median imputation; this HTTP layer never synthesizes lag values or fills prospective features. Temporal evaluation does not validate new sites, India or residential rooftops.

Only primary_extra_trees (default) and explicitly requested fallback_blend_50_50 are supported locally. Both trusted predictors are initialized during lifespan, never per request; the blend is invoked only when selected. There is no automatic fallback after failure. Full-cohort models are never exposed. Negative mathematical predictions remain raw with NEGATIVE_PREDICTION_WARNING. Units are kWh/kWp/day; Phase 5 scores are historical offline evaluation, not API benchmarks.

## PowerShell requests

Complete sample files are captured from real local tests. The historical example is SiteKey 15, 2022-03-01; its 29 features contain no target. Use it only to reproduce historical inference.

```powershell
$base = 'http://127.0.0.1:8000'
Invoke-RestMethod "$base/api/v1/health/live"
Invoke-RestMethod "$base/api/v1/health/ready"
Invoke-RestMethod "$base/api/v1/model/info"
Invoke-RestMethod "$base/api/v1/model/schema"
Invoke-RestMethod "$base/api/v1/limitations"
Invoke-RestMethod "$base/api/v1/panels"
Invoke-RestMethod "$base/api/v1/panels/PNL-TRINA-330W"
Invoke-WebRequest "$base/docs"
Invoke-WebRequest "$base/redoc"
Invoke-WebRequest "$base/openapi.json"
Invoke-RestMethod "$base/api/v1/predict" -Method Post -ContentType 'application/json' -InFile docs/backend/examples/historical_request.json
Invoke-RestMethod "$base/api/v1/predict/batch" -Method Post -ContentType 'application/json' -InFile docs/backend/examples/batch_request.json
Invoke-RestMethod "$base/api/v1/roof-fit" -Method Post -ContentType 'application/json' -InFile docs/backend/examples/roof_request.json

# Explicitly select the authorized blend
$historical = Get-Content docs/backend/examples/historical_request.json -Raw | ConvertFrom-Json
$historical | Add-Member model_variant 'fallback_blend_50_50'
Invoke-RestMethod "$base/api/v1/predict" -Method Post -ContentType 'application/json' -Body ($historical | ConvertTo-Json -Depth 10)

# Expected HTTP 409; PowerShell reports an HTTP error
Invoke-RestMethod "$base/api/v1/predict" -Method Post -ContentType 'application/json' -Body '{"scenario":"prospective_roof","roof_id":"NEW"}'

# Expected HTTP 422
Invoke-RestMethod "$base/api/v1/predict" -Method Post -ContentType 'application/json' -Body '{"scenario":"historical_site_day","features":{"kWp":0}}'
```

See [historical request](examples/historical_request.json), [full historical response](examples/historical_response.json), [roof request](examples/roof_request.json), and [official roof response](examples/roof_response.json). Request IDs and timestamps differ between executions; parallel ExtraTrees reductions can differ at machine precision.

Import [postman_collection.json](postman_collection.json) into Postman and set base_url. All endpoints, explicit blend, ordered batch, pending, leakage, missing/invalid predictors, unknown panels, and consumed-roof errors have expected-status assertions. The exported [openapi.json](openapi.json) came from the running server.

## Roof mapping and workload bounds

HTTP uses the existing Phase 9-style length/width fields in metres. inter_panel_clearance maps explicitly to clamping_gap; inter_row_clearance maps to walkway_gap; orientation_override maps to allowed_orientations. None means the engine's both policy. The HTTP default row clearance is 0.5 m, preserving the existing UI schema, whereas the core engine default is 0.05 m; the adapter always passes the HTTP value explicitly.

Obstacles use x/y/width/height/buffer in metres. Integer quantization, setbacks, obstacles and placements remain entirely in Phase 7. No floating-point tolerance relaxes geometry. HTTP workload bounds are 200 m per roof side and 100 obstacles; these are service resource limits, not engineering approvals. The result is geometric feasibility only, with RECOMMENDATION_NOT_EVALUATED and NOT_EVALUATED_INSUFFICIENT_SPECIFICATIONS.

## Configuration and model lifecycle

SOLARSELECT_ROOT optionally selects an operator-controlled repository root. Otherwise paths resolve from backend module location, independently of current working directory. Frozen artifact paths are fixed relative to that root; HTTP clients cannot choose paths or URIs. The audited backend frozen_manifest.json pins SHA-256 for both authorized binary artifacts and final metadata, verified before joblib deserialization. Binary artifact hashes are exact. Metadata is hashed after CRLF-to-LF normalization to accommodate Git text checkout on Windows; every other metadata byte remains pinned, and no metadata file is rewritten. Estimator ordering is cross-checked against metadata and the HTTP contract. Do not update the manifest to bypass a mismatch; obtain a reviewed artifact handoff.

MODEL_SOURCE defaults to local. Registry configuration uses MODEL_SOURCE=mlflow, MLFLOW_TRACKING_URI, MLFLOW_MODEL_URI=models:/name@alias and REGISTRY_HANDOFF_FILE. See [the Registry Handoff Contract](person1_registry_handoff.md). Restart the service after changing configuration. An incomplete/empty/unavailable registry makes readiness 503 and model routes unavailable; liveness remains 200. It never silently serves local predictions as a registry champion. The approved Person 1 SQLite/skops handoff is now loaded and parity-verified in registry mode. The verified local configuration is configs/registry_peer_champion.json; registry/package files stay ignored under .person2-local/. See the handoff document for import, launch, trust checks and actual mixed-type signature.

No CORS origins are enabled. The default launch binds 127.0.0.1. Streamlit's future server-side HTTP calls do not require browser CORS. Deploying to public networks, adding authentication or weather integrations is outside this local deliverable.

## Errors and monitoring/frontend integration

All errors use this shape:

```json
{"error":{"code":"VALIDATION_ERROR","message":"Request validation failed.","details":[{"location":["body","features","kWp"],"type":"greater_than","message":"Input should be greater than 0"}]},"request_id":"generated-uuid"}
```

The discriminator can add historical_site_day to validation locations; consume location as an array. Every response carries X-Request-ID matching the body where a body request_id exists.

| HTTP | Codes |
|---|---|
| 409 | PREDICTION_PENDING_LAG_POLICY; MODEL_VARIANT_NOT_ENABLED in registry mode |
| 422 | VALIDATION_ERROR, INVALID_MODEL_INPUT, INVALID_ROOF_INPUT |
| 404 | PANEL_NOT_FOUND, HTTP_ERROR for unknown routes |
| 503 | NOT_READY, MODEL_UNAVAILABLE, GEOMETRY_UNAVAILABLE, INVALID_MODEL_OUTPUT, ENGINE_UNAVAILABLE |
| 500 | INTERNAL_ERROR |

The solarselect.api logger emits JSON request_id, route template, status, duration_ms, selected model_variant and error_code. Startup errors include service, safe code and exception type. No payloads, credentials or exception text are logged by this logger. Tracebacks are never returned. Uvicorn access messages are separate.

Frontend owner: preserve existing SolarSelectPlatformService and schemas; use these versioned HTTP contracts when wiring real actions. Render error/pending states explicitly, leave unavailable metrics blank, display governance limitations, and keep synthetic existing charts labeled DEMONSTRATION DATA ONLY. Do not interpret ready as validation of prospective forecasting. Model info's scores must be labeled offline_test_metrics.

Monitoring owner: alert on readiness failures, sustained 5xx and INVALID_MODEL_OUTPUT; correlate X-Request-ID with JSON request logs. Latency logs are observations, not re-evaluated model performance. No drift monitoring or retraining was added.

## Verification and troubleshooting

```powershell
python -m pytest -q tests -k test_api
python -m pytest -q tests/
python scripts/verify_backend_http.py
python -m pip check
```

The first command avoids shell-specific wildcard expansion. The live verifier requires a separately running server; it asserts real HTTP outcomes, compares direct predictor, PredictionService and HTTP outputs for eight genuine reference rows and both variants (absolute tolerance 1e-8, relative zero), exports OpenAPI/Postman/examples, and reads registry counts in SQLite read-only mode. It never trains or calculates renewed held-out metrics. Use --report-dir reports/phase9/person2/submission_verification for new evidence. Optional --failure-base-url and --registry-base-url exercise separately launched unavailable-model instances. The legacy verifier expects an available local mlflow.db for its read-only registry summary; the database is not committed. See the [final submission](../../reports/phase9/person2/FINAL_PERSON2_SUBMISSION.md) and [verified champion integration](../../reports/phase9/person2/FINAL_REGISTERED_CHAMPION_INTEGRATION.md).

For 503 startup errors, inspect startup service/code/exception_type and verify the configured root, trusted files and environment. A fingerprint mismatch requires restoring reviewed bytes, not modifying models. A missing registry handoff remains blocked. A 422 lists exact fields/indexes; send numbers rather than numeric strings and remove targets. A 409 prospective response requires a separately authorized lag policy or lag-free model, not zero-filled lags or an external weather substitution.

Implementation follows FastAPI's [lifespan](https://fastapi.tiangolo.com/advanced/events/) and [lifespan testing](https://fastapi.tiangolo.com/advanced/testing-events/) patterns and Pydantic's [strict types](https://docs.pydantic.dev/latest/api/types/) contracts.

## Verified Person 1 champion (2026-11-12)

The existing MLflowRegistryProvider supports the actual SolarSelect-Yield-PeerCohort champion, version 1, in addition to the existing frozen source. The adapter resolves the approved alias from the supplied SQLite snapshot read-only, verifies package hashes, and maps the original macOS artifact URI to the imported Windows directory without changing either source file. No MLflow UI or new registration is required.

The actual signature is 24 doubles and five longs, in the same 29-feature order as Phase 5. Integer fields are day_of_year, month, day_of_week, is_weekend and has_valid_lag1. Conversion is confined to the provider: exact integral values become int64, with fractional/out-of-range values rejected. Other features stay float64. The existing HTTP contracts and OpenAPI are unchanged. The estimator has no extra scaler or preprocessing pipeline; upstream historical feature preparation remains the caller's responsibility.

Follow [person1_registry_handoff.md](person1_registry_handoff.md) to import and launch. Set Postman's model_source collection variable to mlflow for registry mode, or local for frozen mode. Its explicit-blend assertion expects 409 in registry mode and 200 locally.

Fresh verification: 118 dedicated API tests passed; 361 passed and one external legacy evaluation-store failure in the full suite; 74 live HTTP checks passed across registered, frozen and unavailable-source modes. Eight genuine held-out records matched independent frozen, provider, service, single HTTP and batch HTTP predictions within 1e-8 absolute tolerance (relative zero); the observed live maximum was 8.881784197001252e-16. The registered estimator's 100 fitted trees also matched the frozen estimator exactly.

Run the actual-asset tests and live verifier after provisioning:
```powershell
$env:SOLARSELECT_REQUIRE_REGISTRY_TESTS = '1'
python -m pytest -q tests -k test_api
python -m pytest -q tests/
python scripts/verify_registered_backend.py
```

The new live verifier launches/stops only its own loopback processes and writes evidence without updating the API schema or examples. The older verify_backend_http.py remains local-mode-specific. Tests use the available Python 3.12.14 environment; the declared Python 3.13.9/dependency set still requires deployment-owner verification. MLflow dependency/Python mismatch warnings are retained in the local logs. See [the authoritative final submission](../../reports/phase9/person2/FINAL_PERSON2_SUBMISSION.md).

Final completion: the current authoritative status and committed file list are in [FINAL_PERSON2_SUBMISSION.md](../../reports/phase9/person2/FINAL_PERSON2_SUBMISSION.md). The API has no built-in authentication; Person 3 must supply authenticated TLS/network controls before public exposure. Use loopback during local verification. Raw XML/local audit pointers are ignored; the source, tests, scripts and safe handoff JSON belong in the feature-branch commit.
