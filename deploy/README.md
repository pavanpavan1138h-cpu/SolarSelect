# Deployment

Target (configurable): any Linux host with Docker + Compose, reached over SSH; image published to GHCR. For a managed platform (Cloud Run, ECS, Azure Container Apps) reuse the same image and the `/api/v1/health/ready` health check, and run `scripts/verify_deployed_endpoint.py <url>` afterwards.

## Repository secrets / variables (Settings → Secrets and variables → Actions)
| Name | Kind | Purpose |
|---|---|---|
| `DAGSHUB_TOKEN` | secret | `dvc pull` of model artifacts/data (DagsHub S3 remote) |
| `DEPLOY_SSH_KEY`, `DEPLOY_HOST`, `DEPLOY_USER` | secrets | SSH deploy |
| `GHCR_PULL_USER`, `GHCR_PULL_TOKEN` | secrets | GitHub user + read:packages token used on the server |
| `DEPLOY_ENABLED` | variable | `true` to turn the deploy job on (default off) |
| `DEPLOY_URL` | variable | public base URL for the post-deploy check |

The API holds no secrets in frozen mode. Never commit `.env`; see `.env.example`. Use a GitHub Environment `production` with required reviewers.
Rollback: re-run CD for an earlier commit, or `IMAGE=<previous tag> docker compose up -d` on the host.
