"""SmartCart Streamlit storefront and admin dashboard."""

from __future__ import annotations

import streamlit as st

from frontend.utils.api import (
    APIError,
    delete,
    get,
    is_admin,
    is_authenticated,
    login_user,
    logout_user,
    patch,
    post,
    register_user,
)
from frontend.utils.styles import kpi_html, money


def bootstrap_session() -> None:
    """Initialize session keys used across pages."""
    if "page" not in st.session_state:
        st.session_state.page = "Shop"
    if "selected_product" not in st.session_state:
        st.session_state.selected_product = None
    if "coupon_code" not in st.session_state:
        st.session_state.coupon_code = ""


def flash_error(exc: Exception) -> None:
    st.error(str(exc))


def sidebar_nav() -> str:
    with st.sidebar:
        st.markdown(
            '<a href="?page=Shop" class="sc-sidebar-brand" style="text-decoration:none;display:inline-block;cursor:pointer">SmartCart</a>'
            '<p class="sc-sidebar-sub">AI-Powered Shopping</p>',
            unsafe_allow_html=True,
        )
        if st.button("Home · Shop", use_container_width=True, key="brand_home_btn"):
            st.session_state.page = "Shop"
            st.rerun()
        user = st.session_state.get("user")
        if user:
            name = user.get("name") or user.get("full_name") or ""
            st.write(f"Signed in as **{name}**")
            st.caption(user.get("email", ""))
            if st.button("Logout", use_container_width=True):
                logout_user()
                st.rerun()
        pages = [
            "Shop",
            "Cart",
            "Wishlist",
            "Orders",
            "AI Assistant",
            "Address Book",
            "Account",
        ]
        if is_admin():
            pages.extend(["Admin Dashboard", "Admin Catalog", "Analytics"])
        choice = st.radio(
            "Navigate",
            pages,
            index=pages.index(st.session_state.page) if st.session_state.page in pages else 0,
        )
        st.session_state.page = choice
        st.markdown("---")
        st.caption("API · localhost:8904")
        return choice


def page_shop() -> None:
    st.markdown(
        '<div class="sc-hero">'
        '<p class="sc-brand">SmartCart</p>'
        '<p class="sc-tagline">Curated products · Fast checkout · Transparent totals</p>'
        "</div>",
        unsafe_allow_html=True,
    )
    try:
        categories = get("/categories", params={"active_only": True})
        brands = get("/brands", params={"active_only": True})
    except APIError as exc:
        flash_error(exc)
        return

    c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
    with c1:
        q = st.text_input("Search products", placeholder="Headphones, jacket, mug…")
    with c2:
        cat_map = {"All": None}
        cat_map.update({c["name"]: c["id"] for c in categories})
        cat_name = st.selectbox("Category", list(cat_map.keys()))
    with c3:
        brand_map = {"All": None}
        brand_map.update({b["name"]: b["id"] for b in brands})
        brand_name = st.selectbox("Brand", list(brand_map.keys()))
    with c4:
        featured_only = st.checkbox("Featured only")

    params = {"page": 1, "page_size": 24, "active_only": True}
    if q:
        params["q"] = q
    if cat_map[cat_name] is not None:
        params["category_id"] = cat_map[cat_name]
    if brand_map[brand_name] is not None:
        params["brand_id"] = brand_map[brand_name]
    if featured_only:
        params["featured"] = True

    try:
        data = get("/products", params=params)
    except APIError as exc:
        flash_error(exc)
        return

    items = data.get("items", [])
    st.caption(f"{data.get('total', 0)} products")
    if not items:
        st.info("No products found.")
        return

    cols = st.columns(3)
    for idx, product in enumerate(items):
        with cols[idx % 3]:
            st.markdown('<div class="sc-product-card">', unsafe_allow_html=True)
            if product.get("image_url"):
                st.image(product["image_url"], use_container_width=True)
            if product.get("is_featured"):
                st.markdown('<span class="sc-badge">Featured</span>', unsafe_allow_html=True)
            st.subheader(product["name"])
            st.markdown(f'<div class="sc-price">{money(product["price"])}</div>', unsafe_allow_html=True)
            st.caption(f"Stock: {product['stock_quantity']} · SKU {product['sku']}")
            b1, b2 = st.columns(2)
            if b1.button("Details", key=f"d_{product['id']}", use_container_width=True):
                st.session_state.selected_product = product["id"]
                st.session_state.page = "Product Details"
                st.rerun()
            if b2.button("Add", key=f"a_{product['id']}", use_container_width=True):
                if not is_authenticated():
                    st.warning("Please sign in to add items.")
                else:
                    try:
                        post("/cart/items", {"product_id": product["id"], "quantity": 1})
                        st.success("Added to cart")
                    except APIError as exc:
                        flash_error(exc)
            st.markdown("</div>", unsafe_allow_html=True)


