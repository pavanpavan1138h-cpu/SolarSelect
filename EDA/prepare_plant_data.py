
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw" / "archive"
OUTPUT_DIR = PROJECT_ROOT / "data" / "interim"

FILES = {
    "plant1": ("Plant_1_Generation_Data.csv", "%d-%m-%Y %H:%M"),
    "plant2": ("Plant_2_Generation_Data.csv", "%Y-%m-%d %H:%M:%S"),
}

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

for plant, (filename, date_format) in FILES.items():
    df = pd.read_csv(RAW_DIR / filename)

    df["DATE_TIME"] = pd.to_datetime(
        df["DATE_TIME"], format=date_format
    )

    expected_sources = df["SOURCE_KEY"].nunique()

    result = (
        df.groupby(["PLANT_ID", "DATE_TIME"], as_index=False)
        .agg(
            AC_POWER=("AC_POWER", "sum"),
            DC_POWER=("DC_POWER", "sum"),
            source_count=("SOURCE_KEY", "nunique"),
        )
        .sort_values("DATE_TIME")
        .reset_index(drop=True)
    )

    result["expected_sources"] = expected_sources
    result["complete_coverage"] = (
        result["source_count"] == expected_sources
    )

    output_path = OUTPUT_DIR / f"{plant}_generation_coverage.csv"
    result.to_csv(output_path, index=False)

    print(f"\n{plant}")
    print("Expected sources:", expected_sources)
    print("Total timestamps:", len(result))
    print("Complete timestamps:", result["complete_coverage"].sum())
    print("Incomplete timestamps:", (~result["complete_coverage"]).sum())
    print("Saved:", output_path)
