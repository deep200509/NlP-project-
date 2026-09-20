import os
import secrets
from pathlib import Path

# backend/ folder (two levels up from this file)
BASE_DIR = Path(__file__).resolve().parent.parent
# api-agent/ folder (one more level up)
PROJECT_DIR = BASE_DIR.parent

DATA_DIR = BASE_DIR / "data"          # SQLite file + secret key
MODELS_DIR = BASE_DIR / "models"      # trained ML models
REPORTS_DIR = BASE_DIR / "reports"    # metrics + confusion matrix for your report
DATASETS_DIR = PROJECT_DIR / "datasets"

for folder in (DATA_DIR, MODELS_DIR, REPORTS_DIR):
    folder.mkdir(exist_ok=True)

APP_NAME = "AI API Generator Agent"
APP_VERSION = "0.7.0"
DATABASE_URL = f"sqlite:///{(DATA_DIR / 'app.db').as_posix()}"

# NLP settings
SPACY_MODEL = "en_core_web_md"
INTENT_DATASET_PATH = DATASETS_DIR / "intent_dataset.csv"
INTENT_MODEL_PATH = MODELS_DIR / "intent_classifier.joblib"


# Authentication settings
def _load_secret_key() -> str:
    """
    The key that signs login tokens. It must never be written in the code or pushed to GitHub.
    Order: SECRET_KEY environment variable -> data/secret.key (created once, randomly).
    """
    from_environment = os.getenv("SECRET_KEY")
    if from_environment:
        return from_environment
    key_file = DATA_DIR / "secret.key"
    if not key_file.exists():
        key_file.write_text(secrets.token_hex(32), encoding="utf-8")
    return key_file.read_text(encoding="utf-8").strip()


SECRET_KEY = _load_secret_key()
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_MINUTES = 60 * 12        # a login stays valid for 12 hours