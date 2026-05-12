import polars as pl
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from configs.paths import ITEM_FEATURES_PATH, REPORTS_DIR


GEOM_COLS = [
    "vertical_id",
    "category_ext_y",
    "region_id_y",
    "loc_id_y",
    "sid_0_y",
    "sid_1_y",
    "sid_2_y",
    "sid_3_y",
]


def main() -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    print("Reading item_features lazily...")
    items = pl.scan_parquet(ITEM_FEATURES_PATH)

    print("\n" + "=" * 80)
    print("Basic min/max only")
    print("=" * 80)

    exprs = []
    for col in GEOM_COLS:
        exprs.extend([
            pl.col(col).min().alias(f"{col}_min"),
            pl.col(col).max().alias(f"{col}_max"),
        ])

    summary = items.select(exprs).collect()
    print(summary)
    summary.write_csv(REPORTS_DIR / "item_space_minmax.csv")

    print("\n" + "=" * 80)
    print("Items per vertical_id")
    print("=" * 80)

    vertical_counts = (
        items
        .group_by("vertical_id")
        .agg(pl.len().alias("n_items"))
        .sort("vertical_id")
        .collect()
    )
    print(vertical_counts)
    vertical_counts.write_csv(REPORTS_DIR / "vertical_counts.csv")

    print("\n" + "=" * 80)
    print("Sample 1,000,000 rows: approximate cardinalities")
    print("=" * 80)

    sample = items.head(1_000_000)

    approx = sample.select([
        pl.col("category_ext_y").n_unique().alias("category_n_unique_sample"),
        pl.col("region_id_y").n_unique().alias("region_n_unique_sample"),
        pl.col("loc_id_y").n_unique().alias("loc_n_unique_sample"),
        pl.col("sid_0_y").n_unique().alias("sid_0_n_unique_sample"),
        pl.struct(["sid_0_y", "sid_1_y"]).n_unique().alias("sid01_n_unique_sample"),
        pl.struct(["sid_0_y", "sid_1_y", "sid_2_y"]).n_unique().alias("sid012_n_unique_sample"),
    ]).collect()

    print(approx)
    approx.write_csv(REPORTS_DIR / "item_space_sample_cardinalities.csv")

    print("\nDone.")


if __name__ == "__main__":
    main()