def page_product_details() -> None:
    pid = st.session_state.selected_product
    if not pid:
        st.session_state.page = "Shop"
        st.rerun()
    if st.button("← Back to shop"):
        st.session_state.page = "Shop"
        st.rerun()
    try:
        product = get(f"/products/{pid}")
    except APIError as exc:
        flash_error(exc)
        return

    left, right = st.columns([1, 1])
    with left:
        if product.get("image_url"):
            st.image(product["image_url"], use_container_width=True)
    with right:
        st.markdown(
            f'<p class="sc-brand-dark">{product["name"]}</p>',
            unsafe_allow_html=True,
        )
        st.markdown(f'<div class="sc-price">{money(product["price"])}</div>', unsafe_allow_html=True)
        st.write(product.get("description") or "No description.")
        st.caption(
            f"Category: {(product.get('category') or {}).get('name', '—')} · "
            f"Brand: {(product.get('brand') or {}).get('name', '—')}"
        )
        qty = st.number_input("Quantity", min_value=1, max_value=50, value=1)
        c1, c2 = st.columns(2)
        if c1.button("Add to Cart", type="primary", use_container_width=True):
            if not is_authenticated():
                st.warning("Sign in required")
            else:
                try:
                    post("/cart/items", {"product_id": product["id"], "quantity": int(qty)})
                    st.success("Added to cart")
                except APIError as exc:
                    flash_error(exc)
        if c2.button("Wishlist", use_container_width=True):
            if not is_authenticated():
                st.warning("Sign in required")
            else:
                try:
                    post("/wishlist", {"product_id": product["id"]})
                    st.success("Saved to wishlist")
                except APIError as exc:
                    flash_error(exc)

    try:
        images = get(f"/products/{pid}/images")
        if images:
            st.subheader("Gallery")
            cols = st.columns(min(4, len(images)))
            for i, img in enumerate(images):
                cols[i % len(cols)].image(img["url"], use_container_width=True)
    except APIError:
        pass

    try:
        rating = get(f"/products/{pid}/ratings")
        st.write(
            f"Rating: **{rating.get('average_rating', 0)}**/5 "
            f"({rating.get('review_count', 0)} reviews)"
        )
        summary = get(f"/ai/reviews/{pid}/summarize")
        st.caption(summary.get("summary", ""))
    except APIError:
        pass

    st.subheader("Reviews")
    if is_authenticated():
        with st.form("review_form"):
            stars = st.slider("Rating", 1, 5, 5)
            title = st.text_input("Title")
            body = st.text_area("Review")
            if st.form_submit_button("Submit review"):
                try:
                    post(
                        f"/products/{pid}/reviews",
                        {"rating": stars, "title": title, "body": body},
                    )
                    st.success("Review submitted")
                    st.rerun()
                except APIError as exc:
                    flash_error(exc)
    try:
        for rev in get(f"/products/{pid}/reviews"):
            st.write(
                f"{'★' * rev['rating']}{'☆' * (5 - rev['rating'])} — "
                f"**{rev.get('user_name') or 'Customer'}**: {rev.get('title') or ''}"
            )
            if rev.get("body"):
                st.caption(rev["body"])
    except APIError as exc:
        flash_error(exc)

    try:
        similar = get(f"/ai/similar/{pid}")
        if similar.get("recommendations"):
            st.subheader("Similar products")
            for sp in similar["recommendations"]:
                st.write(f"- {sp['name']} · {money(sp['price'])}")
        pred = get(f"/ai/price-prediction/{pid}")
        st.caption(
            f"Price insight: current {money(pred['current_price'])}, "
            f"suggested {money(pred['predicted_price'])} — {pred.get('insight', '')}"
        )
    except APIError:
        pass


