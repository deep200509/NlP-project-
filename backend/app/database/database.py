from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import DATABASE_URL

# engine = the actual connection to the SQLite file
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # needed for SQLite + FastAPI
)

# each request gets its own session (a "conversation" with the DB)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    """All our database tables will inherit from this later."""


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()