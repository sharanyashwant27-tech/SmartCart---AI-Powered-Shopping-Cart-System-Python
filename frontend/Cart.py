"""Cart page module."""

from __future__ import annotations

import streamlit as st

from frontend.lib import flash_error, page_cart
from frontend.utils.api import APIError, get, is_authenticated, post
from frontend.utils.styles import money


def render() -> None:
    """Render cart line items and totals (checkout panel lives in Checkout.py)."""
    page_cart()


def render_summary_only() -> None:
    if not is_authenticated():
        st.warning("Sign in to view your cart.")
        return
    try:
        cart = get("/cart")
    except APIError as exc:
        flash_error(exc)
        return
    st.metric("Items", cart.get("item_count", 0))
    st.metric("Total", money(cart.get("total", 0)))
