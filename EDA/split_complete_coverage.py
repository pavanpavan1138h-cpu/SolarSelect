
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
INTERIM_DIR = PROJECT_ROOT / "data" / "interim"
OUTPUT_DIR = PROJECT_ROOT / "data" / "processed" / "complete_coverage"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

for plant in ["plant1", "plant2"]:
    path = INTERIM_DIR / f"{plant}_forecasting_dataset.csv"
    df = pd.read_csv(
        path,
        parse_dates=["DATE_TIME", "TARGET_TIMESTAMP"],
    )
    df = df.sort_values("DATE_TIME").reset_index(drop=True)

    # Check coverage at both the input time and target time.
    coverage = df.set_index("DATE_TIME")["complete_coverage"]
    future_coverage = (
        df["DATE_TIME"] + pd.Timedelta(minutes=15)
    ).map(coverage)

    df["TARGET_COMPLETE_COVERAGE"] = (
        future_coverage.fillna(False).astype(bool)
    )

    eligible = df[
        df["TARGET_AC_POWER_15MIN"].notna()
        & df["complete_coverage"].eq(True)
        & df["TARGET_COMPLETE_COVERAGE"]
    ].copy()

    eligible = eligible.sort_values("DATE_TIME").reset_index(drop=True)

    n = len(eligible)
    train_end = int(n * 0.70)
    val_end = int(n * 0.85)

    train = eligible.iloc[:train_end].copy()
    validation = eligible.iloc[train_end:val_end].copy()
    test = eligible.iloc[val_end:].copy()

    # Prevent a target from crossing a split's time boundary.
    if not train.empty:
        train = train[
            train["TARGET_TIMESTAMP"] <= train["DATE_TIME"].max()
        ]

    if not validation.empty:
        validation = validation[
            validation["TARGET_TIMESTAMP"]
            <= validation["DATE_TIME"].max()
        ]

    for split_name, part in [
        ("train", train),
        ("validation", validation),
        ("test", test),
    ]:
        output_path = OUTPUT_DIR / f"{plant}_{split_name}.csv"
        part.to_csv(output_path, index=False)

        print(
            f"{plant} {split_name}: {len(part)} rows | "
            f"{part['DATE_TIME'].min()} to "
            f"{part['DATE_TIME'].max()}"
        )

    print(f"{plant}: eligible complete-coverage rows = {n}\n")

print("Complete-coverage splits created.")
