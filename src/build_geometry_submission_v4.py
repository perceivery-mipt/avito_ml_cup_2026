import polars as pl
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from configs.paths import (
    EVAL_USERS_PATH,
    CONTACT_EIDS_PATH,
    INTERIM_DIR,
    SUBMISSIONS_DIR,
)

# ============================================================
# Profiles
# ============================================================

PROFILE_VCR = INTERIM_DIR / "user_profile_vertical_category_region.parquet"
PROFILE_VC = INTERIM_DIR / "user_profile_vertical_category.parquet"
PROFILE_VSID01 = INTERIM_DIR / "user_profile_vertical_sid01.parquet"
PROFILE_RSID01 = INTERIM_DIR / "user_profile_region_sid01.parquet"

# ============================================================
# Candidate indices
# ============================================================

INDEX_VCR = INTERIM_DIR / "candidate_index_vertical_category_region.parquet"
INDEX_VC = INTERIM_DIR / "candidate_index_vertical_category.parquet"
INDEX_VSID01 = INTERIM_DIR / "candidate_index_vertical_sid01.parquet"
INDEX_RSID01 = INTERIM_DIR / "candidate_index_region_sid01.parquet"

# ============================================================
# Base data
# ============================================================

GLOBAL_POPULAR = INTERIM_DIR / "candidate_index_global_popular.parquet"
SEEN_EVENTS = INTERIM_DIR / "eval_events_geometry.parquet"
ITEM_GEOMETRY = INTERIM_DIR / "item_geometry_eval_verticals.parquet"
USER_MEASURE = INTERIM_DIR / "user_interest_measure.parquet"
ITEM_POPULARITY = INTERIM_DIR / "item_popularity_eval_events.parquet"

# ============================================================
# Outputs
# ============================================================

OUT_BASE_CANDIDATES = INTERIM_DIR / "geometry_candidates_v4_base.parquet"
OUT_PREFILTERED = INTERIM_DIR / "geometry_candidates_v4_prefiltered.parquet"
OUT_KERNEL = INTERIM_DIR / "geometry_candidates_v4_kernel_scores.parquet"
OUT_SUBMISSION = SUBMISSIONS_DIR / "submission_geometry_v4.csv"

# ============================================================
# Candidate generation parameters
# inherited from geometry_v3 / geometry_v2
# ============================================================

TOP_PROFILE_KEYS = 5
TOP_ITEMS_VCR = 50
TOP_ITEMS_VC = 60
TOP_ITEMS_VSID01 = 30
TOP_ITEMS_RSID01 = 25

# ============================================================
# Kernel reranking parameters
# geometry_v4
# ============================================================

TOP_CANDIDATES_PER_USER_BEFORE_KERNEL = 1000
TOP_HISTORY_ATOMS_PER_USER = 50
TOP_CONTACT_ATOMS_PER_USER = 20

BASE_SCORE_WEIGHT = 1.00
KERNEL_SUM_WEIGHT = 0.20
KERNEL_MAX_WEIGHT = 0.50
CONTACT_KERNEL_SUM_WEIGHT = 0.30
CONTACT_KERNEL_MAX_WEIGHT = 0.80

W_SAME_VERTICAL = 0.50
W_SAME_CATEGORY = 1.00
W_SAME_REGION = 0.80
W_SAME_LOC = 0.40
W_SAME_SID0 = 0.30
W_SAME_SID01 = 1.20
W_SAME_SID012 = 1.80
W_SAME_SID0123 = 2.40

POPULARITY_WEIGHT = 0.03

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
    print(f"Preparing source: {source_name}", flush=True)

    profile = top_user_profile(
        pl.scan_parquet(profile_path),
        top_k=top_profile_keys,
    )

    index = (
        pl.scan_parquet(index_path)
        .filter(pl.col("rank_in_key") <= top_items_per_key)
    )

    return (
        profile
        .join(index, on=keys, how="inner")
        .with_columns(
            [
                (
                    pl.col("mass")
                    * source_weight
                    * (1.0 + pl.col("item_popularity").log1p())
                    / pl.col("rank_in_key").sqrt()
                ).alias("base_score"),
                pl.lit(source_name).alias("source"),
            ]
        )
        .select(["user_id", "item_id", "base_score", "source"])
    )


