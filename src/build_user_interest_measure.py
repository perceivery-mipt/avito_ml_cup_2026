import polars as pl
from pathlib import Path
import sys
import math

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from configs.paths import CONTACT_EIDS_PATH, INTERIM_DIR

EVENTS_GEOMETRY_PATH = INTERIM_DIR / "eval_events_geometry.parquet"
OUT_PATH = INTERIM_DIR / "user_interest_measure.parquet"

# Half-life in days: через столько дней вклад события уменьшается в 2 раза.
HALF_LIFE_DAYS = 7.0
MS_PER_DAY = 24 * 60 * 60 * 1000
LAMBDA = math.log(2.0) / HALF_LIFE_DAYS


def main() -> None:
    print("Building user interest measure...")
    print(f"Source: {EVENTS_GEOMETRY_PATH}")
    print(f"Target: {OUT_PATH}")
    print(f"Half-life days: {HALF_LIFE_DAYS}")

    contact_eids = (
        pl.read_csv(CONTACT_EIDS_PATH)
        .get_column("mapped_eid")
        .cast(pl.UInt16)
        .to_list()
    )

    print(f"Contact eids: {contact_eids}")

    events = pl.scan_parquet(EVENTS_GEOMETRY_PATH)

    # Берём максимальный timestamp в eval_user_events как локальный cutoff для затухания.
    # Для первого бейзлайна это нормальная приближённая шкала свежести.
    max_ts = events.select(pl.col("timestamp").max()).collect().item()
    print(f"Max timestamp in eval history: {max_ts}")

    weighted = (
        events
        .with_columns(
            [
                ((pl.lit(max_ts) - pl.col("timestamp")) / MS_PER_DAY).alias("age_days"),
                pl.when(pl.col("eid").is_in(contact_eids))
                .then(8.0)
                .when(pl.col("eid") == 7)
                .then(1.0)
                .when(pl.col("eid") == 10)
                .then(2.0)
                .otherwise(3.0)
                .alias("event_alpha"),
            ]
        )
        .with_columns(
            [
                (
                    pl.col("event_alpha")
                    * (-LAMBDA * pl.col("age_days")).exp()
                ).alias("event_weight")
            ]
        )
        .select(
            [
                "user_id",
                "item_id",
                "eid",
                "timestamp",
                "age_days",
                "event_alpha",
                "event_weight",
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

    weighted.sink_parquet(OUT_PATH)

    print("Saved weighted event measure.")

    measure = pl.scan_parquet(OUT_PATH)

    print("\nWeight summary:")
    print(
        measure.select(
            [
                pl.len().alias("n_atoms"),
                pl.col("event_weight").min().alias("weight_min"),
                pl.col("event_weight").mean().alias("weight_mean"),
                pl.col("event_weight").max().alias("weight_max"),
                pl.col("age_days").min().alias("age_min"),
                pl.col("age_days").mean().alias("age_mean"),
                pl.col("age_days").max().alias("age_max"),
            ]
        ).collect()
    )

    print("\nMass by eid:")
    print(
        measure
        .group_by("eid")
        .agg(
            [
                pl.len().alias("n_events"),
                pl.col("event_weight").sum().alias("total_mass"),
                pl.col("event_weight").mean().alias("mean_weight"),
            ]
        )
        .sort("total_mass", descending=True)
        .collect()
    )

    print("\nMass by vertical:")
    print(
        measure
        .group_by("vertical_id")
        .agg(
            [
                pl.len().alias("n_events"),
                pl.col("event_weight").sum().alias("total_mass"),
            ]
        )
        .sort("vertical_id")
        .collect()
    )

    print("\nHead:")
    print(measure.head(5).collect())


if __name__ == "__main__":
    main()
