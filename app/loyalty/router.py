"""Loyalty points API — guest (customer) rewards."""

from fastapi import APIRouter, Query

from app.schemas.loyalty import (
    LoyaltyAccountResponse,
    LoyaltyPreviewRequest,
    LoyaltyPreviewResponse,
    LoyaltyTransactionResponse,
)
from app.services.loyalty_service import LoyaltyService
from app.utils.dependencies import CurrentUser, DbSession

router = APIRouter(prefix="/loyalty", tags=["Loyalty"])


@router.get("/me", response_model=LoyaltyAccountResponse)
async def my_loyalty(user: CurrentUser, db: DbSession) -> LoyaltyAccountResponse:
    return LoyaltyService(db).account(user)


@router.get("/history", response_model=list[LoyaltyTransactionResponse])
async def loyalty_history(
    user: CurrentUser,
    db: DbSession,
    limit: int = Query(50, ge=1, le=100),
) -> list[LoyaltyTransactionResponse]:
    return LoyaltyService(db).account(user, limit=limit).recent


@router.post("/preview", response_model=LoyaltyPreviewResponse)
async def preview_loyalty(
    payload: LoyaltyPreviewRequest, user: CurrentUser, db: DbSession
) -> LoyaltyPreviewResponse:
    return LoyaltyService(db).preview(
        user, redeem_points=payload.redeem_points, coupon_code=payload.coupon_code
    )
