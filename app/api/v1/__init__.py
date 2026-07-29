"""Legacy shim — prefer `app.api.router`."""

from app.api.router import api_router

__all__ = ["api_router"]
