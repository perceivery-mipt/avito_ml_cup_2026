import polars as pl
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from configs.paths import INTERIM_DIR

EVENTS_GEOMETRY_PATH = INTERIM_DIR / "eval_events_geometry.parquet"
ITEM_GEOMETRY_PATH = INTERIM_DIR / "item_geometry_eval_verticals.parquet"

OUT_POPULAR_ITEMS = INTERIM_DIR / "item_popularity_eval_events.parquet"
OUT_INDEX_VCR = INTERIM_DIR / "candidate_index_vertical_category_region.parquet"
OUT_INDEX_VC = INTERIM_DIR / "candidate_index_vertical_category.parquet"
OUT_INDEX_VSID01 = INTERIM_DIR / "candidate_index_vertical_sid01.parquet"
OUT_INDEX_RSID01 = INTERIM_DIR / "candidate_index_region_sid01.parquet"
OUT_GLOBAL_POPULAR = INTERIM_DIR / "candidate_index_global_popular.parquet"

TOP_K_PER_KEY = 300
GLOBAL_TOP_K = 5000


def save_top_index(
    items_with_pop: pl.LazyFrame,
    keys: list[str],
    out_path: Path,
    top_k_per_key: int = TOP_K_PER_KEY,
) -> None:
    print("\n" + "=" * 80)
    print(f"Building candidate index: {out_path.name}")
    print(f"Keys: {keys}")
    print("=" * 80)

    index = (
        items_with_pop
        .sort([*keys, "item_popularity"], descending=[False] * len(keys) + [True])
        .with_columns(
            pl.col("item_popularity")
            .rank(method="ordinal", descending=True)
            .over(keys)
            .alias("rank_in_key")
        )
        .filter(pl.col("rank_in_key") <= top_k_per_key)
        .select([*keys, "item_id", "item_popularity", "rank_in_key"])
    )

    index.sink_parquet(out_path)

    df = pl.scan_parquet(out_path)

    summary = df.select(
        [
            pl.len().alias("n_rows"),
            pl.col("item_id").n_unique().alias("n_unique_items"),
            pl.col("item_popularity").min().alias("pop_min"),
            pl.col("item_popularity").mean().alias("pop_mean"),
            pl.col("item_popularity").max().alias("pop_max"),
        ]
    ).collect()

    print("Summary:")
    print(summary)

    print("\nHead:")
    print(df.head(10).collect())


def main() -> None:
    print("Building item popularity from eval events...")
    print(f"Source: {EVENTS_GEOMETRY_PATH}")

    events = pl.scan_parquet(EVENTS_GEOMETRY_PATH)

    item_popularity = (
        events
        .group_by("item_id")
        .agg(pl.len().alias("item_popularity"))
    )

    item_popularity.sink_parquet(OUT_POPULAR_ITEMS)

    print(f"Saved item popularity: {OUT_POPULAR_ITEMS}")

    pop = pl.scan_parquet(OUT_POPULAR_ITEMS)

    print("\nPopularity summary:")
    print(
        pop.select(
            [
                pl.len().alias("n_items_with_events"),
                pl.col("item_popularity").min().alias("pop_min"),
                pl.col("item_popularity").mean().alias("pop_mean"),
                pl.col("item_popularity").max().alias("pop_max"),
            ]
        ).collect()
    )

    print("\nJoining popularity with item geometry...")
    items = pl.scan_parquet(ITEM_GEOMETRY_PATH)

    # Для первого индекса берём только item-ы, которые встречались в eval history.
    # Это сильно уменьшает размер и даёт рабочий baseline.
    items_with_pop = (
        items
        .join(pop, on="item_id", how="inner")
        .select(
            [
                "item_id",
                "vertical_id",
                "category_ext_y",
                "region_id_y",
                "loc_id_y",
                "sid_0_y",
                "sid_1_y",
                "sid_2_y",
                "sid_3_y",
                "item_popularity",
            ]
        )
    )

    save_top_index(
        items_with_pop,
        keys=["vertical_id", "category_ext_y", "region_id_y"],
        out_path=OUT_INDEX_VCR,
    )

    save_top_index(
        items_with_pop,
        keys=["vertical_id", "category_ext_y"],
        out_path=OUT_INDEX_VC,
    )

    save_top_index(
        items_with_pop,
        keys=["vertical_id", "sid_0_y", "sid_1_y"],
        out_path=OUT_INDEX_VSID01,
    )

    save_top_index(
        items_with_pop,
        keys=["region_id_y", "sid_0_y", "sid_1_y"],
        out_path=OUT_INDEX_RSID01,
    )

    print("\n" + "=" * 80)
    print("Building global popular fallback")
    print("=" * 80)

    global_popular = (
        items_with_pop
        .sort("item_popularity", descending=True)
        .limit(GLOBAL_TOP_K)
        .select(["item_id", "item_popularity"])
    )

    global_popular.sink_parquet(OUT_GLOBAL_POPULAR)

    print("Global popular:")
    print(pl.scan_parquet(OUT_GLOBAL_POPULAR).head(10).collect())

    print("\nDone.")


if __name__ == "__main__":
    main()
