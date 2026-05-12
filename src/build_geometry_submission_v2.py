import polars as pl
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from configs.paths import (
    EVAL_USERS_PATH,
    INTERIM_DIR,
    SUBMISSIONS_DIR,
)

PROFILE_VCR = INTERIM_DIR / "user_profile_vertical_category_region.parquet"
PROFILE_VC = INTERIM_DIR / "user_profile_vertical_category.parquet"
PROFILE_VSID01 = INTERIM_DIR / "user_profile_vertical_sid01.parquet"
PROFILE_RSID01 = INTERIM_DIR / "user_profile_region_sid01.parquet"

INDEX_VCR = INTERIM_DIR / "candidate_index_vertical_category_region.parquet"
INDEX_VC = INTERIM_DIR / "candidate_index_vertical_category.parquet"
INDEX_VSID01 = INTERIM_DIR / "candidate_index_vertical_sid01.parquet"
INDEX_RSID01 = INTERIM_DIR / "candidate_index_region_sid01.parquet"

GLOBAL_POPULAR = INTERIM_DIR / "candidate_index_global_popular.parquet"
SEEN_EVENTS = INTERIM_DIR / "eval_events_geometry.parquet"

OUT_SUBMISSION = SUBMISSIONS_DIR / "submission_geometry_v2.csv"
OUT_CANDIDATES = INTERIM_DIR / "geometry_candidates_v2.parquet"

TOP_PROFILE_KEYS = 5
TOP_ITEMS_VCR = 50
TOP_ITEMS_VC = 60
TOP_ITEMS_VSID01 = 30
TOP_ITEMS_RSID01 = 25

TOP_GLOBAL = 160
TOP_FINAL = 160


def top_user_profile(profile: pl.LazyFrame, top_k: int) -> pl.LazyFrame:
    return (
        profile
        .sort(["user_id", "mass"], descending=[False, True])
        .with_columns(
            pl.col("mass")
            .rank(method="ordinal", descending=True)
            .over("user_id")
            .alias("profile_rank")
        )
        .filter(pl.col("profile_rank") <= top_k)
        .drop("profile_rank")
    )


def build_source_candidates(
    profile_path: Path,
    index_path: Path,
    keys: list[str],
    top_profile_keys: int,
    top_items_per_key: int,
    source_weight: float,
    source_name: str,
) -> pl.LazyFrame:
    print(f"Preparing source: {source_name}")

    profile = top_user_profile(
        pl.scan_parquet(profile_path),
        top_k=top_profile_keys,
    )

    index = (
        pl.scan_parquet(index_path)
        .filter(pl.col("rank_in_key") <= top_items_per_key)
    )

    candidates = (
        profile
        .join(index, on=keys, how="inner")
        .with_columns(
            [
                (
                    pl.col("mass")
                    * source_weight
                    * (1.0 + pl.col("item_popularity").log1p())
                    / pl.col("rank_in_key").sqrt()
                ).alias("score"),
                pl.lit(source_name).alias("source"),
            ]
        )
        .select(["user_id", "item_id", "score", "source"])
    )

    return candidates


