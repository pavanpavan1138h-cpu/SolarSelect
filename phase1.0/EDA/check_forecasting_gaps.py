
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
INTERIM_DIR = PROJECT_ROOT / "data" / "interim"

for plant in ["plant1", "plant2"]:
    path = INTERIM_DIR / f"{plant}_forecasting_dataset.csv"
    df = pd.read_csv(path, parse_dates=["DATE_TIME"])
    df = df.sort_values("DATE_TIME").reset_index(drop=True)

    # Check gaps between consecutive observed timestamps.
    gaps = df["DATE_TIME"].diff()
    irregular = df.loc[
        gaps.notna() & (gaps != pd.Timedelta(minutes=15)),
        ["DATE_TIME"],
    ].copy()

    irregular["gap_from_previous"] = gaps[
        gaps.notna() & (gaps != pd.Timedelta(minutes=15))
    ].to_numpy()

    # Verify each target against the exact timestamp 15 minutes ahead.
    lookup = df.set_index("DATE_TIME")["AC_POWER"]
    expected_target = (
        df["DATE_TIME"] + pd.Timedelta(minutes=15)
    ).map(lookup)

    valid_target = (
        df["TARGET_AC_POWER_15MIN"].notna()
        & expected_target.notna()
        & (
            df["TARGET_AC_POWER_15MIN"]
            == expected_target
        )
    )

    print(f"\n{'=' * 40}\n{plant.upper()}\n{'=' * 40}")
    print("Total timestamps:", len(df))
    print("Irregular gaps:", len(irregular))
    print(irregular.to_string(index=False))
    print("Missing targets:", df["TARGET_AC_POWER_15MIN"].isna().sum())
    print("Targets verified:", valid_target.sum())
    print(
        "Target mismatches:",
        (
            df["TARGET_AC_POWER_15MIN"].notna()
            & ~valid_target
        ).sum(),
    )
