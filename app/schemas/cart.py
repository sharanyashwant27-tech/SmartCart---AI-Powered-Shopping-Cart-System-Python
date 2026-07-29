"""Cart, wishlist, and coupon schemas."""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.utils.enums import CartItemStatus, CouponType
from app.schemas.product import CartProductSummary, ProductResponse


class CartItemCreate(BaseModel):
    product_id: int
    quantity: int = Field(1, ge=1, le=100)


class CartItemUpdate(BaseModel):
    quantity: int = Field(..., ge=1, le=100)


class CartItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    quantity: int
    status: CartItemStatus
    product: CartProductSummary
    line_total: Decimal
    created_at: datetime


class CartSummary(BaseModel):
    items: list[CartItemResponse]
    saved_for_later: list[CartItemResponse] = []
    subtotal: Decimal
    discount_amount: Decimal
    shipping_amount: Decimal
    tax_amount: Decimal
    total: Decimal
    coupon_code: Optional[str] = None
    item_count: int


class ApplyCouponRequest(BaseModel):
    code: str = Field(..., min_length=2, max_length=40)


class WishlistItemCreate(BaseModel):
    product_id: int


class WishlistItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    product: ProductResponse
    created_at: datetime


class CouponCreate(BaseModel):
    code: str = Field(..., min_length=2, max_length=40)
    description: Optional[str] = None
    coupon_type: CouponType
    value: Decimal = Field(..., gt=0)
    min_order_amount: Decimal = Field(Decimal("0.00"), ge=0)
    max_discount: Optional[Decimal] = Field(None, ge=0)
    usage_limit: Optional[int] = Field(None, ge=1)
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None
    is_active: bool = True


class CouponUpdate(BaseModel):
    description: Optional[str] = None
    value: Optional[Decimal] = Field(None, gt=0)
    min_order_amount: Optional[Decimal] = Field(None, ge=0)
    max_discount: Optional[Decimal] = Field(None, ge=0)
    usage_limit: Optional[int] = Field(None, ge=1)
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None
    is_active: Optional[bool] = None


class CouponResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    description: Optional[str]
    coupon_type: CouponType
    value: Decimal
    min_order_amount: Decimal
    max_discount: Optional[Decimal]
    usage_limit: Optional[int]
    used_count: int
    starts_at: Optional[datetime]
    ends_at: Optional[datetime]
    is_active: bool
    created_at: datetime
