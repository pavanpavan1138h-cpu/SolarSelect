"""Baselines and sklearn-style model factories."""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, RegressorMixin
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


class Persistence(BaseEstimator, RegressorMixin):
    """y(t+15) = AC_POWER(t). Needs the AC_POWER column."""

    def fit(self, X, y=None):
        return self

    def predict(self, X):
        return np.asarray(X["AC_POWER"], float)


class HourOfDayMean(BaseEstimator, RegressorMixin):
    """y(t+15) = mean training target for the same 15-min slot of day.

    Slot is derived from the prediction-time cyclic features (tod_sin/tod_cos),
    rounded to the nearest 15-min bin, so no timestamp column is required.
    """

    @staticmethod
    def _slot(X):
        ang = np.arctan2(X["tod_sin"], X["tod_cos"]) % (2 * np.pi)
        return np.round(ang / (2 * np.pi) * 96).astype(int) % 96

    def fit(self, X, y):
        s = pd.Series(np.asarray(y, float)).groupby(self._slot(X).to_numpy()).mean()
        self.table_ = s
        self.global_ = float(np.mean(y))
        return self

    def predict(self, X):
        return self._slot(X).map(self.table_).fillna(self.global_).to_numpy()


def make_model(name: str, **p):
    if name == "ridge":
        return make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), Ridge(**p))
    if name == "random_forest":
        return make_pipeline(SimpleImputer(strategy="median"),
                             RandomForestRegressor(random_state=p.pop("seed", 42), n_jobs=-1, **p))
    if name == "xgboost":
        from xgboost import XGBRegressor
        return XGBRegressor(random_state=p.pop("seed", 42), n_jobs=-1, **p)
    if name == "lightgbm":
        from lightgbm import LGBMRegressor
        return LGBMRegressor(random_state=p.pop("seed", 42), n_jobs=-1, verbose=-1, **p)
    raise ValueError(name)
