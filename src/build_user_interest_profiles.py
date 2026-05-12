import polars as pl
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from configs.paths import INTERIM_DIR

MEASURE_PATH = INTERIM_DIR / "user_interest_measure.parquet"

OUT_USER_VCR = INTERIM_DIR / "user_profile_vertical_category_region.parquet"
OUT_USER_VC = INTERIM_DIR / "user_profile_vertical_category.parquet"
OUT_USER_VSID01 = INTERIM_DIR / "user_profile_vertical_sid01.parquet"
OUT_USER_VSID012 = INTERIM_DIR / "user_profile_vertical_sid012.parquet"
OUT_USER_RSID01 = INTERIM_DIR / "user_profile_region_sid01.parquet"


def aggregate_profile(keys: list[str], out_path: Path, top_k_per_user: int = 20) -> None:
    print("\n" + "=" * 80)
    print(f"Building profile: {out_path.name}")
    print(f"Keys: {keys}")
    print("=" * 80)

    measure = pl.scan_parquet(MEASURE_PATH)

    profile = (
        measure
        .group_by(["user_id", *keys])
        .agg(
            [
                pl.col("event_weight").sum().alias("mass"),
                pl.len().alias("n_events"),
                pl.col("timestamp").max().alias("last_timestamp"),
            ]
        )
        .sort(["user_id", "mass"], descending=[False, True])
        .with_columns(
            pl.col("mass")
            .rank(method="ordinal", descending=True)
            .over("user_id")
            .alias("rank_in_user")
        )
        .filter(pl.col("rank_in_user") <= top_k_per_user)
        .drop("rank_in_user")
    )

    profile.sink_parquet(out_path)

    df = pl.scan_parquet(out_path)

    summary = df.select(
        [
            pl.len().alias("n_rows"),
            pl.col("user_id").n_unique().alias("n_users"),
            pl.col("mass").min().alias("mass_min"),
            pl.col("mass").mean().alias("mass_mean"),
            pl.col("mass").max().alias("mass_max"),
        ]
    ).collect()

    print("Summary:")
    print(summary)

    print("\nHead:")
    print(df.head(10).collect())


def main() -> None:
    print("Building user interest profiles from measure...")
    print(f"Source: {MEASURE_PATH}")

    aggregate_profile(
        keys=["vertical_id", "category_ext_y", "region_id_y"],
        out_path=OUT_USER_VCR,
        top_k_per_user=20,
    )

    aggregate_profile(
        keys=["vertical_id", "category_ext_y"],
        out_path=OUT_USER_VC,
        top_k_per_user=20,
    )

    aggregate_profile(
        keys=["vertical_id", "sid_0_y", "sid_1_y"],
        out_path=OUT_USER_VSID01,
        top_k_per_user=30,
    )

    aggregate_profile(
        keys=["vertical_id", "sid_0_y", "sid_1_y", "sid_2_y"],
        out_path=OUT_USER_VSID012,
        top_k_per_user=30,
    )

    aggregate_profile(
        keys=["region_id_y", "sid_0_y", "sid_1_y"],
        out_path=OUT_USER_RSID01,
        top_k_per_user=30,
    )

    print("\nDone.")


if __name__ == "__main__":
    main()
