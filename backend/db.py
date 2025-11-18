from sqlmodel import SQLModel, create_engine, Session
import os

PG_HOST = os.getenv("PG_HOST", "postgres")
PG_PORT = os.getenv("PG_PORT", "5432")
PG_USER = os.getenv("PG_USER", "appuser")
PG_PASSWORD = os.getenv("PG_PASSWORD", "apppass")
PG_DB = os.getenv("PG_DB", "appdb")

DATABASE_URL = (
    f"postgresql://{PG_USER}:{PG_PASSWORD}@{PG_HOST}:{PG_PORT}/{PG_DB}"
)

engine = create_engine(DATABASE_URL, echo=False)


def init_db():
    """Create all tables if they don't exist."""
    SQLModel.metadata.create_all(engine)


def get_session():
    """Provide a new SQLModel session."""
    return Session(engine)