def page_cart() -> None:
    st.header("Shopping Cart")
    if not is_authenticated():
        st.warning("Sign in to view your cart.")
        return
    coupon = st.text_input("Coupon code", value=st.session_state.coupon_code)
    try:
        cart = get("/cart")
        if coupon:
            cart = post("/cart/apply-coupon", {"code": coupon})
            st.session_state.coupon_code = coupon
    except APIError as exc:
        flash_error(exc)
        return

    if not cart["items"]:
        st.info("Your cart is empty.")
    else:
        for item in cart["items"]:
            cols = st.columns([3, 1, 1, 1, 1])
            cols[0].write(f"**{item['product']['name']}**")
            cols[1].write(money(item["product"]["price"]))
            new_qty = cols[2].number_input(
                "Qty",
                min_value=1,
                max_value=100,
                value=item["quantity"],
                key=f"qty_{item['id']}",
            )
            cols[3].write(money(item["line_total"]))
            with cols[4]:
                if st.button("Update", key=f"u_{item['id']}"):
                    try:
                        patch(f"/cart/items/{item['id']}", {"quantity": int(new_qty)})
                        st.rerun()
                    except APIError as exc:
                        flash_error(exc)
                if st.button("Save", key=f"s_{item['id']}"):
                    try:
                        post(f"/cart/items/{item['id']}/save-for-later")
                        st.rerun()
                    except APIError as exc:
                        flash_error(exc)
                if st.button("Remove", key=f"r_{item['id']}"):
                    try:
                        delete(f"/cart/items/{item['id']}")
                        st.rerun()
                    except APIError as exc:
                        flash_error(exc)

    if cart.get("saved_for_later"):
        st.subheader("Saved for later")
        for item in cart["saved_for_later"]:
            c1, c2, c3 = st.columns([3, 1, 1])
            c1.write(item["product"]["name"])
            c2.write(money(item["product"]["price"]))
            if c3.button("Move to cart", key=f"m_{item['id']}"):
                try:
                    post(f"/cart/items/{item['id']}/move-to-cart")
                    st.rerun()
                except APIError as exc:
                    flash_error(exc)

    st.markdown("---")
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Subtotal", money(cart["subtotal"]))
    m2.metric("Discount", money(cart["discount_amount"]))
    m3.metric("Shipping", money(cart["shipping_amount"]))
    m4.metric("Tax", money(cart["tax_amount"]))
    m5.metric("Total", money(cart["total"]))

    st.subheader("Checkout")
    user = st.session_state.get("user") or {}
    default_addr = ", ".join(
        filter(
            None,
            [
                user.get("address_line1"),
                user.get("city"),
                user.get("state"),
                user.get("postal_code"),
                user.get("country"),
            ],
        )
    ) or "123 Main St, Springfield, IL 62701, USA"
    address = st.text_area("Shipping address", value=default_addr)
    notes = st.text_input("Order notes (optional)")
    if st.button("Place order & pay", type="primary", disabled=not cart["items"]):
        try:
            result = post(
                "/checkout",
                {
                    "shipping_address": address,
                    "coupon_code": cart.get("coupon_code") or None,
                    "notes": notes or None,
                },
            )
            st.session_state["pending_checkout"] = result
            st.rerun()
        except APIError as exc:
            flash_error(exc)

    pending = st.session_state.get("pending_checkout")
    if pending:
        order = pending["order"]
        st.info(pending.get("message", "Payment initiated"))
        st.write(
            f"Order **{order['order_number']}** · Total **{money(order['total_amount'])}**"
        )
        pay_ok = st.radio(
            "Sandbox payment result",
            ["Success", "Failure"],
            horizontal=True,
            key="pay_result",
        )
        if st.button("Confirm payment", type="primary"):
            try:
                confirmed = post(
                    f"/payments/orders/{order['id']}/confirm",
                    {
                        "payment_intent_id": (order.get("payment") or {}).get(
                            "stripe_payment_intent_id"
                        )
                        or "pi_sim",
                        "success": pay_ok == "Success",
                        "failure_reason": None
                        if pay_ok == "Success"
                        else "Card declined",
                    },
                )
                st.session_state.pop("pending_checkout", None)
                st.session_state.coupon_code = ""
                if confirmed["status"] == "paid":
                    st.success(f"Payment succeeded · Order {confirmed['order_number']}")
                else:
                    st.error(f"Payment failed · Order {confirmed['order_number']}")
                st.session_state.page = "Orders"
                st.rerun()
            except APIError as exc:
                flash_error(exc)


