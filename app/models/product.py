"""Product model — id, name, description, category, brand, price, stock, rating, image."""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, synonym

from app.database import Base


class Product(Base):
    """
    Products
    --------
    id, name, description, category, brand, price, stock, rating, image
    (category/brand stored as FKs for referential integrity)
    """

    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"), nullable=True, index=True
    )
    brand_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("brands.id", ondelete="SET NULL"), nullable=True, index=True
    )
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    stock: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rating: Mapped[Decimal] = mapped_column(
        Numeric(3, 2), default=Decimal("0.00"), nullable=False
    )
    image: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Catalog helpers
    slug: Mapped[str] = mapped_column(String(220), unique=True, nullable=False, index=True)
    sku: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    compare_at_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    weight_kg: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 3), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    stock_quantity = synonym("stock")
    image_url = synonym("image")

    category = relationship("Category", back_populates="products")
    brand = relationship("Brand", back_populates="products")
    cart_items = relationship("CartItem", back_populates="product")
    wishlist_items = relationship("WishlistItem", back_populates="product")
    order_items = relationship("OrderItem", back_populates="product")
    images = relationship(
        "ProductImage",
        back_populates="product",
        cascade="all, delete-orphan",
        order_by="ProductImage.sort_order",
    )
    reviews = relationship("Review", back_populates="product", cascade="all, delete-orphan")