def build_base_candidates() -> None:
    print("=" * 80, flush=True)
    print("Step 1: building geometry-v3-style base candidates", flush=True)
    print("=" * 80, flush=True)

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

    print(f"Writing base candidates: {OUT_BASE_CANDIDATES}", flush=True)
    candidates.sink_parquet(OUT_BASE_CANDIDATES)
    print("Base candidates saved.", flush=True)

    cand = pl.scan_parquet(OUT_BASE_CANDIDATES)

    print("\nRaw candidate summary:", flush=True)
    print(
        cand.select(
            [
                pl.len().alias("n_rows"),
                pl.col("user_id").n_unique().alias("n_users"),
                pl.col("item_id").n_unique().alias("n_items"),
                pl.col("base_score").min().alias("base_score_min"),
                pl.col("base_score").mean().alias("base_score_mean"),
                pl.col("base_score").max().alias("base_score_max"),
            ]
        ).collect(),
        flush=True,
    )

    print("\nRaw candidates by source:", flush=True)
    print(
        cand.group_by("source")
        .agg(
            [
                pl.len().alias("n_rows"),
                pl.col("user_id").n_unique().alias("n_users"),
                pl.col("item_id").n_unique().alias("n_items"),
                pl.col("base_score").mean().alias("base_score_mean"),
                pl.col("base_score").max().alias("base_score_max"),
            ]
        )
        .sort("source")
        .collect(),
        flush=True,
    )


def prefilter_candidates() -> None:
    print("=" * 80, flush=True)
    print("Step 2: aggregating, removing seen, and prefiltering top candidates", flush=True)
    print("=" * 80, flush=True)

    cand = (
        pl.scan_parquet(OUT_BASE_CANDIDATES)
        .group_by(["user_id", "item_id"])
        .agg(pl.col("base_score").sum().alias("base_score"))
    )

    seen = (
        pl.scan_parquet(SEEN_EVENTS)
        .select(["user_id", "item_id"])
        .unique()
    )

    cand_unseen = cand.join(seen, on=["user_id", "item_id"], how="anti")

    prefiltered = (
        cand_unseen
        .sort(["user_id", "base_score", "item_id"], descending=[False, True, False])
        .with_columns(
            pl.col("base_score")
            .rank(method="ordinal", descending=True)
            .over("user_id")
            .alias("base_rank")
        )
        .filter(pl.col("base_rank") <= TOP_CANDIDATES_PER_USER_BEFORE_KERNEL)
    )

    print(f"Writing prefiltered candidates: {OUT_PREFILTERED}", flush=True)
    prefiltered.sink_parquet(OUT_PREFILTERED)
    print("Prefiltered candidates saved.", flush=True)

    pf = pl.scan_parquet(OUT_PREFILTERED)

    print("\nPrefiltered candidate summary:", flush=True)
    print(
        pf.select(
            [
                pl.len().alias("n_rows"),
                pl.col("user_id").n_unique().alias("n_users"),
                pl.col("item_id").n_unique().alias("n_items"),
                pl.col("base_score").mean().alias("base_score_mean"),
                pl.col("base_score").max().alias("base_score_max"),
            ]
        ).collect(),
        flush=True,
    )

    print("\nCandidates per user after prefilter:", flush=True)
    print(
        pf.group_by("user_id")
        .agg(pl.len().alias("n_candidates"))
        .select(
            [
                pl.col("n_candidates").min().alias("min_candidates"),
                pl.col("n_candidates").mean().alias("mean_candidates"),
                pl.col("n_candidates").max().alias("max_candidates"),
            ]
        )
        .collect(),
        flush=True,
    )


