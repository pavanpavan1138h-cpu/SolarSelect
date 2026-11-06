 
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
INTERIM_DIR = PROJECT_ROOT / "data" / "interim"

for plant in ["plant1", "plant2"]:
    path = INTERIM_DIR / f"{plant}_power_weather.csv"
    df = pd.read_csv(path, parse_dates=["DATE_TIME"])

    df = df.sort_values("DATE_TIME").reset_index(drop=True)

    # Build a timestamp-to-power lookup for exactly 15 minutes ahead.
    future = df[["DATE_TIME", "AC_POWER"]].copy()
    future["DATE_TIME"] = future["DATE_TIME"] - pd.Timedelta(minutes=15)
    future = future.rename(
        columns={"AC_POWER": "TARGET_AC_POWER_15MIN"}
    )

    df = df.merge(
        future,
        on="DATE_TIME",
        how="left",
        validate="one_to_one",
    )

    # Keep only examples with an exact 15-minute future timestamp.
    # Keep incomplete source coverage flagged for now.
    df["TARGET_TIMESTAMP"] = (
        df["DATE_TIME"] + pd.Timedelta(minutes=15)
    )

    existing_times = set(df["DATE_TIME"])
    df["HAS_EXACT_FUTURE_TIMESTAMP"] = (
        df["TARGET_TIMESTAMP"].isin(existing_times)
    )

    output = INTERIM_DIR / f"{plant}_forecasting_dataset.csv"
    df.to_csv(output, index=False)

    print(f"\n{plant}")
    print("Input rows:", len(df))
    print("Exact 15-minute targets:", df["TARGET_AC_POWER_15MIN"].notna().sum())
    print("Rows without target:", df["TARGET_AC_POWER_15MIN"].isna().sum())
    print("Saved:", output)
