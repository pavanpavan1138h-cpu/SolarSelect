
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw" / "archive"
INTERIM_DIR = PROJECT_ROOT / "data" / "interim"

CONFIG = {
    "plant1": {
        "weather_file": "Plant_1_Weather_Sensor_Data.csv",
        "date_format": "%Y-%m-%d %H:%M:%S",
    },
    "plant2": {
        "weather_file": "Plant_2_Weather_Sensor_Data.csv",
        "date_format": "%Y-%m-%d %H:%M:%S",
    },
}

for plant, config in CONFIG.items():
    power = pd.read_csv(
        INTERIM_DIR / f"{plant}_generation_coverage.csv",
        parse_dates=["DATE_TIME"],
    )

    weather = pd.read_csv(
        RAW_DIR / config["weather_file"]
    )

    weather["DATE_TIME"] = pd.to_datetime(
        weather["DATE_TIME"],
        format=config["date_format"],
    )

    # Weather is recorded at plant level for each timestamp.
    # Confirm one row per timestamp before merging.
    if weather["DATE_TIME"].duplicated().any():
        raise ValueError(
            f"{plant}: duplicate weather timestamps found"
        )

    weather = weather[
        [
            "DATE_TIME",
            "AMBIENT_TEMPERATURE",
            "MODULE_TEMPERATURE",
            "IRRADIATION",
        ]
    ]

    merged = power.merge(
        weather,
        on="DATE_TIME",
        how="left",
        validate="one_to_one",
        indicator=True,
    )

    unmatched = (merged["_merge"] != "both").sum()
    merged = merged.drop(columns="_merge")

    output = INTERIM_DIR / f"{plant}_power_weather.csv"
    merged.to_csv(output, index=False)

    print(f"\n{plant}")
    print("Power timestamps:", len(power))
    print("Rows without weather match:", unmatched)
    print("Output:", output)
