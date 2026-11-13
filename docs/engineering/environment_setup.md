# Environment Setup — SolarSelect

This document details the software prerequisites, operating system compatibility, single canonical Python runtime configuration, and dependency installation for SolarSelect.

---

## 1. System Requirements

- **Operating System:** macOS (Apple Silicon / Intel), Linux (Ubuntu 20.04+ / Debian 11+), Windows 10/11 (via WSL2 recommended).
- **Single Canonical Python Version:** **Python 3.13.9** (pinned in `.python-version`, standardized on Anaconda `base` at `/opt/anaconda3/bin/python`).
  - *Note (Session 75 Unification):* An earlier Phase 1 Python 3.11 `solarselect` conda environment (`scikit-learn 1.9.1`, missing Streamlit/pytest) was retired so that all ML pipelines, Phase 5 serialized `.joblib` models (`scikit-learn==1.7.2`), Jupyter notebooks (`Python (SolarSelect)` kernel), pytest suites, and the Phase 9 Streamlit UI run strictly on one Python 3.13.9 runtime.
- **Memory (RAM):** Minimum 8 GB (16 GB recommended for ExtraTrees ensemble training).
- **Disk Space:** Minimum 5 GB free space for raw telemetry data, processed CSVs, and model artifacts.

---

## 2. Step-by-Step Installation & Verification

### Step A: Clone Repository
```bash
git clone https://github.com/your-org/SolarSelect.git
cd SolarSelect
```

### Step B: Use the Single Canonical Python 3.13.9 Environment
Ensure your shell and IDE point to `/opt/anaconda3/bin/python` (`Python 3.13.9`):
```bash
conda activate base
python --version
# Expected: Python 3.13.9
```

(If setting up on a fresh machine, create a single Python 3.13.9 environment:)
```bash
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

### Step C: Keep Jupyter Kernel Synchronized
Point the project notebook kernel to the same Python 3.13.9 executable:
```bash
python -m ipykernel install --user --name solarselect --display-name "Python (SolarSelect)"
```

---

## 3. Authoritative Core Dependencies (`requirements.txt`)

| Package | Version Pin | Core Role in SolarSelect |
|---|---|---|
| `python` | `3.13.9` | Single canonical runtime (pinned in `.python-version`) |
| `numpy` | `==2.3.5` | Vectorized numerical computing and linear algebra |
| `pandas` | `==2.3.3` | Tabular data manipulation, time series indexing, CSV I/O |
| `scipy` | `==1.16.3` | Statistical tests and astronomical calculations |
| `scikit-learn` | `==1.7.2` | Exact match for frozen Phase 5 `.joblib` model artifacts (ElasticNet, ExtraTrees) |
| `joblib` | `==1.5.2` | Model serialization and inference loading |
| `xgboost` | `==3.4.1` | Gradient boosted decision tree benchmarking |
| `matplotlib` | `==3.10.6` | Publication-grade analytical figure generation |
| `seaborn` | `==0.13.2` | Statistical distribution plotting and residual heatmaps |
| `plotly` | `==6.3.0` | Interactive charts for Phase 9 dashboard |
| `streamlit` | `==1.51.0` | Phase 9 interactive consumer dashboard |
| `pydantic` | `==2.12.4` | Strict request/response boundary schemas |
| `fastapi` | `==0.162.4` | REST API serving framework |
| `uvicorn` | `==0.54.0` | ASGI application server |
| `pytest` | `==8.4.2` | Automated regression suite (238 tests) |
| `protobuf` | `==6.33.6` | Compatible with both Streamlit 1.51.0 and OpenTelemetry/MLflow |
| `jupyter` | `==1.1.1` | Interactive notebook execution and reporting |
| `nbconvert` | `==7.16.6` | Automated headless notebook execution and QA |
| `dvc` | `==3.67.1` | Data Version Control and pipeline lineage tracking |
| `dvc-s3` | `==3.3.0` | S3 remote storage backend plugin for DVC (enables DagsHub S3 transfer) |
| `mlflow` | `==3.18.0` | Experiment tracking and model registry infrastructure |

---

## 4. DVC Remote Storage & DagsHub Configuration

SolarSelect uses DagsHub as the centralized DVC remote registry. Large dataset files and serialized model binaries are versioned and stored on S3-compatible remote storage rather than directly in Git.

- **Remote Name:** `origin` (default)
- **Remote URL:** `s3://dvc`
- **Endpoint URL:** `https://dagshub.com/pavanpavan1138h-cpu/SolarSelect.s3`
- **Configuration File:** `.dvc/config` (committed to Git; contains public endpoint and remote names only).
- **Authentication & Credential Isolation:**
  - Access keys and tokens are stored in `.dvc/config.local` (or standard AWS/S3 environment variables).
  - `.dvc/config.local` is strictly ignored by Git (enforced via `.dvc/.gitignore`) and **must never be committed**.
  - To configure remote credentials on a new developer workstation:
    ```bash
    dvc remote modify origin --local access_key_id <YOUR_DAGSHUB_ACCESS_KEY>
    dvc remote modify origin --local secret_access_key <YOUR_DAGSHUB_SECRET_KEY>
    ```
