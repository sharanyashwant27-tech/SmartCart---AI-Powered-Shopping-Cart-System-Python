"""Compatibility shims for legacy `app.core.*` imports."""

from app.config import Settings, get_settings
from app.database import Base, get_db, init_db
from app.utils.logging import get_logger, setup_logging

__all__ = [
    "Settings",
    "get_settings",
    "Base",
    "get_db",
    "init_db",
    "get_logger",
    "setup_logging",
]
