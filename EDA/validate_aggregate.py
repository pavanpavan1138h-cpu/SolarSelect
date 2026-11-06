
from pathlib import Path

import pandas as pd


# Project paths
PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw" / "archive"
OUTPUT_DIR = PROJECT_ROOT / "data" / "interim"


FILES = {
    "plant1_generation": "Plant_1_Generation_Data.csv",
    "plant1_weather": "Plant_1_Weather_Sensor_Data.csv",
    "plant2_generation": "Plant_2_Generation_Data.csv",
    "plant2_weather": "Plant_2_Weather_Sensor_Data.csv",
}

DATE_FORMATS = {
    "plant1_generation": "%d-%m-%Y %H:%M",
    "plant1_weather": "%Y-%m-%d %H:%M:%S",
    "plant2_generation": "%Y-%m-%d %H:%M:%S",
    "plant2_weather": "%Y-%m-%d %H:%M:%S",
}

GENERATION_COLUMNS = [
    "DATE_TIME",
    "PLANT_ID",
    "SOURCE_KEY",
    "DC_POWER",
    "AC_POWER",
    "DAILY_YIELD",
    "TOTAL_YIELD",
]

WEATHER_COLUMNS = [
    "DATE_TIME",
    "PLANT_ID",
    "SOURCE_KEY",
    "AMBIENT_TEMPERATURE",
    "MODULE_TEMPERATURE",
    "IRRADIATION",
]


def load_and_validate(name, filename):
    """Load a CSV, validate its basic structure, and parse timestamps."""
    path = RAW_DIR / filename

    if not path.is_file():
        raise FileNotFoundError(f"Dataset not found: {path}")

    df = pd.read_csv(path)

    required_columns = (
        GENERATION_COLUMNS
        if "generation" in name
        else WEATHER_COLUMNS
    )

    missing_columns = set(required_columns) - set(df.columns)

    if missing_columns:
        raise ValueError(
            f"{name}: missing required columns "
            f"{sorted(missing_columns)}"
        )

    if df.empty:
        raise ValueError(f"{name}: dataset is empty")

    if df["DATE_TIME"].isna().any():
        raise ValueError(f"{name}: missing timestamps")

    df["DATE_TIME"] = pd.to_datetime(
        df["DATE_TIME"],
        format=DATE_FORMATS[name],
        errors="raise",
    )

    if df.duplicated().any():
        raise ValueError(
            f"{name}: found {df.duplicated().sum()} exact duplicate rows"
        )

    if df["PLANT_ID"].isna().any():
        raise ValueError(f"{name}: missing PLANT_ID values")

    if df["SOURCE_KEY"].isna().any():
        raise ValueError(f"{name}: missing SOURCE_KEY values")

    if "generation" in name:
        numeric_columns = [
            "DC_POWER",
            "AC_POWER",
            "DAILY_YIELD",
            "TOTAL_YIELD",
        ]
    else:
        numeric_columns = [
            "AMBIENT_TEMPERATURE",
            "MODULE_TEMPERATURE",
            "IRRADIATION",
        ]

    for column in numeric_columns:
        df[column] = pd.to_numeric(df[column], errors="raise")

        if df[column].isna().any():
            raise ValueError(
                f"{name}: missing values in {column}"
            )

        if not df[column].map(
            lambda value: pd.notna(value) and abs(value) != float("inf")
        ).all():
            raise ValueError(
                f"{name}: non-finite values in {column}"
            )

    # Basic physical checks: flag invalid values instead of silently
    # deleting observations.
    if "generation" in name:
        for column in ["DC_POWER", "AC_POWER"]:
            if (df[column] < 0).any():
                raise ValueError(
                    f"{name}: negative values found in {column}"
                )
    else:
        if (df["IRRADIATION"] < 0).any():
            raise ValueError(
                f"{name}: negative irradiation values found"
            )

    print(
        f"VALIDATED {name}: "
        f"{len(df):,} rows, "
        f"{df['DATE_TIME'].min()} to {df['DATE_TIME'].max()}"
    )

    return df


def aggregate_generation(df, plant_name):
    """Sum inverter power into one plant-level row per timestamp."""
    result = (
        df.groupby(
            ["PLANT_ID", "DATE_TIME"],
            as_index=False,
        )
        .agg(
            AC_POWER=("AC_POWER", "sum"),
            DC_POWER=("DC_POWER", "sum"),
            inverter_records=("SOURCE_KEY", "nunique"),
        )
        .sort_values("DATE_TIME")
        .reset_index(drop=True)
    )

    print(f"\n{plant_name}")
    print("Plant-level rows:", len(result))
    print("Unique timestamps:", result["DATE_TIME"].nunique())
    print(
        "Inverter records per timestamp:\n",
        result["inverter_records"].value_counts().sort_index(),
    )

    return result


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    datasets = {
        name: load_and_validate(name, filename)
        for name, filename in FILES.items()
    }

    plant1 = aggregate_generation(
        datasets["plant1_generation"], "Plant 1"
    )
    plant2 = aggregate_generation(
        datasets["plant2_generation"], "Plant 2"
    )

    plant1.to_csv(
        OUTPUT_DIR / "plant1_generation.csv", index=False
    )
    plant2.to_csv(
        OUTPUT_DIR / "plant2_generation.csv", index=False
    )

    print("\nValidation and aggregation completed.")
    print("Output directory:", OUTPUT_DIR)


if __name__ == "__main__":
    main()
