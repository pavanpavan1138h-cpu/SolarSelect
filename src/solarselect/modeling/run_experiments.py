"""Phase 1 baselines + model comparison + cross-plant evaluation, logged to MLflow.

Usage (from repo root):
    python -m src.solarselect.modeling.run_experiments
Outputs: reports/model_comparison.csv, reports/model_comparison.md, reports/figures/*.png,
         mlflow.db (SQLite MLflow store; `mlflow ui --backend-store-uri sqlite:///mlflow.db`).
"""
from __future__ import annotations

import hashlib
import itertools
import json
import subprocess
import sys
from pathlib import Path

import mlflow
import numpy as np
import pandas as pd
import yaml

from .data import FEATURE_SETS, TARGET, load_plant
from .metrics import regression_metrics
from .models import HourOfDayMean, Persistence, make_model

ROOT = Path(__file__).resolve().parents[3]
PLANTS = ("plant1", "plant2")


def _grid(d: dict):
    keys = list(d)
    for vals in itertools.product(*(d[k] for k in keys)):
        yield dict(zip(keys, vals))


def _data_hash(root: Path, split_dir: str) -> str:
    h = hashlib.sha256()
    files = sorted((root / "data/processed" / split_dir).glob("*.csv")) + \
        sorted((root / "data/interim").glob("*_forecasting_dataset.csv"))
    for f in files:
        h.update(f.name.encode()); h.update(f.read_bytes())
    return h.hexdigest()[:16]


