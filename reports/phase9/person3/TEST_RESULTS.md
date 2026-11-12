# Person 3 test results (this session, fresh runs)

| Command | Result |
|---|---|
| `python -m pytest tests/phase9/person3 -q` | 62 passed |
| `python -m pytest -q` (full repo incl. monitoring and Person 4 DevOps tests) | 470 passed, 0 failed — see environment-dependent failures in MODEL_QA_FINAL_REPORT.md |

Baseline before adding any tests: 358 passed / 4 failed with missing plotly+seaborn; 360 passed / 2 failed once installed.
Environment: Python 3.13.16 venv, versions per `requirements.txt` (starlette not pinned → 1.10.0).
Test files: `test_model_artifact_and_contract.py`, `test_reproducibility_and_parity.py`, `test_input_robustness.py`, `test_heldout_quality.py`.
