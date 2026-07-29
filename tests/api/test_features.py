"""Tests for newly added feature endpoints."""


def test_forgot_password_flow(client, auth_headers):
    resp = client.post(
        "/api/v1/auth/forgot-password", json={"email": "customer@example.com"}
    )
    assert resp.status_code == 200
    token = resp.json().get("reset_token")
    assert token
    reset = client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "new_password": "NewPass@12345"},
    )
    assert reset.status_code == 200
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "customer@example.com", "password": "NewPass@12345"},
    )
    assert login.status_code == 200


def test_address_book(client, auth_headers):
    created = client.post(
        "/api/v1/addresses",
        headers=auth_headers,
        json={
            "label": "Home",
            "full_name": "Test Customer",
            "line1": "123 Main St",
            "city": "Springfield",
            "state": "IL",
            "postal_code": "62701",
            "country": "USA",
            "is_default": True,
        },
    )
    assert created.status_code == 201
    listed = client.get("/api/v1/addresses", headers=auth_headers)
    assert listed.status_code == 200
    assert len(listed.json()) >= 1


def test_reviews_and_ratings(client, auth_headers):
    product_id = client.get("/api/v1/products").json()["items"][0]["id"]
    created = client.post(
        f"/api/v1/products/{product_id}/reviews",
        headers=auth_headers,
        json={"rating": 5, "title": "Great", "body": "Loved it"},
    )
    assert created.status_code == 201
    ratings = client.get(f"/api/v1/products/{product_id}/ratings")
    assert ratings.status_code == 200
    assert ratings.json()["review_count"] >= 1
    summary = client.get(f"/api/v1/ai/reviews/{product_id}/summarize")
    assert summary.status_code == 200


def test_cancel_and_invoice(client, auth_headers):
    product_id = client.get("/api/v1/products").json()["items"][0]["id"]
    client.post(
        "/api/v1/cart/items",
        headers=auth_headers,
        json={"product_id": product_id, "quantity": 1},
    )
    checkout = client.post(
        "/api/v1/checkout",
        headers=auth_headers,
        json={"shipping_address": "123 Test Lane, Test City, TS 00000, USA"},
    )
    order_id = checkout.json()["order"]["id"]
    invoice = client.get(f"/api/v1/orders/{order_id}/invoice", headers=auth_headers)
    assert invoice.status_code == 200
    assert invoice.headers["content-type"].startswith("application/pdf")
    cancelled = client.post(
        f"/api/v1/orders/{order_id}/cancel",
        headers=auth_headers,
        json={"reason": "Changed mind"},
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] in {"cancelled", "refunded"}


def test_ai_similar_and_price(client):
    product_id = client.get("/api/v1/products").json()["items"][0]["id"]
    similar = client.get(f"/api/v1/ai/similar/{product_id}")
    assert similar.status_code == 200
    price = client.get(f"/api/v1/ai/price-prediction/{product_id}")
    assert price.status_code == 200
    assert "predicted_price" in price.json()


def test_analytics_dashboard(client, admin_headers):
    resp = client.get("/api/v1/analytics/dashboard", headers=admin_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert "kpis" in body
    kpis = body["kpis"]
    for key in (
        "today_revenue",
        "monthly_revenue",
        "total_orders",
        "pending_orders",
        "cancelled_orders",
        "users",
    ):
        assert key in kpis
    assert "top_products" in body
    assert "low_stock" in body
    assert "coupons" in body
    assert "inventory" in body
