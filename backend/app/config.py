from pathlib import Path

# backend/ folder (two levels up from this file)
BASE_DIR = Path(__file__).resolve().parent.parent
# api-agent/ folder (one more level up)
PROJECT_DIR = BASE_DIR.parent

DATA_DIR = BASE_DIR / "data"          # SQLite file
MODELS_DIR = BASE_DIR / "models"      # trained ML models
REPORTS_DIR = BASE_DIR / "reports"    # metrics + confusion matrix for your report
DATASETS_DIR = PROJECT_DIR / "datasets"

for folder in (DATA_DIR, MODELS_DIR, REPORTS_DIR):
    folder.mkdir(exist_ok=True)

APP_NAME = "AI API Generator Agent"
APP_VERSION = "0.2.0"
DATABASE_URL = f"sqlite:///{(DATA_DIR / 'app.db').as_posix()}"

# NLP settings
SPACY_MODEL = "en_core_web_md"
INTENT_DATASET_PATH = DATASETS_DIR / "intent_dataset.csv"
INTENT_MODEL_PATH = MODELS_DIR / "intent_classifier.joblib"