def _git_sha(root: Path) -> str:
    try:
        return subprocess.check_output(["git", "-C", str(root), "rev-parse", "--short", "HEAD"],
                                       text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return "unknown"


def _fit_predict(name, params, cols, tr, targets: dict):
    m = make_model(name, **params) if name not in ("persistence", "hod_mean") else \
        (Persistence() if name == "persistence" else HourOfDayMean())
    m.fit(tr[cols], tr[TARGET])
    return m, {k: m.predict(v[cols]) for k, v in targets.items()}


def main():
    cfg = yaml.safe_load((ROOT / "params.yaml").read_text())["modeling"]
    seed, split_dir, mape_min = cfg["seed"], cfg["split_dir"], cfg["min_actual_for_mape_w"]
    np.random.seed(seed)
    data = {p: load_plant(ROOT, p, split_dir) for p in PLANTS}
    dhash, sha = _data_hash(ROOT, split_dir), _git_sha(ROOT)

    mlflow.set_tracking_uri(f"sqlite:///{ROOT / 'mlflow.db'}")
    mlflow.set_experiment(cfg["mlflow_experiment"])
    rows = []

    def log(run_name, plant_train, plant_test, model, fset, params, tag_stage, preds_val, preds_test, extra=None):
        mv = regression_metrics(data[plant_train]["validation"][TARGET], preds_val,
                                data[plant_train]["validation"]["is_day"], mape_min)
        te = data[plant_test]["test"]
        mt = regression_metrics(te[TARGET], preds_test, te["is_day"], mape_min)
        rec = dict(run=run_name, train_plant=plant_train, test_plant=plant_test,
                   protocol="in_plant" if plant_train == plant_test else "cross_plant",
                   model=model, feature_set=fset, params=json.dumps(params, default=str), stage=tag_stage,
                   **{f"val_{k}": v for k, v in mv.items()}, **{f"test_{k}": v for k, v in mt.items()})
        if extra:
            rec.update(extra)
        rows.append(rec)
        with mlflow.start_run(run_name=run_name):
            mlflow.set_tags({"stage": tag_stage, "protocol": rec["protocol"], "model": model,
                             "feature_set": fset, "train_plant": plant_train, "test_plant": plant_test,
                             "git_sha": sha, "data_hash": dhash, "split_dir": split_dir, "owner": "person3"})
            mlflow.log_params({"model": model, "feature_set": fset, "seed": seed,
                               "n_features": len(FEATURE_SETS[fset]), **{f"hp_{k}": v for k, v in params.items()}})
            mlflow.log_metrics({k: v for k, v in rec.items()
                                if k.startswith(("val_", "test_")) and isinstance(v, float) and np.isfinite(v)})
        return rec

    best = {}  # (plant, model) -> (params, fset, model_obj)
    preds_store = {}

    for plant in PLANTS:
        tr, va, te = (data[plant][s] for s in ("train", "validation", "test"))

        # 1. baselines
        for name, fset in (("persistence", "nowcast"), ("hod_mean", "nowcast")):
            cols = FEATURE_SETS[fset]
            _, pr = _fit_predict(name, {}, cols, tr, {"val": va, "test": te})
            log(f"{plant}-{name}", plant, plant, name, fset, {}, "baseline", pr["val"], pr["test"])
            preds_store[(plant, name)] = pr["test"]

        # 2. tuned models on 'forecast' features (selection on validation MAE only)
        for name in ("ridge", "random_forest", "xgboost", "lightgbm"):
            cols = FEATURE_SETS["forecast"]
            cands = []
            for hp in _grid(cfg[name]):
                m, pr = _fit_predict(name, {**hp, "seed": seed} if name != "ridge" else dict(hp), cols, tr, {"val": va})
                mae = float(np.mean(np.abs(pr["val"] - va[TARGET])))
                cands.append((mae, hp))
            hp = min(cands, key=lambda c: c[0])[1]
            m, pr = _fit_predict(name, {**hp, "seed": seed} if name != "ridge" else dict(hp), cols, tr,
                                 {"val": va, "test": te})
            log(f"{plant}-{name}-forecast", plant, plant, name, "forecast", hp, "model", pr["val"], pr["test"],
                {"n_tuning_candidates": len(cands)})
            best[(plant, name)] = hp
            preds_store[(plant, name)] = pr["test"]

        # 3. feature ablations with the tuned XGBoost
        hp = best[(plant, "xgboost")]
        for fset in ("nowcast", "forecast_no_weather", "leaky"):
            _, pr = _fit_predict("xgboost", {**hp, "seed": seed}, FEATURE_SETS[fset], tr, {"val": va, "test": te})
            log(f"{plant}-xgboost-{fset}", plant, plant, "xgboost", fset, hp, "ablation", pr["val"], pr["test"])
            if fset == "leaky":
                preds_store[(plant, "xgboost_leaky")] = pr["test"]

    # 4. cross-plant: train on plant A train, evaluate on plant B test (hyperparameters from plant A).
    # Main runs use forecast_no_dc; ridge/xgboost with DC_POWER are kept as evidence of the DC-scale problem.
    for a, b in (("plant1", "plant2"), ("plant2", "plant1")):
        tr = data[a]["train"]
        plan = [(n, "nowcast") for n in ("persistence", "hod_mean")] + \
               [(n, "forecast_no_dc") for n in ("ridge", "random_forest", "xgboost", "lightgbm")] + \
               [(n, "forecast") for n in ("ridge", "xgboost")]
        for name, fset in plan:
            hp = best.get((a, name), {})
            hp_fit = {**hp, "seed": seed} if name not in ("ridge", "persistence", "hod_mean") else dict(hp)
            _, pr = _fit_predict(name, hp_fit, FEATURE_SETS[fset], tr,
                                 {"val": data[a]["validation"], "test": data[b]["test"]})
            log(f"{a}-to-{b}-{name}-{fset}", a, b, name, fset, hp, "cross_plant", pr["val"], pr["test"])
            preds_store[(f"{a}->{b}", name, fset)] = pr["test"]

    # 5. day-block bootstrap: is each model's in-plant test MAE really better than persistence?
    boot = []
    rng = np.random.default_rng(seed)
    for plant in PLANTS:
        te = data[plant]["test"]; day = te["TARGET_TIMESTAMP"].dt.date.to_numpy()
        days = np.unique(day); y = te[TARGET].to_numpy()
        base_err = np.abs(preds_store[(plant, "persistence")] - y)
        for m in ("hod_mean", "ridge", "random_forest", "xgboost", "lightgbm"):
            d = base_err - np.abs(preds_store[(plant, m)] - y)  # >0: model better than persistence
            per_day = np.array([d[day == k].sum() for k in days]); n_day = np.array([(day == k).sum() for k in days])
            stats = []
            for _ in range(2000):
                idx = rng.integers(0, len(days), len(days))
                stats.append(per_day[idx].sum() / n_day[idx].sum())
            lo, hi = np.percentile(stats, [2.5, 97.5])
            boot.append(dict(plant=plant, model=m, mae_gain_vs_persistence=float(d.mean()),
                             ci95_lo=float(lo), ci95_hi=float(hi), n_test_days=len(days)))
    pd.DataFrame(boot).to_csv(ROOT / "reports" / "bootstrap_vs_persistence.csv", index=False)
    print(pd.DataFrame(boot).round(1).to_string(index=False))

    res = pd.DataFrame(rows)
    out = ROOT / "reports"; (out / "figures").mkdir(parents=True, exist_ok=True)
    res.to_csv(out / "model_comparison.csv", index=False)
    _write_md(res, out / "model_comparison.md", dhash, sha, split_dir)
    _plots(res, data, preds_store, out / "figures")
    print(res[["run", "protocol", "model", "feature_set", "test_mae", "test_rmse", "test_r2",
               "test_day_mae", "test_bias"]].round(3).to_string(index=False))
    print(f"\n{len(res)} MLflow runs | data_hash={dhash} git_sha={sha}")


def _write_md(res, path, dhash, sha, split_dir):
    cols = ["model", "feature_set", "test_mae", "test_rmse", "test_r2", "test_safe_mape",
            "test_day_mae", "test_day_rmse", "test_bias", "val_mae"]
    lines = [f"# Model comparison (auto-generated)\n",
             f"data_hash `{dhash}` · git `{sha}` · split `{split_dir}` · units: W (plant-level AC power)\n"]
    for title, q in (("In-plant, chronological split (train → test, same plant)", res.protocol == "in_plant"),
                     ("Cross-plant (train plant A → test plant B)", res.protocol == "cross_plant")):
        for plant in PLANTS:
            sub = res[q & (res.test_plant == plant)]
            if sub.empty:
                continue
            tag = f" — test on {plant}" + ("" if title.startswith("In") else f" (trained on {sub.train_plant.iloc[0]})")
            lines += [f"\n## {title}{tag}\n", sub[cols].round(3).to_markdown(index=False)]
    path.write_text("\n".join(lines) + "\n")


def _plots(res, data, preds, figdir):
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    ip = res[(res.protocol == "in_plant") & (res.stage != "ablation")]
    fig, axs = plt.subplots(1, 2, figsize=(11, 4), sharey=True)
    for ax, plant in zip(axs, PLANTS):
        s = ip[ip.test_plant == plant].sort_values("test_mae")
        ax.barh(s.model, s.test_mae / 1000); ax.invert_yaxis()
        ax.set_title(f"{plant}: test MAE (kW)"); ax.set_xlabel("MAE (kW)")
    fig.tight_layout(); fig.savefig(figdir / "model_comparison_mae.png", dpi=130); plt.close(fig)

    fig, axs = plt.subplots(2, 1, figsize=(11, 7))
    for ax, plant in zip(axs, PLANTS):
        te = data[plant]["test"]
        ax.plot(te["TARGET_TIMESTAMP"], te[TARGET] / 1000, "k", lw=1.2, label="actual")
        for m in ("persistence", "hod_mean", "xgboost"):
            ax.plot(te["TARGET_TIMESTAMP"], preds[(plant, m)] / 1000, lw=0.9, label=m)
        ax.set_title(f"{plant} test period: AC power 15 min ahead"); ax.set_ylabel("kW"); ax.legend(ncol=4, fontsize=8)
    fig.tight_layout(); fig.savefig(figdir / "test_predictions.png", dpi=130); plt.close(fig)

    ab = res[(res.model == "xgboost") & (res.protocol == "in_plant")]
    fig, ax = plt.subplots(figsize=(8, 4))
    order = ["forecast_no_weather", "nowcast", "forecast", "leaky"]
    w = 0.38
    for i, plant in enumerate(PLANTS):
        s = ab[ab.test_plant == plant].set_index("feature_set").reindex(order)
        ax.bar(np.arange(len(order)) + i * w, s.test_mae / 1000, w, label=plant)
    ax.set_xticks(np.arange(len(order)) + w / 2); ax.set_xticklabels(order, rotation=15)
    ax.set_ylabel("test MAE (kW)"); ax.set_title("XGBoost feature ablation (leaky = illegitimate future weather)")
    ax.legend(); fig.tight_layout(); fig.savefig(figdir / "feature_ablation.png", dpi=130); plt.close(fig)


if __name__ == "__main__":
    main()