def page_wishlist() -> None:
    st.header("Wishlist")
    if not is_authenticated():
        st.warning("Sign in to view wishlist.")
        return
    try:
        items = get("/wishlist")
    except APIError as exc:
        flash_error(exc)
        return
    if not items:
        st.info("Wishlist is empty.")
        return
    for item in items:
        c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
        c1.write(item["product"]["name"])
        c2.write(money(item["product"]["price"]))
        if c3.button("Add to cart", key=f"wadd_{item['id']}"):
            try:
                post("/cart/items", {"product_id": item["product_id"], "quantity": 1})
                st.success("Added")
            except APIError as exc:
                flash_error(exc)
        if c4.button("Remove", key=f"wrm_{item['id']}"):
            try:
                delete(f"/wishlist/{item['id']}")
                st.rerun()
            except APIError as exc:
                flash_error(exc)


def page_orders() -> None:
    st.header("Your Orders")
    if not is_authenticated():
        st.warning("Sign in to view orders.")
        return
    try:
        orders = get("/orders")
    except APIError as exc:
        flash_error(exc)
        return
    if not orders:
        st.info("No orders yet.")
        return
    for order in orders:
        with st.expander(
            f"{order['order_number']} · {order['status'].upper()} · {money(order['total_amount'])}"
        ):
            st.write(f"Placed: {order['created_at']}")
            st.write(f"Ship to: {order['shipping_address']}")
            for item in order.get("items", []):
                st.write(
                    f"- {item['product_name']} × {item['quantity']} = {money(item['line_total'])}"
                )
            if order.get("payment"):
                st.caption(
                    f"Payment: {order['payment']['status']} via {order['payment']['provider']}"
                )
            c1, c2, c3, c4 = st.columns(4)
            if c1.button("Track", key=f"trk_{order['id']}"):
                try:
                    st.json(get(f"/orders/{order['id']}/track"))
                except APIError as exc:
                    flash_error(exc)
            if c2.button("Invoice", key=f"inv_{order['id']}"):
                st.info(
                    f"PDF: GET /api/v1/orders/{order['id']}/invoice "
                    "(authorize in Swagger to download)"
                )
            if c3.button("Cancel", key=f"can_{order['id']}"):
                try:
                    post(f"/orders/{order['id']}/cancel", {"reason": "Changed mind"})
                    st.success("Cancelled")
                    st.rerun()
                except APIError as exc:
                    flash_error(exc)
            if c4.button("Return", key=f"ret_{order['id']}"):
                try:
                    post(
                        f"/orders/{order['id']}/return",
                        {"reason": "Item not as expected"},
                    )
                    st.success("Return requested")
                    st.rerun()
                except APIError as exc:
                    flash_error(exc)


