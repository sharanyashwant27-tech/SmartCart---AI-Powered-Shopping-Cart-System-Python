"""API integration tests."""

from decimal import Decimal


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_register_and_login(client):
    reg = client.post(
        "/api/v1/auth/register",
        json={
            "email": "newuser@example.com",
            "password": "Password@123",
            "full_name": "New User",
        },
    )
    assert reg.status_code == 201
    assert "access_token" in reg.json()

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "newuser@example.com", "password": "Password@123"},
    )
    assert login.status_code == 200
    me = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {login.json()['access_token']}"},
    )
    assert me.status_code == 200
    assert me.json()["email"] == "newuser@example.com"


def test_list_products(client):
    resp = client.get("/api/v1/products")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1
    assert body["items"][0]["sku"] == "TEST-001"


def test_cart_flow(client, auth_headers):
    products = client.get("/api/v1/products").json()["items"]
    pid = products[0]["id"]

    add = client.post(
        "/api/v1/cart/items",
        headers=auth_headers,
        json={"product_id": pid, "quantity": 2},
    )
    assert add.status_code == 201

    cart = client.get("/api/v1/cart", headers=auth_headers)
    assert cart.status_code == 200
    assert cart.json()["item_count"] == 2
    assert Decimal(str(cart.json()["subtotal"])) == Decimal("50.00")

    item_id = cart.json()["items"][0]["id"]
    upd = client.patch(
        f"/api/v1/cart/items/{item_id}",
        headers=auth_headers,
        json={"quantity": 3},
    )
    assert upd.status_code == 200

    coupon = client.post(
        "/api/v1/cart/apply-coupon",
        headers=auth_headers,
        json={"code": "TEST10"},
    )
    assert coupon.status_code == 200
    assert Decimal(str(coupon.json()["discount_amount"])) > 0

    save = client.post(
        f"/api/v1/cart/items/{item_id}/save-for-later",
        headers=auth_headers,
    )
    assert save.status_code == 200


def test_checkout_and_payment(client, auth_headers):
    products = client.get("/api/v1/products").json()["items"]
    pid = products[0]["id"]
    client.post(
        "/api/v1/cart/items",
        headers=auth_headers,
        json={"product_id": pid, "quantity": 1},
    )
    checkout = client.post(
        "/api/v1/checkout",
        headers=auth_headers,
        json={"shipping_address": "123 Test Lane, Test City, TS 00000, USA"},
    )
    assert checkout.status_code == 201
    order = checkout.json()["order"]
    assert order["status"] == "pending"
    intent = order["payment"]["stripe_payment_intent_id"]

    paid = client.post(
        f"/api/v1/payments/orders/{order['id']}/confirm",
        headers=auth_headers,
        json={"payment_intent_id": intent, "success": True},
    )
    assert paid.status_code == 200
    assert paid.json()["status"] == "paid"


def test_admin_analytics(client, admin_headers):
    overview = client.get("/api/v1/analytics/overview", headers=admin_headers)
    assert overview.status_code == 200
    assert "total_products" in overview.json()

    sales = client.get("/api/v1/analytics/sales", headers=admin_headers)
    assert sales.status_code == 200

    inventory = client.get("/api/v1/analytics/inventory", headers=admin_headers)
    assert inventory.status_code == 200
    assert inventory.json()["total_products"] >= 1


def test_rbac_blocks_customer_from_admin(client, auth_headers):
    resp = client.get("/api/v1/analytics/overview", headers=auth_headers)
    assert resp.status_code == 403