def build_history_atoms(contact_only: bool) -> pl.LazyFrame:
    if contact_only:
        print("Preparing top contact history atoms per user...", flush=True)

        contact_eids = (
            pl.read_csv(CONTACT_EIDS_PATH)
            .select(pl.col("mapped_eid").cast(pl.UInt16))
            .get_column("mapped_eid")
            .to_list()
        )

        top_k = TOP_CONTACT_ATOMS_PER_USER
    else:
        print("Preparing top general history atoms per user...", flush=True)
        contact_eids = None
        top_k = TOP_HISTORY_ATOMS_PER_USER

    atoms = pl.scan_parquet(USER_MEASURE)

    if contact_only:
        atoms = atoms.filter(pl.col("eid").is_in(contact_eids))

    atoms = (
        atoms
        .group_by(
            [
                "user_id",
                "item_id",
                "vertical_id",
                "category_ext_y",
                "region_id_y",
                "loc_id_y",
                "sid_0_y",
                "sid_1_y",
                "sid_2_y",
                "sid_3_y",
            ]
        )
        .agg(
            [
                pl.col("event_weight").sum().alias("atom_weight"),
                pl.len().alias("n_events"),
                pl.col("timestamp").max().alias("last_timestamp"),
            ]
        )
        .sort(["user_id", "atom_weight", "last_timestamp"], descending=[False, True, True])
        .with_columns(
            pl.col("atom_weight")
            .rank(method="ordinal", descending=True)
            .over("user_id")
            .alias("atom_rank")
        )
        .filter(pl.col("atom_rank") <= top_k)
        .rename(
            {
                "item_id": "hist_item_id",
                "vertical_id": "hist_vertical_id",
                "category_ext_y": "hist_category_ext_y",
                "region_id_y": "hist_region_id_y",
                "loc_id_y": "hist_loc_id_y",
                "sid_0_y": "hist_sid_0_y",
                "sid_1_y": "hist_sid_1_y",
                "sid_2_y": "hist_sid_2_y",
                "sid_3_y": "hist_sid_3_y",
            }
        )
    )

    return atoms


def add_kernel_columns(pairs: pl.LazyFrame) -> pl.LazyFrame:
    same_vertical = (pl.col("vertical_id") == pl.col("hist_vertical_id")).cast(pl.Float64)
    same_category = (pl.col("category_ext_y") == pl.col("hist_category_ext_y")).cast(pl.Float64)
    same_region = (pl.col("region_id_y") == pl.col("hist_region_id_y")).cast(pl.Float64)
    same_loc = (pl.col("loc_id_y") == pl.col("hist_loc_id_y")).cast(pl.Float64)

    same_sid0_bool = pl.col("sid_0_y") == pl.col("hist_sid_0_y")
    same_sid01_bool = same_sid0_bool & (pl.col("sid_1_y") == pl.col("hist_sid_1_y"))
    same_sid012_bool = same_sid01_bool & (pl.col("sid_2_y") == pl.col("hist_sid_2_y"))
    same_sid0123_bool = same_sid012_bool & (pl.col("sid_3_y") == pl.col("hist_sid_3_y"))

    same_sid0 = same_sid0_bool.cast(pl.Float64)
    same_sid01 = same_sid01_bool.cast(pl.Float64)
    same_sid012 = same_sid012_bool.cast(pl.Float64)
    same_sid0123 = same_sid0123_bool.cast(pl.Float64)

    return (
        pairs
        .with_columns(
            (
                W_SAME_VERTICAL * same_vertical
                + W_SAME_CATEGORY * same_category
                + W_SAME_REGION * same_region
                + W_SAME_LOC * same_loc
                + W_SAME_SID0 * same_sid0
                + W_SAME_SID01 * same_sid01
                + W_SAME_SID012 * same_sid012
                + W_SAME_SID0123 * same_sid0123
            ).alias("kernel_sim")
        )
        .with_columns(
            (pl.col("atom_weight") * pl.col("kernel_sim")).alias("kernel_contribution")
        )
    )


