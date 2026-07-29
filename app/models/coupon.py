"""Coupon model — id, code, discount, expiry, active."""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Boolean, DateTime, Enum, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, synonym

from app.database import Base
from app.utils.enums import CouponType


class Coupon(Base):
    """
    Coupons
    -------
    id, code, discount, expiry, active
    """

    __tablename__ = "coupons"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    code: Mapped[str] = mapped_column(String(40), unique=True, nullable=False, index=True)
    discount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    expiry: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)

    # Extended coupon rules
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    coupon_type: Mapped[CouponType] = mapped_column(Enum(CouponType), nullable=False)
    min_order_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00"), nullable=False
    )
    max_discount: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    usage_limit: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    used_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    starts_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    value = synonym("discount")
    ends_at = synonym("expiry")
    is_active = synonym("active")
