"""Database configuration; no implicit SQLite or in-memory fallback."""

import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from .models import Base

load_dotenv(Path(__file__).resolve().parents[1] / ".env")


def database_url() -> str | None:
    return os.getenv("DATABASE_URL") or None


def make_engine(url: str | None = None) -> Engine | None:
    url = url or database_url()
    if not url:
        return None
    if not url.startswith("postgresql+psycopg://"):
        raise ValueError("DATABASE_URL must use PostgreSQL with psycopg")
    return create_engine(url, pool_pre_ping=True, pool_size=3, max_overflow=0)


def database_ready(engine: Engine | None) -> bool:
    if engine is None:
        return False
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        inspector = inspect(engine)
        if not all(inspector.has_table(name) for name in Base.metadata.tables) or not inspector.has_table("alembic_version"):
            return False
        with engine.connect() as connection:
            return connection.scalar(text("SELECT version_num FROM alembic_version")) == "0003_comparison"
    except Exception:
        return False


def session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)
