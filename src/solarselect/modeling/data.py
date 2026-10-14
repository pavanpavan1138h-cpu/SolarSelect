"""Load SolarSelect splits and build model features (nowcast / forecast / leaky).

Lag/rolling features are computed on each plant's full, time-ordered series
using only PAST values, then joined onto the split rows by DATE_TIME. A split
row may therefore use history from before its split boundary; that is legal
(it is past information at prediction time) and no future value is used.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

TARGET = "TARGET_AC_POWER_15MIN"
SPLITS = ("train", "validation", "test")
DAYTIME_IRRADIATION = 0.01  # kW/m2 at prediction time; input-side, not target-side


def _full_series(root: Path, plant: str) -> pd.DataFrame:
    df = pd.read_csv(root / "data/interim" / f"{plant}_forecasting_dataset.csv", parse_dates=["DATE_TIME"])
    df = df.sort_values("DATE_TIME").set_index("DATE_TIME")
    # Re-index to a strict 15-min grid so shift(k) means exactly k*15 minutes.
    # Gaps become NaN (honest missingness); tree models handle NaN, Ridge gets imputed.
    grid = pd.date_range(df.index.min(), df.index.max(), freq="15min")
    df = df[~df.index.duplicated()].reindex(grid)
    df.index.name = "DATE_TIME"
    return df


def add_features(df: pd.DataFrame) -> pd.DataFrame:
    """df: strict-15-min series with AC_POWER, DC_POWER, weather columns."""
    out = pd.DataFrame(index=df.index)
    ac, irr = df["AC_POWER"], df["IRRADIATION"]
    mod = df.index.hour * 60 + df.index.minute
    # time features of the *prediction* time t
    out["tod_sin"] = np.sin(2 * np.pi * mod / 1440)
    out["tod_cos"] = np.cos(2 * np.pi * mod / 1440)
    out["doy"] = df.index.dayofyear
    # current observations (known at t)
    for c in ("AC_POWER", "DC_POWER", "AMBIENT_TEMPERATURE", "MODULE_TEMPERATURE", "IRRADIATION"):
        out[c] = df[c]
    # past-only lags / rolling
    for k in (1, 2, 4, 96):  # 15m, 30m, 1h, 24h
        out[f"ac_lag{k}"] = ac.shift(k)
    out["irr_lag1"] = irr.shift(1)
    out["ac_roll4_mean"] = ac.rolling(4, min_periods=2).mean()
    out["irr_roll4_mean"] = irr.rolling(4, min_periods=2).mean()
    # LEAKY (ablation only): observed weather at t+15, i.e. not available at t
    out["LEAK_irr_future"] = irr.shift(-1)
    out["LEAK_modtemp_future"] = df["MODULE_TEMPERATURE"].shift(-1)
    return out


FEATURE_SETS = {
    # observations at t + calendar only
    "nowcast": ["tod_sin", "tod_cos", "doy", "AC_POWER", "DC_POWER",
                "AMBIENT_TEMPERATURE", "MODULE_TEMPERATURE", "IRRADIATION"],
    # nowcast + history (what a deployable 15-min-ahead model may use)
    "forecast": ["tod_sin", "tod_cos", "doy", "AC_POWER", "DC_POWER",
                 "AMBIENT_TEMPERATURE", "MODULE_TEMPERATURE", "IRRADIATION",
                 "ac_lag1", "ac_lag2", "ac_lag4", "ac_lag96",
                 "irr_lag1", "ac_roll4_mean", "irr_roll4_mean"],
    # forecast minus DC_POWER: Plant 1 DC_POWER is ~10x its AC_POWER but Plant 2's is ~1x,
    # so DC is not comparable across plants (needed for cross-plant transfer)
    "forecast_no_dc": ["tod_sin", "tod_cos", "doy", "AC_POWER",
                       "AMBIENT_TEMPERATURE", "MODULE_TEMPERATURE", "IRRADIATION",
                       "ac_lag1", "ac_lag2", "ac_lag4", "ac_lag96",
                       "irr_lag1", "ac_roll4_mean", "irr_roll4_mean"],
    "forecast_no_weather": ["tod_sin", "tod_cos", "doy", "AC_POWER", "DC_POWER",
                            "ac_lag1", "ac_lag2", "ac_lag4", "ac_lag96", "ac_roll4_mean"],
    "forecast_no_lags": None,  # == nowcast; kept as alias below
    # forecast + future observed weather: NOT legitimate, quantifies leakage
    "leaky": ["tod_sin", "tod_cos", "doy", "AC_POWER", "DC_POWER",
              "AMBIENT_TEMPERATURE", "MODULE_TEMPERATURE", "IRRADIATION",
              "ac_lag1", "ac_lag2", "ac_lag4", "ac_lag96",
              "irr_lag1", "ac_roll4_mean", "irr_roll4_mean",
              "LEAK_irr_future", "LEAK_modtemp_future"],
}
FEATURE_SETS["forecast_no_lags"] = FEATURE_SETS["nowcast"]


def load_plant(root: Path, plant: str, split_dir: str = "complete_coverage") -> dict[str, pd.DataFrame]:
    """Return {split: frame} with features, TARGET, TARGET_TIMESTAMP, is_day."""
    feats = add_features(_full_series(root, plant))
    res = {}
    for s in SPLITS:
        base = pd.read_csv(root / "data/processed" / split_dir / f"{plant}_{s}.csv",
                           parse_dates=["DATE_TIME", "TARGET_TIMESTAMP"])
        base = base[["DATE_TIME", "TARGET_TIMESTAMP", TARGET]].dropna(subset=[TARGET])
        d = base.merge(feats.reset_index(), on="DATE_TIME", how="left").sort_values("DATE_TIME")
        d["is_day"] = d["IRRADIATION"].fillna(0) > DAYTIME_IRRADIATION
        d["plant"] = plant
        res[s] = d.reset_index(drop=True)
    return res
