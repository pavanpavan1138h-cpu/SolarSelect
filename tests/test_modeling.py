import numpy as np
import pandas as pd

from src.solarselect.modeling.data import FEATURE_SETS, add_features
from src.solarselect.modeling.metrics import regression_metrics, safe_mape
from src.solarselect.modeling.models import HourOfDayMean, Persistence


def _series(n=200):
    idx = pd.date_range("2020-05-15", periods=n, freq="15min")
    r = np.random.default_rng(0)
    return pd.DataFrame({"AC_POWER": r.random(n) * 1e4, "DC_POWER": r.random(n) * 1e4,
                         "AMBIENT_TEMPERATURE": 25.0, "MODULE_TEMPERATURE": 30.0,
                         "IRRADIATION": r.random(n)}, index=idx)


def test_metrics_perfect_and_bias():
    y = np.array([0., 1000., 2000., 4000.])
    m = regression_metrics(y, y)
    assert m["mae"] == 0 and m["rmse"] == 0 and m["r2"] == 1 and m["bias"] == 0
    assert regression_metrics(y, y + 10)["bias"] == 10  # over-forecast is positive


def test_safe_mape_ignores_night():
    y, p = np.array([0., 0., 2000.]), np.array([5., 0., 1000.])
    assert safe_mape(y, p, 1000.0) == 50.0
    assert np.isnan(safe_mape([0., 0.], [1., 1.], 1000.0))


def test_legit_feature_sets_have_no_future_columns():
    for name, cols in FEATURE_SETS.items():
        has_leak = any(c.startswith("LEAK_") for c in cols)
        assert has_leak == (name == "leaky"), name


def test_lags_use_only_past():
    df = _series()
    f = add_features(df)
    assert np.isnan(f["ac_lag1"].iloc[0])
    assert f["ac_lag1"].iloc[5] == df["AC_POWER"].iloc[4]
    assert f["ac_lag4"].iloc[10] == df["AC_POWER"].iloc[6]
    # changing a FUTURE value must not change any legitimate feature at t
    df2 = df.copy(); df2.iloc[100:, df2.columns.get_loc("AC_POWER")] += 999
    f2 = add_features(df2)
    legit = FEATURE_SETS["forecast"]
    pd.testing.assert_frame_equal(f[legit].iloc[:100], f2[legit].iloc[:100])


def test_persistence_and_hod_mean():
    X = add_features(_series(192))  # two days
    y = pd.Series(np.arange(192, dtype=float))
    assert (Persistence().fit(X, y).predict(X) == X["AC_POWER"].to_numpy()).all()
    h = HourOfDayMean().fit(X, y)
    p = h.predict(X)
    assert np.isclose(p[0], (y[0] + y[96]) / 2) and np.isclose(p[0], p[96])
