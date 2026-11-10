# Environment Setup — SolarSelect

This document details the software prerequisites, operating system compatibility, Python virtual environment configuration, and dependency installation for SolarSelect.

---

## 1. System Requirements

- **Operating System:** macOS (Apple Silicon / Intel), Linux (Ubuntu 20.04+ / Debian 11+), Windows 10/11 (via WSL2 recommended).
- **Python Version:** **Python 3.11** (recommended: 3.11.4 to 3.11.9).
- **Memory (RAM):** Minimum 8 GB (16 GB recommended for ExtraTrees ensemble training).
- **Disk Space:** Minimum 5 GB free space for raw telemetry data, processed CSVs, and model artifacts.

---

## 2. Step-by-Step Installation

### Step A: Clone Repository
```bash
git clone https://github.com/your-org/SolarSelect.git
cd SolarSelect
```

### Step B: Create & Activate Virtual Environment
```bash
# Using standard venv
python3.11 -m venv .venv

# Activate on macOS / Linux:
source .venv/bin/activate

# Activate on Windows (Command Prompt):
# .venv\Scripts\activate.bat
```

### Step C: Upgrade Core Packaging Tools
```bash
python -m pip install --upgrade pip setuptools wheel
```

### Step D: Install Authoritative Dependencies
```bash
pip install -r requirements.txt
```

---

## 3. Authoritative Core Dependencies (`requirements.txt`)

| Package | Version Pin | Core Role in SolarSelect |
|---|---|---|
| `python` | `~=3.11.0` | Runtime environment |
| `numpy` | `>=1.24.0, <2.0.0` | Vectorized numerical computing and linear algebra |
| `pandas` | `>=2.0.0, <2.3.0` | Tabular data manipulation, time series indexing, CSV I/O |
| `scipy` | `>=1.10.0` | Statistical tests (Welch, Wilcoxon) and astronomical math |
| `scikit-learn` | `>=1.3.0, <1.5.0` | Classical ML models (ElasticNet, ExtraTrees, Random Forest), metrics |
| `lightgbm` | `>=4.0.0` | Gradient boosted decision trees benchmarking |
| `matplotlib` | `>=3.7.0` | Publication-grade analytical figure generation |
| `seaborn` | `>=0.12.0` | Statistical distribution plotting and residual heatmaps |
| `joblib` | `>=1.3.0` | High-efficiency model serialization and parallel processing |
| `jupyter` | `>=1.0.0` | Interactive notebook execution and reporting |
| `nbconvert` | `>=7.0.0` | Automated headless notebook execution and quality assurance |
| `dvc` | `>=3.0.0` | Data Version Control and pipeline lineage tracking |
| `mlflow` | `>=2.8.0` | Experiment tracking and model registry infrastructure |

---

## 4. Verification of Environment Integrity

Run the following one-line test to verify that the environment is fully operational:
```bash
python3 -c "
import numpy as np, pandas as pd, sklearn, joblib, matplotlib
print(f'NumPy: {np.__version__} | Pandas: {pd.__version__} | Scikit-Learn: {sklearn.__version__}')
print('SolarSelect Python 3.11 environment is operational.')
"
```

