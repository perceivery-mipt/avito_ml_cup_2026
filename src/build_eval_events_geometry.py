import polars as pl
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from configs.paths import EVAL_USER_EVENTS_PATH, INTERIM_DIR

ITEM_GEOMETRY_PATH = INTERIM_DIR / "item_geometry_eval_verticals.parquet"
OUT_PATH = INTERIM_DIR / "eval_events_geometry.parquet"


def main() -> None:
    print("Building eval events with item geometry...")
    print(f"Events source: {EVAL_USER_EVENTS_PATH}")
    print(f"Item geometry:  {ITEM_GEOMETRY_PATH}")
    print(f"Target:         {OUT_PATH}")

    events = (
        pl.scan_parquet(EVAL_USER_EVENTS_PATH)
        .select(
            [
                pl.col("timestamp").cast(pl.Int64),
                pl.col("eid").cast(pl.UInt16),
                pl.col("user_id").cast(pl.UInt32),
                pl.col("item_id").cast(pl.UInt32),
            ]
        )
    )

    items = pl.scan_parquet(ITEM_GEOMETRY_PATH)

    joined = (
        events
        .join(items, on="item_id", how="inner")
    )

    joined.sink_parquet(OUT_PATH)

    print("Saved eval events with geometry.")

    df = pl.scan_parquet(OUT_PATH)

    summary = df.select(
        [
            pl.len().alias("n_events_after_join"),
            pl.col("user_id").n_unique().alias("n_users"),
            pl.col("item_id").n_unique().alias("n_items"),
            pl.col("eid").n_unique().alias("n_eids"),
            pl.col("vertical_id").n_unique().alias("n_verticals"),
            pl.col("category_ext_y").n_unique().alias("n_categories"),
            pl.col("region_id_y").n_unique().alias("n_regions"),
            pl.col("sid_0_y").n_unique().alias("n_sid0"),
        ]
    ).collect()

    print("\nSummary:")
    print(summary)

    print("\nEvents per vertical:")
    vertical_counts = (
        df.group_by("vertical_id")
        .agg(pl.len().alias("n_events"))
        .sort("vertical_id")
        .collect()
    )
    print(vertical_counts)

    print("\nEvents per eid:")
    eid_counts = (
        df.group_by("eid")
        .agg(pl.len().alias("n_events"))
        .sort("n_events", descending=True)
        .collect()
    )
    print(eid_counts)

    print("\nHead:")
    print(df.head(5).collect())


if __name__ == "__main__":
    main()
