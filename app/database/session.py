"""Database engine, session factory, and base model."""

from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings


def normalize_database_url(url: str) -> str:
    """Normalize provider URLs (Render/Railway) for SQLAlchemy + psycopg2."""
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg2://", 1)
    if url.startswith("postgresql://") and "+psycopg2" not in url:
        return url.replace("postgresql://", "postgresql+psycopg2://", 1)
    return url


settings = get_settings()
DATABASE_URL = normalize_database_url(settings.database_url)

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    echo=False,
    pool_pre_ping=True,
)


@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record) -> None:  # noqa: ARG001
    """Enable foreign keys for SQLite connections."""
    if DATABASE_URL.startswith("sqlite"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """SQLAlchemy declarative base for all models."""


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a DB session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all tables (used for local bootstrap; Alembic preferred in prod)."""
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _ensure_loyalty_columns()


def _ensure_loyalty_columns() -> None:
    """SQLite-friendly patches for existing databases (create_all won't ALTER)."""
    from sqlalchemy import inspect, text

    insp = inspect(engine)
    tables = set(insp.get_table_names())
    with engine.begin() as conn:
        if "users" in tables:
            cols = {c["name"] for c in insp.get_columns("users")}
            if "loyalty_points" not in cols:
                conn.execute(
                    text(
                        "ALTER TABLE users ADD COLUMN loyalty_points "
                        "INTEGER NOT NULL DEFAULT 0"
                    )
                )
        if "orders" in tables:
            cols = {c["name"] for c in insp.get_columns("orders")}
            if "points_earned" not in cols:
                conn.execute(
                    text(
                        "ALTER TABLE orders ADD COLUMN points_earned "
                        "INTEGER NOT NULL DEFAULT 0"
                    )
                )
            if "points_redeemed" not in cols:
                conn.execute(
                    text(
                        "ALTER TABLE orders ADD COLUMN points_redeemed "
                        "INTEGER NOT NULL DEFAULT 0"
                    )
                )
