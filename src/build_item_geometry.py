import polars as pl
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from configs.paths import ITEM_FEATURES_PATH, INTERIM_DIR

EVAL_VERTICALS = [0, 2, 3, 4, 5, 7]


def main() -> None:
    INTERIM_DIR.mkdir(parents=True, exist_ok=True)

    out_path = INTERIM_DIR / "item_geometry_eval_verticals.parquet"

    print("Building item geometry table...")
    print(f"Source: {ITEM_FEATURES_PATH}")
    print(f"Target: {out_path}")

    items = (
        pl.scan_parquet(ITEM_FEATURES_PATH)
        .filter(pl.col("vertical_id").is_in(EVAL_VERTICALS))
        .select(
            [
                pl.col("item_id").cast(pl.UInt32),
                pl.col("vertical_id").cast(pl.UInt8),
                pl.col("category_ext_y").cast(pl.UInt16),
                pl.col("region_id_y").cast(pl.UInt16),
                pl.col("loc_id_y").cast(pl.UInt32),
                pl.col("sid_0_y").cast(pl.UInt16),
                pl.col("sid_1_y").cast(pl.UInt16),
                pl.col("sid_2_y").cast(pl.UInt16),
                pl.col("sid_3_y").cast(pl.UInt16),
            ]
        )
    )

    items.sink_parquet(out_path)

    print("Saved item geometry.")

    df = pl.scan_parquet(out_path)

    summary = df.select(
        [
            pl.len().alias("n_items"),
            pl.col("item_id").n_unique().alias("n_unique_items"),
            pl.col("vertical_id").n_unique().alias("n_verticals"),
            pl.col("category_ext_y").n_unique().alias("n_categories"),
            pl.col("region_id_y").n_unique().alias("n_regions"),
            pl.col("loc_id_y").n_unique().alias("n_locs"),
            pl.col("sid_0_y").n_unique().alias("n_sid0"),
        ]
    ).collect()

    print("\nSummary:")
    print(summary)

    vertical_counts = (
        df.group_by("vertical_id")
        .agg(pl.len().alias("n_items"))
        .sort("vertical_id")
        .collect()
    )

    print("\nVertical counts:")
    print(vertical_counts)


if __name__ == "__main__":
    main()
