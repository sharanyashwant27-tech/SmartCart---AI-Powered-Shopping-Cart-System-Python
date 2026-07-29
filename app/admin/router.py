"""Admin domain routes."""

from typing import Optional

from fastapi import APIRouter, Query
from fastapi.responses import Response

from app.utils.dependencies import AdminUser, DbSession
from app.utils.enums import OrderStatus
from app.utils.exceptions import NotFoundError
from app.schemas.extra import TrackingUpdate
from app.schemas.order import OrderResponse, OrderStatusUpdate
from app.schemas.product import ProductCreate, ProductResponse, ProductUpdate
from app.schemas.user import MessageResponse, UserResponse
from app.services.auth_service import UserService
from app.services.invoice_service import build_invoice_pdf
from app.services.order_service import OrderService
from app.services.product_service import ProductService

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/orders", response_model=list[OrderResponse])
async def admin_orders(
    _: AdminUser,
    db: DbSession,
    status: Optional[OrderStatus] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> list[OrderResponse]:
    items, _ = OrderService(db).admin_list(status=status, skip=skip, limit=limit)
    return [OrderResponse.model_validate(o) for o in items]


@router.patch("/orders/{order_id}/status", response_model=OrderResponse)
async def admin_update_order_status(
    order_id: int, payload: OrderStatusUpdate, _: AdminUser, db: DbSession
) -> OrderResponse:
    return OrderResponse.model_validate(
        OrderService(db).update_status(order_id, payload.status)
    )


@router.post("/orders/{order_id}/tracking", response_model=OrderResponse)
async def admin_set_tracking(
    order_id: int, payload: TrackingUpdate, _: AdminUser, db: DbSession
) -> OrderResponse:
    status = OrderStatus(payload.status) if payload.status else None
    return OrderResponse.model_validate(
        OrderService(db).update_tracking(
            order_id,
            tracking_number=payload.tracking_number,
            carrier=payload.carrier,
            estimated_delivery=payload.estimated_delivery,
            status=status,
        )
    )


@router.post("/orders/{order_id}/approve-return", response_model=OrderResponse)
async def admin_approve_return(
    order_id: int, _: AdminUser, db: DbSession
) -> OrderResponse:
    return OrderResponse.model_validate(OrderService(db).approve_return(order_id))


@router.get("/customers", response_model=list[UserResponse])
async def admin_customers(
    _: AdminUser,
    db: DbSession,
    skip: int = 0,
    limit: int = 50,
) -> list[UserResponse]:
    items, _ = UserService(db).list_customers(skip=skip, limit=limit)
    return [UserResponse.model_validate(u) for u in items]


@router.get("/orders/{order_id}/invoice")
async def admin_download_invoice(
    order_id: int, _: AdminUser, db: DbSession
) -> Response:
    """Admin bill/invoice download for any order."""
    order = OrderService(db).orders.get_by_id(order_id)
    if order is None:
        raise NotFoundError("Order not found")
    pdf = build_invoice_pdf(order)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="bill-{order.order_number}.pdf"'
        },
    )


@router.post("/products", response_model=ProductResponse, status_code=201)
async def admin_create_product(
    payload: ProductCreate, _: AdminUser, db: DbSession
) -> ProductResponse:
    return ProductResponse.model_validate(ProductService(db).create(payload))


@router.patch("/products/{product_id}", response_model=ProductResponse)
async def admin_update_product(
    product_id: int, payload: ProductUpdate, _: AdminUser, db: DbSession
) -> ProductResponse:
    return ProductResponse.model_validate(
        ProductService(db).update(product_id, payload)
    )


@router.delete("/products/{product_id}", response_model=MessageResponse)
async def admin_delete_product(
    product_id: int, _: AdminUser, db: DbSession
) -> MessageResponse:
    ProductService(db).delete(product_id)
    return MessageResponse(message="Product deleted")
