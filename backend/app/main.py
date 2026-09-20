from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.config import APP_NAME, APP_VERSION
from app.database.database import Base, engine
from app.nlp.routes import router as nlp_router

# create tables (none yet - they arrive later)
Base.metadata.create_all(bind=engine)

app = FastAPI(title=APP_NAME, version=APP_VERSION)

# lets the React frontend (later phase) call this server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Phase 2: NLP endpoints (/nlp/preprocess and /nlp/intent)
app.include_router(nlp_router)


@app.get("/")
def root():
    return {"message": f"{APP_NAME} is running", "docs": "/docs"}


@app.get("/health")
def health():
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))  # proves the DB is reachable
    return {"status": "ok", "database": "connected", "version": APP_VERSION}