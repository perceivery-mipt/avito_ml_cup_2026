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
    print("Basic ranges and cardinalities")
    print("=" * 80)

    exprs = []
    for col in GEOM_COLS:
        exprs.extend(
            [
                pl.col(col).min().alias(f"{col}_min"),
                pl.col(col).max().alias(f"{col}_max"),
                pl.col(col).n_unique().alias(f"{col}_n_unique"),
            ]
        )

    summary = items.select(exprs).collect()
    print(summary)

    out_path = REPORTS_DIR / "item_space_summary.csv"
    summary.write_csv(out_path)
    print(f"\nSaved: {out_path}")

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

    out_path = REPORTS_DIR / "vertical_counts.csv"
    vertical_counts.write_csv(out_path)
    print(f"\nSaved: {out_path}")

    print("\n" + "=" * 80)
    print("Top categories by number of items")
    print("=" * 80)

    category_counts = (
        items
        .group_by(["vertical_id", "category_ext_y"])
        .agg(pl.len().alias("n_items"))
        .sort("n_items", descending=True)
        .limit(30)
        .collect()
    )
    print(category_counts)

    out_path = REPORTS_DIR / "top_categories.csv"
    category_counts.write_csv(out_path)
    print(f"\nSaved: {out_path}")

    print("\n" + "=" * 80)
    print("SID prefix cardinalities")
    print("=" * 80)

    sid_prefix_summary = items.select(
        [
            pl.struct(["sid_0_y"]).n_unique().alias("n_sid0"),
            pl.struct(["sid_0_y", "sid_1_y"]).n_unique().alias("n_sid01"),
            pl.struct(["sid_0_y", "sid_1_y", "sid_2_y"]).n_unique().alias("n_sid012"),
            pl.struct(["sid_0_y", "sid_1_y", "sid_2_y", "sid_3_y"]).n_unique().alias("n_sid0123"),
        ]
    ).collect()

    print(sid_prefix_summary)

    out_path = REPORTS_DIR / "sid_prefix_summary.csv"
    sid_prefix_summary.write_csv(out_path)
    print(f"\nSaved: {out_path}")

    print("\nDone.")


if __name__ == "__main__":
    main()
