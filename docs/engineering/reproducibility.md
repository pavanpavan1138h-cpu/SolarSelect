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

Raw data archives and intermediate datasets are tracked using DVC (`.dvc/`):
- `data/raw/archive.dvc`: Tracks original Kaggle CSV files.
- DVC local and remote storage caches ensure data hashes remain immutable.

---

## 4. Authoritative Verification Audit Trail (`log.txt`)

Every execution session in the SolarSelect project lifecycle is recorded sequentially in the root audit log: [`log.txt`](../../log.txt).
- Each entry records: UTC/local timestamp, session number, user request, technical actions taken, empirical findings, metric outputs, and formal status handoffs.
- No historical entries in `log.txt` are ever overwritten or redacted.

