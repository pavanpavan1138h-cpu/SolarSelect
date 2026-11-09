
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
INTERIM_DIR = PROJECT_ROOT / "data" / "interim"
SPLIT_DIR = PROJECT_ROOT / "data" / "processed" / "splits"

SPLIT_DIR.mkdir(parents=True, exist_ok=True)

for plant in ["plant1", "plant2"]:
    path = INTERIM_DIR / f"{plant}_forecasting_dataset.csv"
    df = pd.read_csv(path, parse_dates=["DATE_TIME", "TARGET_TIMESTAMP"])
    df = df.sort_values("DATE_TIME").reset_index(drop=True)

    # Only examples with a valid future target are eligible.
    df = df.dropna(subset=["TARGET_AC_POWER_15MIN"]).copy()

    # Chronological split: 70% train, 15% validation, 15% test.
    n = len(df)
    train_end = int(n * 0.70)
    val_end = int(n * 0.85)

    train = df.iloc[:train_end].copy()
    val = df.iloc[train_end:val_end].copy()
    test = df.iloc[val_end:].copy()

    # Remove examples whose future target crosses a split boundary.
    train_end_time = train["DATE_TIME"].max()
    val_end_time = val["DATE_TIME"].max()

    train = train[
        train["TARGET_TIMESTAMP"] <= train_end_time
    ]
    val = val[
        val["TARGET_TIMESTAMP"] <= val_end_time
    ]

    for name, part in [
        ("train", train),
        ("validation", val),
        ("test", test),
    ]:
        output = SPLIT_DIR / f"{plant}_{name}.csv"
        part.to_csv(output, index=False)
        print(
            f"{plant} {name}: {len(part)} rows | "
            f"{part['DATE_TIME'].min()} to "
            f"{part['DATE_TIME'].max()}"
        )

    print()

print("Chronological splitting completed.")
