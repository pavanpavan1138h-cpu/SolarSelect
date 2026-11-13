# SolarSelect: Person 3 and Person 4 handoff

Branch with everything: https://github.com/pavanpavan1138h-cpu/SolarSelect/tree/feature/person3-person4-qa-devops
(based on `feature/person2-final-backend`). A few late changes (Grafana provisioning, compose update) are in the attached zip and may not be pushed yet.

## What was done
| Area | Delivered |
|---|---|
| **Person 3: model QA** | `tests/phase9/person3/` (62 tests): artifact SHA-256, 29-feature contract, leakage, reproducibility, frozen vs API parity (1e-8), input robustness, held-out metrics. Reports in `reports/phase9/person3/` |
| **Person 4: DevOps** | `Dockerfile` (non-root, health check), `docker-compose.yml`, `requirements-api.txt` / `requirements-ci.txt`, `.github/workflows/ci.yml` and `cd.yml`, `deploy/`, `scripts/verify_deployed_endpoint.py`, `tests/phase9/person4/`. Report: `reports/phase9/person4/PERSON4_DEVOPS_REPORT.md` |
| **Monitoring (extra)** | `/metrics` endpoint, drift (PSI/KS), 9 alert rules + runbook, Prometheus + Grafana dashboard. `monitoring/`, `reports/phase9/monitoring/` |
| **Fixes to earlier work** | Corrected fallback-blend and persistence metrics in `final_model_metadata.json` (old values kept under `qa_corrections`; pinned hash in `frozen_manifest.json` updated); `/predict/batch` now one model call per variant (about 3x faster); starlette pinned; OpenAPI wording test fixed; MLflow visualization test fixed by running Person 1's own scripts; `validate_features` docstring corrected |

## Results (run locally, 2026-11-12)
- Full suite: **470 passed, 0 failed**. Fresh-clone dry run mimicking CI: 440 passed, 28 skipped (need Person 1's local-only registry files).
- Docker image builds (159 MB), container healthy, `verify_deployed_endpoint.py` 8/8.
- GitHub: secret-free `static` CI job passes. Full test/Docker jobs have **not** run yet (need the secret/variable below).

## What you need to run it
**Software:** Python 3.13, Docker (Docker Desktop, or Colima on Mac: `colima start`), Git, (optional) DVC.

**Model and data files** are DVC-tracked (git-ignored). Either copy them from a teammate's checkout or run `dvc pull` with the DagsHub token (see "Secrets"). Needed paths: `models/phase5/**`, `data/processed/**`.

**Run the tests**
```bash
python3.13 -m venv .venv && .venv/bin/pip install -r requirements-ci.txt
.venv/bin/python -m pytest -q
```
(Two tests read Person 1's local `mlflow.db`; CI skips them.)

**Run in Docker**
```bash
docker compose up -d --build api     # API at http://localhost:8000/docs
python3 scripts/verify_deployed_endpoint.py http://localhost:8000
docker compose up -d                 # adds Prometheus :9090 and Grafana :3000 (dashboard: /d/solarselect-mon)
docker compose down
```

## What the repo owner must do on GitHub (Settings -> Secrets and variables -> Actions)
| Name | Kind | Needed for |
|---|---|---|
| `DAGSHUB_TOKEN` | secret | `dvc pull` in CI/CD |
| `HAS_DVC_REMOTE` = `true` | variable | enables the test + Docker CI jobs |
| `DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_SSH_KEY`, `GHCR_PULL_USER`, `GHCR_PULL_TOKEN` | secrets | SSH deploy (only if deploying) |
| `DEPLOY_ENABLED` = `true`, `DEPLOY_URL` | variables | turns the deploy job on / post-deploy check |
Also create a GitHub Environment named `production`. Details: `deploy/README.md`.

## Open items
1. Add the secret/variable, then re-run CI and fix anything the first full run finds.
2. Open/merge the pull request.
3. Pick a deployment target (none chosen), then run the deployed-endpoint check.
4. Person 1: confirm where the old fallback metrics (MAE 0.8898) came from.
5. Project owner: confirm the provisional alert thresholds (`monitoring/configs/alert_rules.json`).

## Known limits of the model
R² 0.258 on held-out data (beats persistence baseline). Trained on one Melbourne campus, May-Dec 2021 only, so it drifts on other seasons. Prospective roofs are intentionally blocked (HTTP 409, lag policy pending). Energy basis (AC/DC) unverified. Full list: `reports/phase9/person3/MODEL_LIMITATIONS_AND_RISKS.md`.
