# Reproducibility — SolarSelect

This document details the seed controls, deterministic execution guarantees, and audit protocols enforced to ensure complete scientific reproducibility.

---

## 1. Deterministic Random Seeds

All stochastic operations in SolarSelect (tree ensemble bootstrap subsampling, cross-validation partitioning, feature subsampling) are initialized with fixed global random seeds:

```python
# Standardized global seed across all scripts and notebooks
GLOBAL_RANDOM_SEED = 42

# Scikit-learn model instantiation standard:
ExtraTreesRegressor(..., random_state=42)
ElasticNet(..., random_state=42)
RandomForestRegressor(..., random_state=42)
```

---

## 2. Deterministic Chronological Partitioning

Splitting is performed by explicit calendar date filters, eliminating any stochastic variation:
- **Training Set:** `Date >= '2021-05-01' and Date <= '2021-12-31'`
- **Validation Set:** `Date >= '2022-01-01' and Date <= '2022-02-28'`
- **Test Set:** `Date >= '2022-03-01' and Date <= '2022-04-23'`

Because rows are partitioned by absolute calendar bounds rather than randomized percentage indexing, row counts are bit-for-bit identical across runs:
- Full Cohort: Train $= 4,770$, Val $= 1,037$, Test $= 1,232$.
- Peer Cohort: Train $= 4,383$, Val $= 945$, Test $= 1,128$.

---

## 3. Data Version Control (DVC)

SolarSelect enforces a strict separation between Git (source code, configuration, reports, small metadata JSONs) and DVC (large raw telemetry datasets, reproducible processed data matrices, and frozen binary model artifacts).

### 3.1 Tracked Artifact Boundaries
1. **Raw Datasets (`data/raw/`):**
   - `data/raw/archive.dvc`: Tracks Kaggle Plant 1 & 2 generation and weather files (4 CSVs, 11.2 MB, md5: `0d587d78d2ddaa04c1660519dd132000.dir`).
   - `data/raw/unisolar.dvc`: Tracks UNISOLAR Campus 1 multi-site telemetry files (4 CSVs, 106.4 MB, md5: `69d5505ecf6616e349fc43d20803d995.dir`).
2. **Reproducible Processed Data Pipeline (`dvc.yaml` & `dvc.lock`):**
   - Stage `prepare_phase3_data`: Executes `python src/prepare_phase3_data.py`.
   - Dependencies: `src/prepare_phase3_data.py`, `data/raw/archive`, `data/raw/unisolar`.
   - Outputs: 18 processed CSV files (~68.0 MB) spanning Full UNISOLAR Cohort (`target_dataset.csv`, `train.csv`, `validation.csv`, `test.csv`, `features.csv`, etc.), Peer Cohort, and Kaggle Benchmark.
   - *Metadata Boundary:* The 3 `preprocessing_metadata.json` files are explicitly retained under Git tracking for direct diffability and are excluded from DVC stage outputs.
3. **Phase 5 Frozen Model Artifacts (`models/phase5/`):**
   - 8 serialized scikit-learn models (`.joblib`) totaling 52.7 MB are tracked individually via `.joblib.dvc` pointer files:
     * Full Cohort: `models/phase5/full_cohort/tuned_elastic_net.joblib.dvc`, `tuned_extra_trees.joblib.dvc`
     * Peer Cohort: `models/phase5/peer_cohort/tuned_elastic_net.joblib.dvc`, `tuned_extra_trees.joblib.dvc`
     * Final Retrained Models: `models/phase5/final/full_cohort/final_elastic_net.joblib.dvc`, `final_extra_trees.joblib.dvc`
     * Final Retrained Models: `models/phase5/final/peer_cohort/final_elastic_net.joblib.dvc`, `final_extra_trees.joblib.dvc`
   - *Model Governance Boundary:* `models/phase5/final_model_metadata.json` remains tracked by Git.

### 3.2 Remote Registry & Operations
DVC artifacts are hosted on DagsHub S3 (`https://dagshub.com/pavanpavan1138h-cpu/SolarSelect.s3`).

- **Retrieve Artifacts:**
  ```bash
  dvc pull
  ```
  Downloads all raw datasets, processed matrices, and model weights required to run inference or retraining.
