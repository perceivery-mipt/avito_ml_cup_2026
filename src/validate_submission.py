import argparse
import polars as pl
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from configs.paths import EVAL_USERS_PATH, INTERIM_DIR, SUBMISSIONS_DIR

DEFAULT_SUBMISSION_PATH = SUBMISSIONS_DIR / "submission_geometry_v1.csv"
ITEM_GEOMETRY_PATH = INTERIM_DIR / "item_geometry_eval_verticals.parquet"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--submission",
        type=str,
        default=str(DEFAULT_SUBMISSION_PATH),
        help="Path to submission CSV file.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    submission_path = Path(args.submission)

    print(f"Validating submission: {submission_path}")

    sub = (
        pl.scan_csv(submission_path)
        .select(
            [
                pl.col("user_id").cast(pl.UInt32),
                pl.col("item_id").cast(pl.UInt32),
            ]
        )
    )

    users = (
        pl.scan_csv(EVAL_USERS_PATH)
        .select(pl.col("user_id").cast(pl.UInt32))
    )

    items = (
        pl.scan_parquet(ITEM_GEOMETRY_PATH)
        .select("item_id")
        .unique()
    )

    print("\nSubmission summary:")
    print(
        sub.select(
            [
                pl.len().alias("n_rows"),
                pl.col("user_id").n_unique().alias("n_users"),
                pl.col("item_id").n_unique().alias("n_items"),
            ]
        ).collect()
    )

    print("\nRecommendations per user:")
    rec_counts = sub.group_by("user_id").agg(pl.len().alias("n_recs"))

    print(
        rec_counts.select(
            [
                pl.col("n_recs").min().alias("min_recs"),
                pl.col("n_recs").mean().alias("mean_recs"),
                pl.col("n_recs").max().alias("max_recs"),
            ]
        ).collect()
    )

    print("\nUsers without recommendations:")
    missing_users = users.join(
        sub.select("user_id").unique(),
        on="user_id",
        how="anti",
    )
    print(missing_users.select(pl.len().alias("n_missing_users")).collect())

    print("\nUnknown users in submission:")
    unknown_users = sub.select("user_id").unique().join(
        users,
        on="user_id",
        how="anti",
    )
    print(unknown_users.select(pl.len().alias("n_unknown_users")).collect())

    print("\nDuplicate user-item pairs:")
    duplicated_pairs = (
        sub.group_by(["user_id", "item_id"])
        .agg(pl.len().alias("n"))
        .filter(pl.col("n") > 1)
    )
    print(duplicated_pairs.select(pl.len().alias("n_duplicate_pairs")).collect())

    print("\nUsers with more than 160 recommendations:")
    too_many = rec_counts.filter(pl.col("n_recs") > 160)
    print(too_many.select(pl.len().alias("n_users_too_many")).collect())

    print("\nUnknown item_id in submission:")
    unknown_items = sub.select("item_id").unique().join(
        items,
        on="item_id",
        how="anti",
    )
    print(unknown_items.select(pl.len().alias("n_unknown_items")).collect())

    print("\nHead:")
    print(sub.head(10).collect())

    print("\nValidation done.")


if __name__ == "__main__":
    main()
