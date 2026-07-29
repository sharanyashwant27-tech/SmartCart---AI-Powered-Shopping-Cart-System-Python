"""Payment domain routes."""

from fastapi import APIRouter

from app.utils.dependencies import CurrentUser, DbSession
from app.schemas.order import OrderResponse, PaymentConfirmRequest
from app.services.order_service import OrderService

router = APIRouter(prefix="/payments", tags=["Payments"])


@router.post("/orders/{order_id}/confirm", response_model=OrderResponse)
async def confirm_payment(
    order_id: int,
    payload: PaymentConfirmRequest,
    user: CurrentUser,
    db: DbSession,
) -> OrderResponse:
    """Confirm payment success or failure (Stripe sandbox / simulation)."""
    return OrderService(db).confirm_payment(user, order_id, payload)