def page_ai() -> None:
    st.header("AI Shopping Assistant")
    st.caption("Uses OpenAI when `OPENAI_API_KEY` is set; otherwise heuristic recommendations.")
    try:
        status = get("/ai/status")
        st.write(
            f"Provider: **{status.get('provider')}**"
            + (f" · model `{status.get('model')}`" if status.get("model") else "")
        )
    except APIError as exc:
        flash_error(exc)
        return

    intent = st.text_input("What are you shopping for?", placeholder="gift under $50, wireless audio…")
    if st.button("Get recommendations", type="primary"):
        try:
            data = get("/ai/recommendations", params={"query": intent or None, "limit": 4})
            st.info(data.get("message", ""))
            for product in data.get("recommendations", []):
                c1, c2, c3 = st.columns([3, 1, 1])
                c1.write(f"**{product['name']}**")
                c2.write(money(product["price"]))
                if c3.button("Add", key=f"ai_add_{product['id']}"):
                    if not is_authenticated():
                        st.warning("Sign in to add items")
                    else:
                        try:
                            post("/cart/items", {"product_id": product["id"], "quantity": 1})
                            st.success("Added")
                        except APIError as exc:
                            flash_error(exc)
        except APIError as exc:
            flash_error(exc)

    st.subheader("Chat")
    msg = st.text_area("Ask SmartCart", placeholder="Do you have anything for outdoor workouts?")
    if st.button("Send"):
        try:
            reply = post("/ai/chat", {"message": msg})
            st.write(reply.get("reply", ""))
            st.caption(f"via {reply.get('provider')}")
        except APIError as exc:
            flash_error(exc)


def page_addresses() -> None:
    st.header("Address Book")
    if not is_authenticated():
        st.warning("Sign in to manage addresses.")
        return
    with st.form("add_address"):
        label = st.text_input("Label", value="Home")
        full_name = st.text_input("Full name")
        line1 = st.text_input("Address line 1")
        city = st.text_input("City")
        state = st.text_input("State")
        postal = st.text_input("Postal code")
        country = st.text_input("Country", value="USA")
        is_default = st.checkbox("Default")
        if st.form_submit_button("Save address"):
            try:
                post(
                    "/addresses",
                    {
                        "label": label,
                        "full_name": full_name,
                        "line1": line1,
                        "city": city,
                        "state": state,
                        "postal_code": postal,
                        "country": country,
                        "is_default": is_default,
                    },
                )
                st.success("Address saved")
                st.rerun()
            except APIError as exc:
                flash_error(exc)
    try:
        for addr in get("/addresses"):
            st.write(f"**{addr['label']}** — {addr['formatted']}")
            if st.button("Delete", key=f"adel_{addr['id']}"):
                delete(f"/addresses/{addr['id']}")
                st.rerun()
    except APIError as exc:
        flash_error(exc)


