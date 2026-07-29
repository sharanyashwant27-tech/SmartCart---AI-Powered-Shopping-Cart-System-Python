"""Checkout domain routes."""

from fastapi import APIRouter

from app.utils.dependencies import CurrentUser, DbSession
from app.schemas.order import CheckoutRequest, PaymentIntentResponse
from app.services.order_service import OrderService

router = APIRouter(prefix="/checkout", tags=["Checkout"])


@router.post("", response_model=PaymentIntentResponse, status_code=201)
async def checkout(
    payload: CheckoutRequest, user: CurrentUser, db: DbSession
) -> PaymentIntentResponse:
    """Create order from cart and initiate Stripe (or simulated) payment."""
    return OrderService(db).checkout(user, payload)
