
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

    if plant == "Plant 1":
        df["DATE_TIME"] = pd.to_datetime(
            df["DATE_TIME"], format="%d-%m-%Y %H:%M"
        )
    else:
        df["DATE_TIME"] = pd.to_datetime(
            df["DATE_TIME"], format="%Y-%m-%d %H:%M:%S"
        )

    expected_sources = df["SOURCE_KEY"].nunique()

    counts = df.groupby("DATE_TIME")["SOURCE_KEY"].nunique()
    incomplete = counts[counts < expected_sources]

    print(f"\n{plant}")
    print("Distinct sources in dataset:", expected_sources)
    print("Incomplete timestamps:", len(incomplete))
    print("\nCounts of records at incomplete timestamps:")
    print(incomplete.value_counts().sort_index())

    print("\nFirst 10 incomplete timestamps:")
    print(incomplete.head(10))

    if not incomplete.empty:
        timestamp = incomplete.index[0]
        observed = set(
            df.loc[df["DATE_TIME"] == timestamp, "SOURCE_KEY"]
        )
        all_sources = set(df["SOURCE_KEY"].unique())
        print("\nExample timestamp:", timestamp)
        print("Missing source IDs:", sorted(all_sources - observed))
