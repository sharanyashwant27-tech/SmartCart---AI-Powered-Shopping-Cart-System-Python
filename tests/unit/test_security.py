"""Unit tests for helpers and security."""

from app.utils.security import create_access_token, decode_token, hash_password, verify_password
from app.utils.helpers import generate_order_number, slugify


def test_slugify():
    assert slugify("Hello World!") == "hello-world"
    assert slugify("  Smart Cart  ") == "smart-cart"


def test_password_hashing():
    hashed = hash_password("Secret@123")
    assert hashed != "Secret@123"
    assert verify_password("Secret@123", hashed)
    assert not verify_password("wrong", hashed)


def test_jwt_roundtrip():
    token = create_access_token("42", {"role": "customer"})
    payload = decode_token(token)
    assert payload["sub"] == "42"
    assert payload["role"] == "customer"
    assert payload["type"] == "access"


def test_order_number_format():
    number = generate_order_number()
    assert number.startswith("SC-")
    assert len(number) > 10
