# Execution Guide — SolarSelect

This document provides exact, verified CLI commands for reproducing the data preparation, catalogue validation, and notebook execution workflows in SolarSelect.

---

## 1. Running the Automated Data Preprocessing Pipeline

To regenerate all Phase 3 processed datasets (`data/processed/unisolar/` and `data/processed/unisolar/peer_cohort/`) deterministically from raw telemetry:

```bash
# Execute Phase 3 automated preprocessing pipeline from root directory
python3 src/prepare_phase3_data.py
```

### Expected Output Summary:
- Reconciles 8,760 expected annual site-days across 24 documented-$\text{kW}_p$ sites.
- Generates Full Cohort ($N=7,039$) and Peer Cohort ($N=6,456$).
- Produces `train.csv`, `validation.csv`, `test.csv`, `feature_dictionary.csv`, `preprocessing_metadata.json`, and `diagnostic_metadata.csv`.
- Execution runtime: $\approx 15–25\text{ seconds}$.

---

## 2. Running the Panel Catalogue Validator

To execute automated schema, physical dimension, efficiency consistency, and electrical hierarchy validation on the commercial PV catalogue:

```bash
# Validate configs/panels_catalogue.csv against canonical schema
python3 src/validate_panel_catalogue.py
```

### Custom Flags & Arguments:
```bash
python3 src/validate_panel_catalogue.py \
  --csv configs/panels_catalogue.csv \
  --schema configs/panels_catalogue_schema.json \
  --output reports/phase6/catalogue_validation_report.json
```

---

## 3. Recommended Notebook Execution Order

For auditing or reproducing analytical figures and model experiments, execute notebooks in the following strict chronological sequence:

### Phase 1: Data Inspection
1. `notebooks/data_inspection/dataset_inspection_and_source_verification.ipynb`

### Phase 2: Exploratory Data Analysis (EDA 2.0)
2. `notebooks/eda2.0/dataset_quality_and_completeness.ipynb`
3. `notebooks/eda2.0/solar_generation_distributions_and_physical_analysis.ipynb`
4. `notebooks/eda2.0/temporal_seasonal_and_site_analysis.ipynb`
5. `notebooks/eda2.0/feature_relationships_and_target_feasibility.ipynb`
6. `notebooks/eda2.0/consolidated_eda_findings_and_dataset_selection.ipynb`

### Phase 3: Target Definition & Data Preparation
7. `notebooks/phase3/target_definition_and_data_preparation.ipynb`

### Phase 4: Model Development & Benchmarking
8. `notebooks/phase4/baseline_and_model_development.ipynb`

### Phase 5: Model Diagnostics, Blending & Final Evaluation
9. `notebooks/phase5/model_diagnostics_and_improvement_investigation.ipynb`
10. `notebooks/phase5/model_improvement_experiments.ipynb`
11. `notebooks/phase5/final_model_evaluation_and_generalization.ipynb`

### Phase 6: Hardware Catalogue & Validation
12. `notebooks/phase6/panel_catalogue_inventory_and_validation.ipynb`

---

## 4. Headless Execution Command for Quality Assurance

To execute any notebook headless and verify zero runtime errors:
```bash
jupyter nbconvert --to notebook --execute --inplace notebooks/phase6/panel_catalogue_inventory_and_validation.ipynb
```

