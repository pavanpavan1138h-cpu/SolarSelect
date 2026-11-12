> Historical blocker report. Superseded on 2026-11-12 by [current final submission](FINAL_PERSON2_SUBMISSION.md); the supplied registry/package is now loaded and prediction parity verified. Historical findings below describe the earlier database copy.

# Final MLflow Integration — Person 2

Date: 2026-11-12 (Asia/Calcutta).

**Final status: BLOCKED_PENDING_PERSON1_DATABASE_AND_ARTIFACT_HANDOFF. Registry integration is not complete.**

The two registrations confirmed by Person 1 are absent from the database available in this checkout. In accordance with the explicit instruction to stop at a documented blocker if the approved registry is unavailable, no substitute registration, production switch, artifact load or registered-model parity claim was made.

## 1. Absolute database path and discovery

The repository root used throughout this work is:

```text
C:\Users\nithe\OneDrive\Documents\ChatGPT\MLOPs SOLAR\SolarSelect 3\SolarSelect
```

Its SQLite database resolves to:

```text
C:\Users\nithe\OneDrive\Documents\ChatGPT\MLOPs SOLAR\SolarSelect 3\SolarSelect\mlflow.db
```

The already-running MLflow UI on http://127.0.0.1:5000 uses the repository database launched earlier with sqlite:///mlflow.db from this root. This audit queried SQLite directly with mode=ro and checked the named registrations through that UI's REST API.

Searches covered the current workspace and accessible OneDrive Documents/Desktop, Downloads, Documents and Desktop locations. No other mlflow.db or MLmodel package was found in those search scopes. Windows CIM process-command-line inspection returned Access denied; process working directories could not be independently inspected through that interface. No claim is made that all disks or another person's machine were searchable.

## 2. Actual registration findings

| Person 1 confirmation | Expected version | Expected alias | SQLite finding | Local MLflow HTTP lookup |
|---|---:|---|---|---|
| SolarSelect-Yield-PeerCohort | 1 | champion | No model, version or alias row | 404 RESOURCE_DOES_NOT_EXIST |
| SolarSelect-Yield-FullCohort | 1 | campus-tracking-conditional | No model, version or alias row | 404 RESOURCE_DOES_NOT_EXIST |

The requested models:/SolarSelect-Yield-PeerCohort@champion cannot resolve against this database.

This database is no longer completely empty: it contains 3 experiments, 16 runs, 3 registered-name rows, 12 version rows and 12 aliases. All three registered-name rows are MLflow demonstration prompts:

- mlflow-demo.prompts.code-reviewer
- mlflow-demo.prompts.customer-support
- mlflow-demo.prompts.document-summarizer

Their version sources are dummy-source and they are unrelated to the approved SolarSelect regressors. Their presence and READY statuses must not be mistaken for the Peer/Full Cohort registrations. The UI's ordinary registered-model search filters these prompt entries and returns an empty model result. None of these entries was created, modified or deleted by this audit.

## 3. Evidence this is an older/different registry copy

The original eight SolarSelect-Forecasting run IDs and artifact URIs in this database match the database bundled in SolarSelect 3.zip exactly. That archived snapshot contains 2 experiments, 8 runs and no registered models, versions or aliases.

The original experiment/run locations point to a macOS repository:

```text
/Users/apple/Documents/MLOps_EL/SolarSelect/EDA/mlruns/1
/Users/apple/Documents/MLOps_EL/SolarSelect/EDA/mlruns/1/<run-id>/artifacts
```

The local pre-UI SQLite backup also contains no registrations. The current demo additions therefore do not provide the two newer Phase 5 registrations Person 1 described. These findings strongly indicate this Windows checkout lacks Person 1's updated registry/artifact handoff. The approved database's actual location on Person 1's machine cannot be established from the files currently accessible here.

Raw names, sources, aliases, experiment paths, matching original run IDs, snapshot hashes and the two HTTP 404 responses are recorded in [database_discovery.json](final_mlflow/database_discovery.json).

## 4. Registered artifact/signature verification

| Required verification | Status |
|---|---|
| Actual Peer Cohort registered name/version/alias resolution | BLOCKED: registration absent here |
| Registered artifact source URI | UNAVAILABLE: no matching version row |
| Artifact accessibility and trusted package | NOT_EXECUTED |
| Actual MLflow input signature | NOT_EXECUTED |
| Feature count, names, order and types | NOT_VERIFIED for registered model |
| Registered preprocessing pipeline | NOT_VERIFIED |
| Registered prediction units and lineage | NOT_VERIFIED |
| Frozen-versus-registered prediction parity | NOT_EXECUTED |
| Registered-model-versus-FastAPI parity | NOT_EXECUTED |

