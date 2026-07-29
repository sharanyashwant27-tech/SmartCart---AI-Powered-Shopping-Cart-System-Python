"""Shared utilities."""

import re
import uuid
from datetime import datetime, timezone


def slugify(value: str) -> str:
    """Convert a string into a URL-safe slug."""
    value = value.lower().strip()
    value = re.sub(r"[^\w\s-]", "", value)
    value = re.sub(r"[\s_-]+", "-", value)
    return value.strip("-")[:140]


def generate_order_number() -> str:
    """Generate a unique order number."""
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"SC-{stamp}-{uuid.uuid4().hex[:6].upper()}"


def format_address(
    line1: str | None,
    line2: str | None,
    city: str | None,
    state: str | None,
    postal_code: str | None,
    country: str | None,
) -> str:
    """Join address parts into a single string."""
    parts = [p for p in [line1, line2, city, state, postal_code, country] if p]
    return ", ".join(parts)
