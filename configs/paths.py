from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
INTERIM_DIR = DATA_DIR / "interim"
PROCESSED_DIR = DATA_DIR / "processed"
SUBMISSIONS_DIR = DATA_DIR / "submissions"

REPORTS_DIR = PROJECT_ROOT / "reports"

ITEM_FEATURES_PATH = RAW_DIR / "item_features.parquet"
EVAL_USER_EVENTS_PATH = RAW_DIR / "eval_user_events.pq"
EVAL_USERS_PATH = RAW_DIR / "eval_users.csv"
CONTACT_EIDS_PATH = RAW_DIR / "contact_eids.csv"
