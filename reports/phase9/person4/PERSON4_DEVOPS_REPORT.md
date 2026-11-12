# Person 4 — Containerisation, CI/CD and deployment report

## Delivered
| Item | File(s) |
|---|---|
| Dockerfile (python:3.13-slim, non-root user, HEALTHCHECK on `/api/v1/health/ready`, only the files the service needs) | `Dockerfile`, `.dockerignore` |
| Dependency / environment management | `requirements-api.txt` (runtime), `requirements-ci.txt` (tests), pins asserted equal to `requirements.txt`; `.env.example` |
| Local multi-service container config | `docker-compose.yml` (api + Prometheus + Grafana), `monitoring/configs/prometheus.yml` |
| CI | `.github/workflows/ci.yml`: pytest (with `dvc pull`) → docker build → run container → wait healthy → smoke test |
| CD | `.github/workflows/cd.yml`: after CI on `main` (or manual) build + push image to GHCR; SSH deploy to a `production` environment, gated by `vars.DEPLOY_ENABLED`; post-deploy verification |
| Production compose | `deploy/docker-compose.prod.yml` (read-only FS, no-new-privileges), `deploy/README.md` (secrets, variables, rollback) |
| Final endpoint verification | `scripts/verify_deployed_endpoint.py` (8 checks: live/ready, model identity + fingerprint, prediction equals documented reference, 409 lag guard, 422 validation, panels, metrics) |
| Tests | `tests/phase9/person4/` — 13 passed (includes the real Docker build/run/health/smoke test) |

## Verified in this session
- Static tests above pass; compose files parse (`docker compose config` ok).
- The slim image's file set and the minimal `requirements-api.txt` were **simulated outside Docker**: a clean venv with only those packages, containing only the files the Dockerfile copies, started the app, reported READY and served `/metrics`. `verify_deployed_endpoint.py` passes 8/8 against a live uvicorn.
- Full suite with all additions: see TEST_RESULTS.md.

## Container verified locally (Colima runtime, 2026-11-12)
Image built (159 MB, runs as user `app`), container reached `healthy`, `verify_deployed_endpoint.py` passed 8/8 against it, and the Docker test in `tests/phase9/person4` passed.

## NOT verified / not done (be explicit)
1. (resolved) image build and run — see above.
2. **Workflows never ran.** They need to be pushed to GitHub, with the secrets below; YAML validity is tested but GitHub execution is not.
3. **Nothing is deployed.** No deployment target, host or credentials were provided; the CD job is off until `DEPLOY_ENABLED=true` and the secrets exist. "Final deployed endpoint verification" is therefore implemented but not yet executed against a real deployment.
4. **Model artifacts come from DVC** (`*.joblib` are git-ignored). CI/CD need `DAGSHUB_TOKEN`; without it `dvc pull` fails. Confirm the DagsHub S3 endpoint accepts the token as both access key and secret (typical for DagsHub; verify on first run).
5. Registry (MLflow) mode is not containerised; the image serves the frozen, hash-verified model (`MODEL_SOURCE=local`).
6. (resolved) the OpenAPI wording test now ignores the 422 reason-phrase difference.
7. (resolved) MLflow visualization test fixed; starlette pinned.
8. CI: a secret-free `static` job always runs; the test and docker jobs run once repository variable `HAS_DVC_REMOTE=true` and `DAGSHUB_TOKEN` exist.
