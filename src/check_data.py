import polars as pl

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from configs.paths import (
    ITEM_FEATURES_PATH,
    EVAL_USER_EVENTS_PATH,
    EVAL_USERS_PATH,
    CONTACT_EIDS_PATH,
)


def check_exists(path: Path) -> None:
    if path.exists():
        size_mb = path.stat().st_size / 1024 / 1024
        print(f"[OK] {path.name}: {size_mb:.2f} MB")
    else:
        print(f"[MISSING] {path}")


def preview_parquet(path: Path, name: str) -> None:
    print("\n" + "=" * 80)
    print(name)
    print("=" * 80)

    if not path.exists():
        print(f"File not found: {path}")
        return

    df = pl.scan_parquet(path)
    print("Schema:")
    print(df.collect_schema())

    head = df.head(5).collect()
    print("\nHead:")
    print(head)

    n_rows = df.select(pl.len()).collect().item()
    print(f"\nRows: {n_rows:,}")


def preview_csv(path: Path, name: str) -> None:
    print("\n" + "=" * 80)
    print(name)
    print("=" * 80)

    if not path.exists():
        print(f"File not found: {path}")
        return

    df = pl.scan_csv(path)
    print("Schema:")
    print(df.collect_schema())

    head = df.head(5).collect()
    print("\nHead:")
    print(head)

    n_rows = df.select(pl.len()).collect().item()
    print(f"\nRows: {n_rows:,}")


def main() -> None:
    print("Checking raw files...\n")

    for path in [
        ITEM_FEATURES_PATH,
        EVAL_USER_EVENTS_PATH,
        EVAL_USERS_PATH,
        CONTACT_EIDS_PATH,
    ]:
        check_exists(path)

    preview_parquet(ITEM_FEATURES_PATH, "item_features.parquet")
    preview_parquet(EVAL_USER_EVENTS_PATH, "eval_user_events.pq")
    preview_csv(EVAL_USERS_PATH, "eval_users.csv")
    preview_csv(CONTACT_EIDS_PATH, "contact_eids.csv")


if __name__ == "__main__":
    main()