def main() -> None:
    SUBMISSIONS_DIR.mkdir(parents=True, exist_ok=True)

    print("Building geometry candidates v2...")
    print("Changes vs v1: added region_sid01 source.")

    cand_vcr = build_source_candidates(
        profile_path=PROFILE_VCR,
        index_path=INDEX_VCR,
        keys=["vertical_id", "category_ext_y", "region_id_y"],
        top_profile_keys=TOP_PROFILE_KEYS,
        top_items_per_key=TOP_ITEMS_VCR,
        source_weight=1.00,
        source_name="vcr",
    )

    cand_vc = build_source_candidates(
        profile_path=PROFILE_VC,
        index_path=INDEX_VC,
        keys=["vertical_id", "category_ext_y"],
        top_profile_keys=TOP_PROFILE_KEYS,
        top_items_per_key=TOP_ITEMS_VC,
        source_weight=0.60,
        source_name="vc",
    )

    cand_vsid01 = build_source_candidates(
        profile_path=PROFILE_VSID01,
        index_path=INDEX_VSID01,
        keys=["vertical_id", "sid_0_y", "sid_1_y"],
        top_profile_keys=TOP_PROFILE_KEYS,
        top_items_per_key=TOP_ITEMS_VSID01,
        source_weight=0.80,
        source_name="vsid01",
    )

    cand_rsid01 = build_source_candidates(
        profile_path=PROFILE_RSID01,
        index_path=INDEX_RSID01,
        keys=["region_id_y", "sid_0_y", "sid_1_y"],
        top_profile_keys=TOP_PROFILE_KEYS,
        top_items_per_key=TOP_ITEMS_RSID01,
        source_weight=0.70,
        source_name="rsid01",
    )

    candidates = pl.concat([cand_vcr, cand_vc, cand_vsid01, cand_rsid01])

    print(f"Saving raw candidates: {OUT_CANDIDATES}")
    candidates.sink_parquet(OUT_CANDIDATES)

    cand = pl.scan_parquet(OUT_CANDIDATES)

    print("\nRaw candidate summary:")
    print(
        cand.select(
            [
                pl.len().alias("n_rows"),
                pl.col("user_id").n_unique().alias("n_users"),
                pl.col("item_id").n_unique().alias("n_items"),
                pl.col("score").min().alias("score_min"),
                pl.col("score").mean().alias("score_mean"),
                pl.col("score").max().alias("score_max"),
            ]
        ).collect()
    )

    print("\nRaw candidates by source:")
    print(
        cand.group_by("source")
        .agg(
            [
                pl.len().alias("n_rows"),
                pl.col("user_id").n_unique().alias("n_users"),
                pl.col("item_id").n_unique().alias("n_items"),
                pl.col("score").mean().alias("score_mean"),
                pl.col("score").max().alias("score_max"),
            ]
        )
        .sort("source")
        .collect()
    )

    print("\nAggregating duplicate user-item candidates...")
    cand_agg = (
        cand
        .group_by(["user_id", "item_id"])
        .agg(pl.col("score").sum().alias("score"))
    )

    print("Preparing seen user-item pairs...")
    seen = (
        pl.scan_parquet(SEEN_EVENTS)
        .select(["user_id", "item_id"])
        .unique()
    )

    print("Removing already seen items...")
    cand_unseen = cand_agg.join(seen, on=["user_id", "item_id"], how="anti")

    print("Preparing global fallback candidates...")
    users = (
        pl.scan_csv(EVAL_USERS_PATH)
        .select(pl.col("user_id").cast(pl.UInt32))
    )

    global_items = (
        pl.scan_parquet(GLOBAL_POPULAR)
        .limit(TOP_GLOBAL)
        .select(
            [
                pl.col("item_id").cast(pl.UInt32),
                pl.col("item_popularity"),
            ]
        )
    )

    fallback = (
        users
        .join(global_items, how="cross")
        .with_columns(
            (
                0.001 * (1.0 + pl.col("item_popularity").log1p())
            ).alias("score")
        )
        .select(["user_id", "item_id", "score"])
        .join(seen, on=["user_id", "item_id"], how="anti")
    )

    print("Combining geometry candidates with fallback...")
    all_candidates = pl.concat([cand_unseen, fallback])

    print("Ranking candidates per user...")
    final = (
        all_candidates
        .group_by(["user_id", "item_id"])
        .agg(pl.col("score").max().alias("score"))
        .sort(["user_id", "score", "item_id"], descending=[False, True, False])
        .with_columns(
            pl.col("score")
            .rank(method="ordinal", descending=True)
            .over("user_id")
            .alias("rank")
        )
        .filter(pl.col("rank") <= TOP_FINAL)
        .select(["user_id", "item_id"])
    )

    print("\nFinal submission summary:")
    print(
        final.select(
            [
                pl.len().alias("n_rows"),
                pl.col("user_id").n_unique().alias("n_users"),
                pl.col("item_id").n_unique().alias("n_unique_items"),
            ]
        ).collect()
    )

    counts = (
        final
        .group_by("user_id")
        .agg(pl.len().alias("n_recs"))
        .select(
            [
                pl.col("n_recs").min().alias("min_recs_per_user"),
                pl.col("n_recs").mean().alias("mean_recs_per_user"),
                pl.col("n_recs").max().alias("max_recs_per_user"),
            ]
        )
        .collect()
    )

    print("\nRecommendations per user:")
    print(counts)

    print(f"\nWriting submission: {OUT_SUBMISSION}")
    final.collect(streaming=True).write_csv(OUT_SUBMISSION)

    print("Done.")
    print(f"Saved: {OUT_SUBMISSION}")


if __name__ == "__main__":
    main()