- **Inspect Workspace & Remote State:**
  ```bash
  dvc status       # Checks local working tree against local DVC cache
  dvc status -c    # Checks local cache against remote DagsHub S3 storage
  ```
- **Reproduce Pipeline Deterministically:**
  ```bash
  dvc repro prepare_phase3_data
  ```
  Recomputes processed features if and only if code (`prepare_phase3_data.py`) or raw data dependencies change.
- **Synchronize Remote Cache:**
  ```bash
  dvc push
  ```
  Pushes new local cache entries to the remote repository.

### 3.3 Separation of Concerns: DVC vs. MLflow
- **DVC (Data & Binary Artifact Storage):** Canonical authority for large raw datasets (`archive`, `unisolar`), reproducible feature pipelines (`prepare_phase3_data`), and immutable serialized model weights (`models/phase5/**/*.joblib`).
- **MLflow (Experiment Tracking & Model Registry):** Authoritative registry for experiment evaluation runs, hyperparameter lineage, performance metrics, model signatures, and production lifecycle aliasing. Derives registered model packages from DVC-managed binaries.

### 3.4 MLflow Tracking & Model Registry Architecture
SolarSelect integrates MLflow 3.18.0 using a local SQLite backend:
- **Tracking & Registry URI:** `sqlite:///mlflow.db` (enforces atomic relational locking and gitignored persistence).
- **Dedicated Experiment:** `SolarSelect-Phase5-Evaluation` (Experiment ID `2`), isolating the 10 UNISOLAR held-out test evaluation benchmarks from legacy Kaggle plant generation runs in Experiment `1` (`SolarSelect-Forecasting`, preserved intact).
- **Provenance Tagging:** All evaluation runs carry `source=historical_evaluation`, `phase=Phase 5`, `evaluation_split=test`, and direct DVC lineage hashes (`dvc_model_md5`, `dvc_pointer_file`).
- **Model Registry & Aliases:**
  * `SolarSelect-Yield-PeerCohort` (Version 1): Assigned alias `@champion` (Primary ExtraTrees model accepted for rooftop solar panel recommendation).
  * `SolarSelect-Yield-FullCohort` (Version 1): Assigned alias `@campus-tracking-conditional` (ElasticNet model strictly conditioned on macro campus tracking; prohibited for single roofs due to Site 19/24 anomalies).
- **Idempotent Registration:** Managed via [`src/mlops/register_phase5_mlflow.py`](../../src/mlops/register_phase5_mlflow.py), supporting dry-run validation (`--dry-run`).
- **Academic Evaluation Visualizations:** Managed via [`src/mlops/log_phase5_visualizations.py`](../../src/mlops/log_phase5_visualizations.py). Generates and attaches 300 DPI evaluation figures directly as artifacts to the primary production runs (`4b451f68e1c04de49875b095a4defd40` and `9aad1c6a87414b9ca4277d777d9ea8f1`) without duplicate runs or retraining:
  * `visualizations/actual_vs_predicted.png`: Calibration scatter with $y=x$ reference line, documented test metrics box, and Site 19/24 anomaly callout for Full Cohort.
  * `visualizations/residual_diagnostics.png`: Dual-panel diagnostics ($e = \text{Actual} - \text{Predicted}$) including residual error density distribution and residual vs. predicted scatter.
  * `visualizations/feature_importance.png` / `visualizations/feature_coefficients.png`: Peer ExtraTrees top 15 MDI importances cross-referenced with Phase 4 permutation drop; Full ElasticNet top 15 standardized coefficients with explicit non-causal interpretation warning.
  * `visualizations/site_wise_performance.png`: Multi-site MAE and tracking bias breakdown across 22 peer sites / all 24 full cohort sites (highlighting Sites 19 & 24).
  * `visualizations/cohort_model_comparison.png`: Consolidated 3-panel benchmark (MAE, RMSE, $R^2$) across all 10 Phase 5 model formulations.
  * Dry-run validation supported via `--dry-run` and optional local export via `--output-dir <path>`.

---

## 4. Authoritative Verification Audit Trail (`log.txt`)

Every execution session in the SolarSelect project lifecycle is recorded sequentially in the root audit log: [`log.txt`](../../log.txt).
- Each entry records: UTC/local timestamp, session number, user request, technical actions taken, empirical findings, metric outputs, and formal status handoffs.
- No historical entries in `log.txt` are ever overwritten or redacted.

