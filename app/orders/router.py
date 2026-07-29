"""Orders domain routes."""

from typing import Optional

from fastapi import APIRouter
from fastapi.responses import Response

from app.utils.dependencies import CurrentUser, DbSession
from app.schemas.extra import CancelOrderRequest, ReturnOrderRequest
from app.schemas.order import OrderResponse
from app.services.invoice_service import build_invoice_pdf
from app.services.order_service import OrderService

router = APIRouter(prefix="/orders", tags=["Orders"])


@router.get("", response_model=list[OrderResponse])
async def my_orders(user: CurrentUser, db: DbSession) -> list[OrderResponse]:
    return [
        OrderResponse.model_validate(o)
        for o in OrderService(db).list_my_orders(user.id)
    ]


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(order_id: int, user: CurrentUser, db: DbSession) -> OrderResponse:
    return OrderResponse.model_validate(OrderService(db).get_order(user, order_id))


@router.post("/{order_id}/cancel", response_model=OrderResponse)
async def cancel_order(
    order_id: int,
    user: CurrentUser,
    db: DbSession,
    payload: Optional[CancelOrderRequest] = None,
) -> OrderResponse:
    reason = payload.reason if payload else None
    return OrderResponse.model_validate(
        OrderService(db).cancel_order(user, order_id, reason)
    )


@router.post("/{order_id}/return", response_model=OrderResponse)
async def return_order(
    order_id: int, payload: ReturnOrderRequest, user: CurrentUser, db: DbSession
) -> OrderResponse:
    return OrderResponse.model_validate(
        OrderService(db).request_return(user, order_id, payload.reason)
    )


@router.get("/{order_id}/track")
async def track_order(order_id: int, user: CurrentUser, db: DbSession) -> dict:
    return OrderService(db).tracking(user, order_id)


@router.get("/{order_id}/invoice")
async def download_invoice(order_id: int, user: CurrentUser, db: DbSession) -> Response:
    order = OrderService(db).get_order(user, order_id)
    pdf = build_invoice_pdf(order)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="invoice-{order.order_number}.pdf"'
        },
    )