def compute_kernel_scores() -> None:
    print("=" * 80, flush=True)
    print("Step 3: computing extended kernel similarity scores", flush=True)
    print("=" * 80, flush=True)

    candidates = pl.scan_parquet(OUT_PREFILTERED)

    items = (
        pl.scan_parquet(ITEM_GEOMETRY)
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
            ]
        )
    )

    pop = pl.scan_parquet(ITEM_POPULARITY)

    candidates_geom = (
        candidates
        .join(items, on="item_id", how="left")
        .join(pop, on="item_id", how="left")
        .with_columns(pl.col("item_popularity").fill_null(0))
    )

    # ------------------------------------------------------------
    # General history kernel
    # ------------------------------------------------------------

    general_atoms = build_history_atoms(contact_only=False)

    general_pairs = candidates_geom.join(general_atoms, on="user_id", how="inner")
    general_pairs = add_kernel_columns(general_pairs)

    general_scores = (
        general_pairs
        .group_by(["user_id", "item_id"])
        .agg(
            [
                pl.col("base_score").first().alias("base_score"),
                pl.col("item_popularity").first().alias("item_popularity"),
                pl.col("kernel_contribution").sum().alias("kernel_sum"),
                pl.col("kernel_contribution").max().alias("kernel_max"),
                pl.col("kernel_sim").max().alias("max_kernel_sim"),
            ]
        )
    )

    # ------------------------------------------------------------
    # Contact-only history kernel
    # ------------------------------------------------------------

    contact_atoms = build_history_atoms(contact_only=True)

    contact_pairs = candidates_geom.join(contact_atoms, on="user_id", how="inner")
    contact_pairs = add_kernel_columns(contact_pairs)

    contact_scores = (
        contact_pairs
        .group_by(["user_id", "item_id"])
        .agg(
            [
                pl.col("kernel_contribution").sum().alias("contact_kernel_sum"),
                pl.col("kernel_contribution").max().alias("contact_kernel_max"),
                pl.col("kernel_sim").max().alias("contact_max_kernel_sim"),
            ]
        )
    )

    kernel_scores = (
        general_scores
        .join(contact_scores, on=["user_id", "item_id"], how="left")
        .with_columns(
            [
                pl.col("contact_kernel_sum").fill_null(0.0),
                pl.col("contact_kernel_max").fill_null(0.0),
                pl.col("contact_max_kernel_sim").fill_null(0.0),
            ]
        )
        .with_columns(
            (
                BASE_SCORE_WEIGHT * pl.col("base_score")
                + KERNEL_SUM_WEIGHT * pl.col("kernel_sum")
                + KERNEL_MAX_WEIGHT * pl.col("kernel_max")
                + CONTACT_KERNEL_SUM_WEIGHT * pl.col("contact_kernel_sum")
                + CONTACT_KERNEL_MAX_WEIGHT * pl.col("contact_kernel_max")
                + POPULARITY_WEIGHT * pl.col("item_popularity").log1p()
            ).alias("final_score")
        )
    )

    print(f"Writing extended kernel scores: {OUT_KERNEL}", flush=True)
    kernel_scores.sink_parquet(OUT_KERNEL)
    print("Extended kernel scores saved.", flush=True)

    ks = pl.scan_parquet(OUT_KERNEL)

    print("\nKernel score summary:", flush=True)
    print(
        ks.select(
            [
                pl.len().alias("n_rows"),
                pl.col("user_id").n_unique().alias("n_users"),
                pl.col("item_id").n_unique().alias("n_items"),
                pl.col("base_score").mean().alias("base_score_mean"),
                pl.col("kernel_sum").mean().alias("kernel_sum_mean"),
                pl.col("kernel_max").mean().alias("kernel_max_mean"),
                pl.col("contact_kernel_sum").mean().alias("contact_kernel_sum_mean"),
                pl.col("contact_kernel_max").mean().alias("contact_kernel_max_mean"),
                pl.col("final_score").mean().alias("final_score_mean"),
                pl.col("final_score").max().alias("final_score_max"),
            ]
        ).collect(),
        flush=True,
    )


