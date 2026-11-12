# Verified Person 1 registry handoff

Verified 2026-11-12 from the user-supplied supplementary archive, without creating a registration, retraining or replacing backend code. This supersedes the earlier inaccessible-registry blocker. Historical evidence remains in earlier reports.

## Approved identity and provenance

- Registered name: SolarSelect-Yield-PeerCohort; version 1; alias champion; READY.
- URI: models:/SolarSelect-Yield-PeerCohort@champion.
- Run: 4b451f68e1c04de49875b095a4defd40.
- Logged model: m-0fd6281417054bf385101d2a68c3f6a5.
- Version source: models:/m-0fd6281417054bf385101d2a68c3f6a5.
- Original storage: file:///Users/apple/Documents/5th%20sem%20el/MLOps_EL/SolarSelect/mlruns/models/m-0fd6281417054bf385101d2a68c3f6a5/artifacts.
- Algorithm: fitted ExtraTreesRegressor; all 100 fitted trees and estimator parameters match the trusted frozen primary exactly.
- Raw source-run cohort is peer, role primary_candidate; normalized API cohort remains peer_cohort. Model-version tags are actually empty. No tags were invented or written.
- Units kWh/kWp/day are substantiated by the registered model description, daily_specific_yield_kwh_per_kwp target, frozen DVC lineage and parity.
- DVC primary MD5: 420ea113a69405396faab910e25a04a5; frozen SHA-256: 39b4a11beb5423dff926e43b4594b7938957183daaa16f16bdea7e5dc54ecfe9.

The supplied DB also contains SolarSelect-Yield-FullCohort v1 alias campus-tracking-conditional. Its package is not imported or served. Full Cohort registration alone does not authorize rooftop recommendations.

## Import and explicit launch

Provision the team's frozen artifacts and genuine processed peer test.csv through the existing approved DVC/handoff workflow first. They are required for independent reference verification and have not been changed.

From the repository root, using the reviewed supplementary archive:
```powershell
python scripts/prepare_person1_registry.py '..\SolarSelect_Person2_Integration_Files.zip'
$env:MODEL_SOURCE = 'mlflow'
$env:MLFLOW_TRACKING_URI = 'sqlite:///' + ((Resolve-Path '.person2-local/registry/mlflow.db').Path -replace '\\','/')
$env:MLFLOW_MODEL_URI = 'models:/SolarSelect-Yield-PeerCohort@champion'
$env:REGISTRY_HANDOFF_FILE = (Resolve-Path 'configs/registry_peer_champion.json').Path
python -m uvicorn app.backend.main:app --host 127.0.0.1 --port 8000
```

The importer requires the exact reviewed archive and manifest hashes, then checks all eight selected file hashes/sizes before writing. It refuses to overwrite different existing files. It imports only the DB and seven approved package files. The imported directory and rollback snapshots are ignored by Git. Original root mlflow.db is intentionally not replaced.

The configuration records full expected SHA-256 values and relative paths. It is an operator-reviewed trust anchor; clients cannot choose or edit it. The DB is read with SQLite mode=ro and immutable=1. The alias resolves to the approved version/source/run, then MLflow loads the byte-verified mapped package directory. This avoids migrations, global tracking-state changes and rewriting original macOS paths. The snapshot is pinned; a later champion version or new snapshot needs a reviewed configuration update, not an automatic alias upgrade.

Default MODEL_SOURCE=local remains the frozen provider. To restore it explicitly, stop the service, set MODEL_SOURCE=local and restart. No failure silently changes the configured model source. Registry mode exposes only the primary variant; explicit blend returns 409 MODEL_VARIANT_NOT_ENABLED. Local explicit blend continues to work.

## Signature, preprocessing and serialization

The full input signature is in configs/registry_peer_champion.json and the unchanged MLmodel package. Feature names/order exactly match frozen final_model_metadata.json and feature_names_in_. There are 24 required doubles and five required longs: day_of_year, month, day_of_week, is_weekend, has_valid_lag1. Output is one required double target_daily_yield per row.

There is no additional scaler, imputer or pipeline inside the registered estimator. Genuine historical lags and prepared upstream features are required. The adapter validates existing features and losslessly types the five integer columns; it never rounds, truncates, synthesizes or fills values. Public Pydantic schemas remain unchanged.

The package is code-free MLflow sklearn/python_function flavor with skops serialization. Only sklearn.tree._tree.Tree is explicitly trusted. Before deserialization, package SHA-256 values, descriptor, exact signature, frozen/DVC lineage and skops.get_untrusted_types are checked; observed types must equal that reviewed allowlist. It does not automatically trust every reported type. Installed MLflow 3.18.0, scikit-learn 1.7.2 and skops 0.16.0 are required. MLflow code-execution policy is not weakened.

Trust guidance: [skops persistence](https://skops.readthedocs.io/en/latest/persistence.html), [MLflow sklearn loader](https://mlflow.org/docs/latest/api_reference/_modules/mlflow/sklearn.html). Matching hashes establish continuity with the reviewed supplied handoff; they are not an independent signature by Person 1.

## Evidence and deployment limits

Fresh dedicated API tests: 118 passed, zero failed/skipped/errors. Fresh full suite: 361 passed, one external legacy evaluation-store failure, zero skipped/errors. Actual registered-model tests do not create substitute registrations. Existing upstream tests create isolated temporary test-only registrations; these are never used as serving evidence.

Seventy-four live HTTP checks passed. Eight real held-out records matched direct frozen, registered provider, existing prediction service and HTTP single/batch responses with maximum observed live absolute difference 8.881784197001252e-16 (allowed 1e-8, rtol 0). All 100 fitted trees match exactly. OpenAPI is unchanged; missing source stays unready with liveness available, and prospective roofs still return the existing pending-policy error.

The recorded package/runtime is Python 3.13.9, NumPy 2.3.5 and SciPy 1.16.3. Verification here used Python 3.12.14, NumPy 2.5.4 and SciPy 1.18.1, with matching MLflow/sklearn/skops versions. Warnings were inspected and retained. Do not treat this as a clean canonical-runtime deployment certification; Person 3 must reproduce with the declared runtime/dependencies.

The SQLite cleanup failure is fixed by disposing only temporary tracking/registry pools and restoring fluent URI/environment state in the inherited test; original assertions remain. One full-suite failure remains because the legacy visualization test hardcodes the older root DB and original macOS paths. All ten authentic charts were found and hashed read-only in the approved original archive; Person 1 owns portable legacy evaluation-store wiring. No database, artifact or prediction expectation was fabricated to make this pass. See the [final integration report](../../reports/phase9/person2/FINAL_REGISTERED_CHAMPION_INTEGRATION.md).

The adjacent registry_handoff.template.json documents the earlier remote-registry contract (all-double/version-tags). It is retained for that path; use configs/registry_peer_champion.json for this actual mixed-type SQLite handoff.
