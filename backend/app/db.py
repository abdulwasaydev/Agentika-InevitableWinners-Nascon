"""Local SQLite persistence for jobs, evidence, reviews, and lineage."""

import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.engine import Engine, URL
from sqlalchemy.orm import Session, sessionmaker

from .models import Base

BACKEND_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_DIR / ".env")


def local_db_path() -> Path:
    configured = os.getenv("VERITAS_DB_PATH")
    return Path(configured).expanduser().resolve() if configured else BACKEND_DIR / "data" / "veritas.sqlite3"


def database_url() -> str:
    return str(URL.create("sqlite", database=str(local_db_path())))


def make_engine(url: str | None = None) -> Engine:
    if url is not None and not url.startswith("sqlite:///"):
        raise ValueError("Only a local SQLite database is supported")
    if url is None:
        local_db_path().parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(url or database_url(), connect_args={"check_same_thread": False, "timeout": 30})

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _record):
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


def database_ready(engine: Engine | None) -> bool:
    if engine is None:
        return False
    try:
        Base.metadata.create_all(engine)
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        inspector = inspect(engine)
        return all(inspector.has_table(name) for name in Base.metadata.tables)
    except Exception:
        return False


def session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)
