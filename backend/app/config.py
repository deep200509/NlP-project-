from pathlib import Path

# backend/ folder (two levels up from this file)
BASE_DIR = Path(__file__).resolve().parent.parent

# folder where the SQLite file lives
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

APP_NAME = "AI API Generator Agent"
APP_VERSION = "0.1.0"
DATABASE_URL = f"sqlite:///{(DATA_DIR / 'app.db').as_posix()}"