def page_account() -> None:
    st.header("Account")
    tabs = st.tabs(["Sign in", "Register", "Profile", "Forgot password"])
    with tabs[0]:
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_pw")
        if st.button("Login", type="primary"):
            try:
                login_user(email, password)
                st.success("Welcome back!")
                st.rerun()
            except APIError as exc:
                flash_error(exc)
        st.caption("Admin demo: admin@smartcart.com / Admin@12345")
    with tabs[1]:
        name = st.text_input("Full name", key="reg_name")
        email = st.text_input("Email", key="reg_email")
        password = st.text_input("Password", type="password", key="reg_pw")
        if st.button("Create account"):
            try:
                register_user(email, password, name)
                st.success("Account created")
                st.rerun()
            except APIError as exc:
                flash_error(exc)
    with tabs[2]:
        if not is_authenticated():
            st.info("Sign in to edit profile.")
        else:
            user = st.session_state["user"]
            full_name = st.text_input("Full name", value=user.get("full_name", ""))
            phone = st.text_input("Phone", value=user.get("phone") or "")
            address = st.text_input("Address", value=user.get("address_line1") or "")
            city = st.text_input("City", value=user.get("city") or "")
            state = st.text_input("State", value=user.get("state") or "")
            postal = st.text_input("Postal code", value=user.get("postal_code") or "")
            country = st.text_input("Country", value=user.get("country") or "USA")
            if st.button("Save profile"):
                try:
                    updated = patch(
                        "/users/me",
                        {
                            "full_name": full_name,
                            "phone": phone or None,
                            "address_line1": address or None,
                            "city": city or None,
                            "state": state or None,
                            "postal_code": postal or None,
                            "country": country or None,
                        },
                    )
                    st.session_state["user"] = updated
                    st.success("Profile updated")
                except APIError as exc:
                    flash_error(exc)
    with tabs[3]:
        fp_email = st.text_input("Account email", key="fp_email")
        if st.button("Send reset token"):
            try:
                result = post("/auth/forgot-password", {"email": fp_email})
                st.success(result.get("message", "Check your email"))
                if result.get("reset_token"):
                    st.code(result["reset_token"])
                    st.session_state["reset_token"] = result["reset_token"]
            except APIError as exc:
                flash_error(exc)
        token = st.text_input("Reset token", value=st.session_state.get("reset_token", ""))
        new_pw = st.text_input("New password", type="password", key="fp_new")
        if st.button("Reset password"):
            try:
                post("/auth/reset-password", {"token": token, "new_password": new_pw})
                st.success("Password updated — sign in with the new password")
            except APIError as exc:
                flash_error(exc)


def page_admin_dashboard() -> None:
    st.markdown(
        '<div class="sc-hero">'
        '<p class="sc-brand">Admin Dashboard</p>'
        '<p class="sc-tagline">Revenue · Orders · Inventory · Coupons</p>'
        "</div>",
        unsafe_allow_html=True,
    )
    if not is_admin():
        st.error("Admin only")
        return
    try:
        dash = get("/analytics/dashboard")
        kpis = dash.get("kpis", {})
        orders = get("/admin/orders", params={"limit": 15})
        customers = get("/admin/customers", params={"limit": 15})
    except APIError as exc:
        flash_error(exc)
        return

    st.markdown('<div class="sc-section-title">Key metrics</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sc-kpi-row">'
        + kpi_html("Today's Revenue", money(kpis.get("today_revenue", 0)), "teal")
        + kpi_html("Monthly Revenue", money(kpis.get("monthly_revenue", 0)), "sky")
        + kpi_html("Total Orders", str(kpis.get("total_orders", 0)), "coral")
        + kpi_html("Users", str(kpis.get("users", 0)), "amber")
        + "</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="sc-kpi-row">'
        + kpi_html("Pending Orders", str(kpis.get("pending_orders", 0)), "amber")
        + kpi_html("Cancelled Orders", str(kpis.get("cancelled_orders", 0)), "coral")
        + kpi_html("Low Stock", str(kpis.get("low_stock_count", 0)), "lime")
        + kpi_html("Active Coupons", str(kpis.get("active_coupons", 0)), "sky")
        + "</div>",
        unsafe_allow_html=True,
    )

    left, right = st.columns(2)
    with left:
        st.markdown('<div class="sc-section-title">Top Products</div>', unsafe_allow_html=True)
        top = dash.get("top_products") or []
        if top:
            import pandas as pd

            st.dataframe(pd.DataFrame(top), use_container_width=True)
        else:
            st.info("No sales yet.")

        st.markdown('<div class="sc-section-title">Low Stock</div>', unsafe_allow_html=True)
        low = dash.get("low_stock") or []
        if low:
            import pandas as pd

            st.dataframe(pd.DataFrame(low), use_container_width=True)
        else:
            st.success("No low-stock items.")

    with right:
        st.markdown('<div class="sc-section-title">Coupons</div>', unsafe_allow_html=True)
        coupons = dash.get("coupons") or []
        if coupons:
            import pandas as pd

            st.dataframe(pd.DataFrame(coupons), use_container_width=True)
        else:
            st.info("No coupons configured.")

        st.markdown('<div class="sc-section-title">Inventory</div>', unsafe_allow_html=True)
        inv = dash.get("inventory") or {}
        st.write(
            f"Products: **{inv.get('total_products', 0)}** · "
            f"Low stock: **{inv.get('low_stock_count', 0)}** · "
            f"Out of stock: **{inv.get('out_of_stock_count', 0)}**"
        )
        items = inv.get("items") or []
        if items:
            import pandas as pd

            st.dataframe(pd.DataFrame(items), use_container_width=True, height=280)

    if dash.get("monthly_orders"):
        st.markdown(
            '<div class="sc-section-title">Monthly revenue & orders</div>',
            unsafe_allow_html=True,
        )
        import pandas as pd

        mdf = pd.DataFrame(dash["monthly_orders"]).set_index("month")
        st.bar_chart(mdf[["revenue", "orders"]])

    st.markdown('<div class="sc-section-title">Manage orders</div>', unsafe_allow_html=True)
    status_opts = [
        "pending",
        "paid",
        "processing",
        "shipped",
        "delivered",
        "cancelled",
        "refunded",
        "return_requested",
        "returned",
    ]
    for order in orders:
        cols = st.columns([2, 1, 1, 2])
        cols[0].write(order["order_number"])
        cols[1].write(order["status"])
        cols[2].write(money(order["total_amount"]))
        idx = status_opts.index(order["status"]) if order["status"] in status_opts else 0
        new_status = cols[3].selectbox(
            "Status",
            status_opts,
            index=idx,
            key=f"ost_{order['id']}",
        )
        if cols[3].button("Update", key=f"ou_{order['id']}"):
            try:
                patch(f"/admin/orders/{order['id']}/status", {"status": new_status})
                st.success("Updated")
                st.rerun()
            except APIError as exc:
                flash_error(exc)

    st.markdown('<div class="sc-section-title">Users</div>', unsafe_allow_html=True)
    for cust in customers:
        name = cust.get("name") or cust.get("full_name") or "—"
        st.write(
            f"{name} · {cust['email']} · "
            f"{'active' if cust['is_active'] else 'inactive'}"
        )

