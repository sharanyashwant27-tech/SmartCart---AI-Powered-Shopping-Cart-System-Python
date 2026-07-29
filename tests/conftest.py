"""Pytest configuration and fixtures."""

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Use in-memory SQLite for tests before app imports settings heavily
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-pytest-only")
os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("ADMIN_EMAIL", "admin@test.com")
os.environ.setdefault("ADMIN_PASSWORD", "Admin@Test123")

from app.database import Base, get_db
from app.utils.enums import CouponType
from app.main import create_app
from app.schemas.cart import CouponCreate
from app.schemas.product import BrandCreate, CategoryCreate, ProductCreate
from app.services.auth_service import UserService
from app.services.cart_service import CouponService
from app.services.product_service import BrandService, CategoryService, ProductService
from decimal import Decimal


@pytest.fixture()
def db_engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def db_session(db_engine):
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(db_engine):
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db

    # Seed via override session
    db = TestingSessionLocal()
    UserService(db).ensure_admin("admin@test.com", "Admin@Test123", "Test Admin")
    cat = CategoryService(db).create(CategoryCreate(name="Test Cat"))
    brand = BrandService(db).create(BrandCreate(name="Test Brand"))
    ProductService(db).create(
        ProductCreate(
            name="Test Product",
            sku="TEST-001",
            description="A test product",
            price=Decimal("25.00"),
            stock_quantity=100,
            category_id=cat.id,
            brand_id=brand.id,
            is_featured=True,
        )
    )
    CouponService(db).create(
        CouponCreate(
            code="TEST10",
            coupon_type=CouponType.PERCENTAGE,
            value=Decimal("10"),
            min_order_amount=Decimal("0"),
        )
    )
    db.close()

    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def auth_headers(client):
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": "customer@example.com",
            "password": "Customer@123",
            "full_name": "Test Customer",
        },
    )
    assert resp.status_code == 201
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def admin_headers(client):
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@test.com", "password": "Admin@Test123"},
    )
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
