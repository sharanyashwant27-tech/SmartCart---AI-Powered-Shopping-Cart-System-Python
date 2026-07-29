"""Loyalty points schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class LoyaltyRules(BaseModel):
    points_per_dollar: int
    cents_per_point: int
    min_redeem_points: int
    signup_bonus: int


class LoyaltyTransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    points: int
    balance_after: int
    tx_type: str
    note: Optional[str] = None
    order_id: Optional[int] = None
    created_at: datetime


class LoyaltyAccountResponse(BaseModel):
    balance: int
    lifetime_earned: int
    lifetime_redeemed: int
    rules: LoyaltyRules
    recent: list[LoyaltyTransactionResponse] = []


class LoyaltyPreviewRequest(BaseModel):
    redeem_points: int = Field(0, ge=0)
    coupon_code: Optional[str] = None


class LoyaltyPreviewResponse(BaseModel):
    balance: int
    redeem_points: int
    points_discount: float
    estimated_earn: int
    cart_total: float
    rules: LoyaltyRules