def page_admin_catalog() -> None:
    st.header("Catalog Management")
    if not is_admin():
        st.error("Admin only")
        return
    tab_p, tab_c, tab_b, tab_cp = st.tabs(["Products", "Categories", "Brands", "Coupons"])

    with tab_p:
        with st.form("create_product"):
            st.subheader("Create product")
            name = st.text_input("Name")
            sku = st.text_input("SKU")
            price = st.number_input("Price", min_value=0.01, value=29.99)
            stock = st.number_input("Stock", min_value=0, value=10)
            desc = st.text_area("Description")
            image = st.text_input("Image URL")
            featured = st.checkbox("Featured")
            if st.form_submit_button("Create"):
                try:
                    post(
                        "/products",
                        {
                            "name": name,
                            "sku": sku,
                            "price": price,
                            "stock_quantity": int(stock),
                            "description": desc,
                            "image_url": image or None,
                            "is_featured": featured,
                        },
                    )
                    st.success("Product created")
                except APIError as exc:
                    flash_error(exc)
        try:
            products = get("/products", params={"active_only": False, "page_size": 50})
            for p in products["items"]:
                with st.expander(f"{p['name']} ({p['sku']})"):
                    np = st.number_input("Price", value=float(p["price"]), key=f"pp_{p['id']}")
                    ns = st.number_input("Stock", value=int(p["stock_quantity"]), key=f"ps_{p['id']}")
                    if st.button("Save", key=f"psave_{p['id']}"):
                        patch(f"/products/{p['id']}", {"price": np, "stock_quantity": int(ns)})
                        st.success("Saved")
                    if st.button("Delete", key=f"pdel_{p['id']}"):
                        delete(f"/products/{p['id']}")
                        st.rerun()
        except APIError as exc:
            flash_error(exc)

    with tab_c:
        with st.form("create_cat"):
            cname = st.text_input("Category name")
            cdesc = st.text_input("Description")
            if st.form_submit_button("Add category"):
                try:
                    post("/categories", {"name": cname, "description": cdesc})
                    st.success("Created")
                except APIError as exc:
                    flash_error(exc)
        try:
            for c in get("/categories", params={"active_only": False}):
                st.write(f"{c['id']}: {c['name']}")
        except APIError as exc:
            flash_error(exc)

    with tab_b:
        with st.form("create_brand"):
            bname = st.text_input("Brand name")
            if st.form_submit_button("Add brand"):
                try:
                    post("/brands", {"name": bname})
                    st.success("Created")
                except APIError as exc:
                    flash_error(exc)
        try:
            for b in get("/brands", params={"active_only": False}):
                st.write(f"{b['id']}: {b['name']}")
        except APIError as exc:
            flash_error(exc)

    with tab_cp:
        with st.form("create_coupon"):
            code = st.text_input("Code")
            ctype = st.selectbox("Type", ["percentage", "fixed"])
            value = st.number_input("Value", min_value=0.01, value=10.0)
            if st.form_submit_button("Create coupon"):
                try:
                    post(
                        "/coupons",
                        {
                            "code": code,
                            "coupon_type": ctype,
                            "value": value,
                            "min_order_amount": 0,
                        },
                    )
                    st.success("Coupon created")
                except APIError as exc:
                    flash_error(exc)
        try:
            for c in get("/coupons"):
                st.write(f"{c['code']} · {c['coupon_type']} · {c['value']}")
        except APIError as exc:
            flash_error(exc)