def build_final_submission() -> None:
    print("=" * 80, flush=True)
    print("Step 4: building final top-160 submission", flush=True)
    print("=" * 80, flush=True)

    scored = pl.scan_parquet(OUT_KERNEL).select(["user_id", "item_id", "final_score"])

    users = (
        pl.scan_csv(EVAL_USERS_PATH)
        .select(pl.col("user_id").cast(pl.UInt32))
    )

    seen = (
        pl.scan_parquet(SEEN_EVENTS)
        .select(["user_id", "item_id"])
        .unique()
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
            (0.001 * (1.0 + pl.col("item_popularity").log1p())).alias("final_score")
        )
        .select(["user_id", "item_id", "final_score"])
        .join(seen, on=["user_id", "item_id"], how="anti")
    )

    all_candidates = pl.concat([scored, fallback])

    final = (
        all_candidates
        .group_by(["user_id", "item_id"])
        .agg(pl.col("final_score").max().alias("final_score"))
        .sort(["user_id", "final_score", "item_id"], descending=[False, True, False])
        .with_columns(
            pl.col("final_score")
            .rank(method="ordinal", descending=True)
            .over("user_id")
            .alias("rank")
        )
        .filter(pl.col("rank") <= TOP_FINAL)
        .select(["user_id", "item_id"])
    )

    print(f"Writing submission first: {OUT_SUBMISSION}", flush=True)
    final.collect(engine="streaming").write_csv(OUT_SUBMISSION)

    print("Saved submission. Now computing diagnostics from saved CSV...", flush=True)

    saved = (
        pl.scan_csv(OUT_SUBMISSION)
        .select(
            [
                pl.col("user_id").cast(pl.UInt32),
                pl.col("item_id").cast(pl.UInt32),
            ]
        )
    )

    print("\nFinal submission summary:", flush=True)
    print(
        saved.select(
            [
                pl.len().alias("n_rows"),
                pl.col("user_id").n_unique().alias("n_users"),
                pl.col("item_id").n_unique().alias("n_unique_items"),
            ]
        ).collect(),
        flush=True,
    )

    print("\nRecommendations per user:", flush=True)
    print(
        saved.group_by("user_id")
        .agg(pl.len().alias("n_recs"))
        .select(
            [
                pl.col("n_recs").min().alias("min_recs_per_user"),
                pl.col("n_recs").mean().alias("mean_recs_per_user"),
                pl.col("n_recs").max().alias("max_recs_per_user"),
            ]
        )
        .collect(),
        flush=True,
    )

    print("Done.", flush=True)
    print(f"Saved: {OUT_SUBMISSION}", flush=True)


def main() -> None:
    SUBMISSIONS_DIR.mkdir(parents=True, exist_ok=True)

    print("Building geometry_v4 submission...", flush=True)
    print("Base: geometry_v3", flush=True)
    print("New component: extended contact-aware kernel reranking.", flush=True)
    print(f"TOP_CANDIDATES_PER_USER_BEFORE_KERNEL = {TOP_CANDIDATES_PER_USER_BEFORE_KERNEL}", flush=True)
    print(f"TOP_HISTORY_ATOMS_PER_USER = {TOP_HISTORY_ATOMS_PER_USER}", flush=True)
    print(f"TOP_CONTACT_ATOMS_PER_USER = {TOP_CONTACT_ATOMS_PER_USER}", flush=True)
    print(f"KERNEL_SUM_WEIGHT = {KERNEL_SUM_WEIGHT}", flush=True)
    print(f"KERNEL_MAX_WEIGHT = {KERNEL_MAX_WEIGHT}", flush=True)
    print(f"CONTACT_KERNEL_SUM_WEIGHT = {CONTACT_KERNEL_SUM_WEIGHT}", flush=True)
    print(f"CONTACT_KERNEL_MAX_WEIGHT = {CONTACT_KERNEL_MAX_WEIGHT}", flush=True)

    build_base_candidates()
    prefilter_candidates()
    compute_kernel_scores()
    build_final_submission()


if __name__ == "__main__":
    main()