The expected local reference has 29 ordered predictors and predicts daily specific yield in kWh/kWp/day. That expectation is not evidence that an unavailable registered package has the same signature. No schema changes were made based on an assumed match.

Both frozen artifacts and final metadata still match the existing pinned SHA-256 manifest. The primary ExtraTrees reference SHA-256 is:

```text
39b4a11beb5423dff926e43b4594b7938957183daaa16f16bdea7e5dc54ecfe9
```

## 5. FastAPI and fallback decision

The current checkout calls the frozen implementation LocalFrozenModelProvider (the role referred to as FrozenModelProvider in the request). It and the existing MLflowRegistryProvider remain unchanged.

The registry provider must not be switched to an unresolvable model alias or bypass its signature, lineage and parity gates. No handoff JSON containing invented identities was generated. Local frozen serving remains available with the existing configuration; no automatic source switching or silent registry-to-local relabeling was introduced. The Full Cohort model is not exposed for individual rooftop recommendations.

The existing process on port 8000 reports model_source=frozen through a different response contract from this checkout, as previously documented. It was not modified, restarted or counted as proof of registry integration.

## 6. Tests and execution scope

This task executed database/path/snapshot inspection, named local MLflow HTTP lookups and frozen-manifest integrity checks.

Under the explicit stop-at-blocker rule, the following were **NOT_EXECUTED in this task**:

- Registered Peer Cohort model deserialization.
- Actual signature/pipeline/unit/lineage verification.
- Frozen/registered/FastAPI prediction parity.
- Registry-mode readiness, prediction and batch success checks.
- Dedicated API and full repository pytest reruns.
- Malformed/prospective-request regression reruns after a registry integration.

No new passing test count is claimed. Earlier evidence recorded 90 API tests and 328 repository tests passing, but those results predate this task and do not validate the unavailable registered model. No historical expected predictions or tests were altered.

## 7. Exact handoff required from Person 1

Provide either a complete portable handoff or an accessible running tracking server.

### Portable database/artifact handoff

1. A consistent SQLite backup from Person 1's actual repository after registration, containing:
   - SolarSelect-Yield-PeerCohort, version 1, alias champion.
   - SolarSelect-Yield-FullCohort, version 1, alias campus-tracking-conditional.
   - Their originating run records, version metadata and tags.
2. The actual artifact storage directories referenced by those versions and runs. A database alone is insufficient when artifact URIs point to /Users/apple/... on another machine.
3. The complete Peer Cohort MLflow model package: MLmodel, serialized estimator or pipeline, dependency/environment files such as requirements.txt, conda.yaml and python_env.yaml, and any wrapper/code/preprocessing resources named by MLmodel.
4. An explicit mapping from original artifact URIs to accessible local files, or a server that can resolve and serve those original sources. Do not merely copy the database and assume macOS absolute paths become valid on Windows.
5. Trusted artifact/package hashes, exact signature/preprocessing/units/cohort/variant metadata, originating run/version lineage and the reviewed handoff JSON required by the existing provider.
6. Approved reference inputs/predictions or authorization to use the already-established genuine eight-row fixture. The existing absolute parity tolerance is 1e-8, relative tolerance zero.

### Running-server alternative

Provide the reachable MLflow tracking/registry URI serving Person 1's actual database, authentication configured securely outside chat, and working artifact access for models:/SolarSelect-Yield-PeerCohort@champion. A localhost URI on another machine is not reachable as this machine's localhost.

The repository's [Registry Handoff Contract](../../../docs/backend/person1_registry_handoff.md) and [template](../../../docs/backend/registry_handoff.template.json) describe the current provider's fields and required gates. Do not overwrite this checkout's database or rewrite existing registry paths without preserving the original and reviewing the supplied mapping.

## 8. Completion decision

**Person 2's final registry integration remains blocked.** No retraining, DVC dataset changes, frozen-model overwrites, replacement registrations, endpoint/schema changes or fabricated parity evidence occurred. Work can resume once Person 1's actual registered database and accessible artifact package—or an accessible server serving both—are supplied.
