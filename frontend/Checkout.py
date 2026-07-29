"""Checkout and orders page module."""

from __future__ import annotations

from frontend.lib import page_orders


def render_orders() -> None:
    page_orders()


def render_checkout_panel() -> None:
    """Checkout UI is embedded inside the cart page flow in lib.page_cart."""
    # Intentionally empty — page_cart already includes checkout.
    return
