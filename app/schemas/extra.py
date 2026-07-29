"""Address book, review, and password-reset schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.utils.enums import AddressType


class AddressCreate(BaseModel):
    label: str = Field("Home", max_length=80)
    full_name: str = Field(..., min_length=2, max_length=150)
    phone: Optional[str] = None
    line1: str = Field(..., min_length=3, max_length=255)
    line2: Optional[str] = None
    city: str = Field(..., min_length=2, max_length=100)
    state: str = Field(..., min_length=2, max_length=100)
    postal_code: str = Field(..., min_length=2, max_length=20)
    country: str = Field("USA", max_length=100)
    address_type: AddressType = AddressType.BOTH
    is_default: bool = False


class AddressUpdate(BaseModel):
    label: Optional[str] = None
    full_name: Optional[str] = None
    phone: Optional[str] = None
    line1: Optional[str] = None
    line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    address_type: Optional[AddressType] = None
    is_default: Optional[bool] = None


class AddressResponse(AddressCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    created_at: datetime
    formatted: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(..., min_length=10)
    new_password: str = Field(..., min_length=8, max_length=128)


class ReviewCreate(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    title: Optional[str] = Field(None, max_length=150)
    body: Optional[str] = Field(None, max_length=5000)


class ReviewUpdate(BaseModel):
    rating: Optional[int] = Field(None, ge=1, le=5)
    title: Optional[str] = None
    body: Optional[str] = None


class ReviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    user_id: int
    rating: int
    title: Optional[str]
    body: Optional[str]
    is_verified_purchase: bool
    created_at: datetime
    user_name: Optional[str] = None


class ProductImageCreate(BaseModel):
    url: str = Field(..., min_length=5, max_length=500)
    alt_text: Optional[str] = None
    sort_order: int = 0
    is_primary: bool = False


class ProductImageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    url: str
    alt_text: Optional[str]
    sort_order: int
    is_primary: bool


class CancelOrderRequest(BaseModel):
    reason: Optional[str] = Field(None, max_length=500)


class ReturnOrderRequest(BaseModel):
    reason: str = Field(..., min_length=5, max_length=500)


class TrackingUpdate(BaseModel):
    tracking_number: str = Field(..., min_length=4, max_length=80)
    carrier: Optional[str] = Field(None, max_length=80)
    estimated_delivery: Optional[datetime] = None
    status: Optional[str] = None


class OrderTrackingResponse(BaseModel):
    order_number: str
    status: str
    tracking_number: Optional[str]
    carrier: Optional[str]
    estimated_delivery: Optional[datetime]
    timeline: list[dict]
    shipping_address: str