def page_analytics() -> None:
    st.header("Analytics & Reports")
    if not is_admin():
        st.error("Admin only")
        return
    try:
        dash = get("/analytics/dashboard")
        sales = dash["sales"]
        inventory = get("/analytics/inventory")
        overview = dash["overview"]
    except APIError as exc:
        flash_error(exc)
        return

    st.subheader("Sales (30 days)")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Orders", sales["total_orders"])
    c2.metric("Revenue", money(dash["revenue"]))
    c3.metric("AOV", money(sales["average_order_value"]))
    c4.metric("Customers", overview["total_customers"])
    if sales["by_day"]:
        import pandas as pd

        df = pd.DataFrame(sales["by_day"])
        st.line_chart(df.set_index("date")[["revenue", "orders"]])
    else:
        st.info("No paid orders in the selected window yet.")

    st.subheader("Best sellers")
    st.table(dash.get("best_sellers") or [])

    st.subheader("Monthly orders")
    import pandas as pd

    st.bar_chart(pd.DataFrame(dash["monthly_orders"]).set_index("month")[["orders", "revenue"]])

    st.subheader("Customer growth")
    st.line_chart(
        pd.DataFrame(dash["customer_growth"]).set_index("month")[["new_customers"]]
    )

    st.subheader("Low stock")
    st.dataframe(pd.DataFrame(dash.get("low_stock") or []), use_container_width=True)

    st.subheader("Inventory")
    st.write(
        f"Total: {inventory['total_products']} · "
        f"Low stock: {inventory['low_stock_count']} · "
        f"Out of stock: {inventory['out_of_stock_count']}"
    )
    st.dataframe(pd.DataFrame(inventory["items"]), use_container_width=True)


def main() -> None:
    page = sidebar_nav()
    # Allow product details override
    if st.session_state.page == "Product Details":
        page_product_details()
        return
    routes = {
        "Shop": page_shop,
        "Cart": page_cart,
        "Wishlist": page_wishlist,
        "Orders": page_orders,
        "AI Assistant": page_ai,
        "Address Book": page_addresses,
        "Account": page_account,
        "Admin Dashboard": page_admin_dashboard,
        "Admin Catalog": page_admin_catalog,
        "Analytics": page_analytics,
    }
    routes.get(page, page_shop)()