- **Remote Connectivity Verification:**
  ```bash
  dvc status -c
  # Expected output: Cache and remote 'origin' are in sync.
  ```

---

## 5. MLflow Tracking & Model Registry Setup

SolarSelect uses a local SQLite backend for MLflow 3.18.0 tracking and registry services:
- **Tracking & Registry Database:** `sqlite:///mlflow.db` (root database file, gitignored).
- **Dedicated Experiment:** `SolarSelect-Phase5-Evaluation` (Experiment ID `2`).
- **Registered Model Registry Aliases:**
  * `SolarSelect-Yield-PeerCohort@champion`: Primary ExtraTrees model (Peer cohort).
  * `SolarSelect-Yield-FullCohort@campus-tracking-conditional`: ElasticNet model (Full cohort macro tracking).
- **Verification CLI Command:**
  ```bash
  python -c "
  import mlflow
  mlflow.set_tracking_uri('sqlite:///mlflow.db')
  client = mlflow.tracking.MlflowClient()
  mv = client.get_model_version_by_alias('SolarSelect-Yield-PeerCohort', 'champion')
  print(f'Peer Champion Model Version: {mv.version} (Run: {mv.run_id})')
  "
  ```
- **Model Evaluation Visualizations CLI:**
  ```bash
  # Dry-run validation (does not write to database or artifact store)
  python src/mlops/log_phase5_visualizations.py --dry-run

  # Live generation and MLflow artifact logging to primary runs
  python src/mlops/log_phase5_visualizations.py
  ```
- **Optional Local MLflow UI Launch:**
  ```bash
  mlflow ui --backend-store-uri sqlite:///mlflow.db --port 5000
  ```

---

## 6. Verification of Environment Integrity

Run the following command to verify that only the unified Python 3.13.9 runtime is active and that Phase 5 models, Phase 9 UI dependencies, and tests run cleanly without warnings:
```bash
python -c "
import sys, numpy as np, pandas as pd, sklearn, joblib, streamlit, mlflow, dvc
print(f'Python: {sys.version.split()[0]} ({sys.executable})')
print(f'NumPy: {np.__version__} | Pandas: {pd.__version__} | Scikit-Learn: {sklearn.__version__} | Streamlit: {streamlit.__version__}')
m = joblib.load('models/phase5/final/peer_cohort/final_extra_trees.joblib')
print('Phase 5 ExtraTrees loaded cleanly:', type(m).__name__)
"
pytest -q tests/
```

---

## 7. GitHub Actions CI/CD Configuration (Secrets & Variables)

For automated CI/CD pipelines, container builds, and deployment workflows, repository administrators configure secrets and environment variables in GitHub under **Settings → Secrets and variables → Actions**:

### 7.1 Encrypted Secrets (Secrets Tab)

| Secret Name | Scope / Permissions | Purpose in CI/CD Pipeline |
| :--- | :--- | :--- |
| `DAGSHUB_TOKEN` | DagsHub Access Token | Authenticates `dvc pull` commands on CI runners to fetch DVC-tracked raw data and frozen Phase 5 model binaries from DagsHub S3 remote storage (`https://dagshub.com/pavanpavan1138h-cpu/SolarSelect.s3`). |
| `GHCR_PULL_USER` | GitHub Username | Username used by the target deployment host/server to authenticate against GitHub Container Registry (`ghcr.io`). |
| `GHCR_PULL_TOKEN` | Personal Access Token (`read:packages`) | Authentication token with read-only package access used by the deployment server to pull the application Docker image. |

#### CI DVC Credential Injection Example:
```bash
# Configure DVC S3 credentials on ephemeral GitHub Actions runners
dvc remote modify origin --local access_key_id "$DAGSHUB_TOKEN"
dvc remote modify origin --local secret_access_key "$DAGSHUB_TOKEN"
dvc pull models/phase5/final/peer_cohort/final_extra_trees.joblib.dvc
```

#### GHCR Docker Login Example:
```bash
echo "$GHCR_PULL_TOKEN" | docker login ghcr.io -u "$GHCR_PULL_USER" --password-stdin
docker pull ghcr.io/<owner>/solarselect:latest
```

### 7.2 Configuration Variables (Variables Tab)

| Variable Name | Default / Example Value | Purpose in CI/CD Pipeline |
| :--- | :--- | :--- |
| `DEPLOY_ENABLED` | `true` or `false` | Boolean toggle gating the CD deployment stage. Prevents deployment if disabled while allowing CI tests to pass. |
| `DEPLOY_URL` | `http://host:8000` | The public base URL of the deployed application/API, used for post-deployment smoke tests and health checks. |

#### Workflow Gating Example:
```yaml
deploy:
  needs: [build-and-test]
  if: vars.DEPLOY_ENABLED == 'true'
  runs-on: ubuntu-latest
  env:
    DEPLOY_URL: ${{ vars.DEPLOY_URL }}
  steps:
    - name: Trigger Remote Deployment
      run: |
        echo "Deploying to ${DEPLOY_URL}..."
        # deployment command / webhook / SSH execution
```
