"""SmartCart Home — Streamlit entrypoint."""

from __future__ import annotations

import streamlit as st

from frontend.lib import (
    bootstrap_session,
    page_account,
    page_addresses,
    sidebar_nav,
)
from frontend.utils.styles import CUSTOM_CSS
from frontend import Admin, Cart, Checkout, Products

st.set_page_config(
    page_title="SmartCart",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
bootstrap_session()


def run() -> None:
    page = sidebar_nav()
    if st.session_state.page == "Product Details":
        Products.render_details()
        return

    routes = {
        "Shop": Products.render_shop,
        "Cart": Cart.render,
        "Wishlist": Products.render_wishlist,
        "Orders": Checkout.render_orders,
        "AI Assistant": Products.render_ai,
        "Address Book": page_addresses,
        "Account": page_account,
        "Admin Dashboard": Admin.render_dashboard,
        "Admin Catalog": Admin.render_catalog,
        "Analytics": Admin.render_analytics,
    }
    # Checkout is reachable from Cart page actions; also expose via Shop total flow
    if page == "Cart":
        Cart.render()
        Checkout.render_checkout_panel()
        return
    routes.get(page, Products.render_shop)()


if __name__ == "__main__":
    run()
