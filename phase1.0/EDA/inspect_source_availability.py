
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw" / "archive"

FILES = {
    "Plant 1": "Plant_1_Generation_Data.csv",
    "Plant 2": "Plant_2_Generation_Data.csv",
}

for plant, filename in FILES.items():
    df = pd.read_csv(RAW_DIR / filename)

    date_format = (
        "%d-%m-%Y %H:%M"
        if plant == "Plant 1"
        else "%Y-%m-%d %H:%M:%S"
    )

    df["DATE_TIME"] = pd.to_datetime(
        df["DATE_TIME"], format=date_format
    )

    print(f"\n{'=' * 50}")
    print(plant, "- SOURCE AVAILABILITY")
    print("=" * 50)

    report = (
        df.groupby("SOURCE_KEY")
        .agg(
            row_count=("DATE_TIME", "size"),
            first_seen=("DATE_TIME", "min"),
            last_seen=("DATE_TIME", "max"),
            unique_timestamps=("DATE_TIME", "nunique"),
        )
        .sort_values("row_count")
    )

    print(report.to_string())

    # Inspect how many source records appear at each timestamp.
    counts = df.groupby("DATE_TIME")["SOURCE_KEY"].nunique()

    print("\nTimestamp coverage summary:")
    print(counts.value_counts().sort_index().to_string())

    # Show the time periods where coverage is below 22.
    incomplete_times = counts[counts < 22].index

    if len(incomplete_times):
        print("\nIncomplete timestamp range:")
        print("First:", incomplete_times.min())
        print("Last: ", incomplete_times.max())
