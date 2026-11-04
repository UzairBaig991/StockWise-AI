from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
DB_PATH = ROOT_DIR / "data" / "stockwise.db"
MODELS_DIR = ROOT_DIR / "models"
DATA_DIR = ROOT_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
DEMO_DATA_DIR = DATA_DIR / "demo"

DEFAULT_MIN_HISTORY_DAYS = 14
DEFAULT_TOP_N_PRODUCTS = 15
MODEL_METADATA_PATH = MODELS_DIR / "model_metadata.json"
