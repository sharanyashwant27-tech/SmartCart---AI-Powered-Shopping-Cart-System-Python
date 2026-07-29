"""Products page module."""

from __future__ import annotations

from frontend.lib import page_ai, page_product_details, page_shop, page_wishlist


def render_shop() -> None:
    page_shop()


def render_details() -> None:
    page_product_details()


def render_wishlist() -> None:
    page_wishlist()


def render_ai() -> None:
    page_ai()
