"""Checkout, orders, payments, admin, and analytics routes."""

from typing import Optional

from fastapi import APIRouter, Query
from fastapi.responses import Response

from app.utils.dependencies import AdminUser, CurrentUser, DbSession
from app.utils.enums import OrderStatus
from app.schemas.extra import CancelOrderRequest, ReturnOrderRequest, TrackingUpdate
from app.schemas.order import (
    AnalyticsOverview,
    CheckoutRequest,
    InventoryReportResponse,
    OrderResponse,
    OrderStatusUpdate,
    PaymentConfirmRequest,
    PaymentIntentResponse,
    SalesReportResponse,
)
from app.schemas.product import ProductCreate, ProductResponse, ProductUpdate
from app.schemas.user import MessageResponse, UserResponse
from app.services.auth_service import UserService
from app.services.invoice_service import build_invoice_pdf
from app.services.order_service import AnalyticsService, OrderService
from app.services.product_service import ProductService

checkout_router = APIRouter(prefix="/checkout", tags=["Checkout"])
orders_router = APIRouter(prefix="/orders", tags=["Orders"])
payments_router = APIRouter(prefix="/payments", tags=["Payments"])
admin_router = APIRouter(prefix="/admin", tags=["Admin"])
analytics_router = APIRouter(prefix="/analytics", tags=["Analytics"])


@checkout_router.post("", response_model=PaymentIntentResponse, status_code=201)
async def checkout(
    payload: CheckoutRequest, user: CurrentUser, db: DbSession
) -> PaymentIntentResponse:
    """Create order from cart and initiate Stripe (or simulated) payment."""
    return OrderService(db).checkout(user, payload)


@orders_router.get("", response_model=list[OrderResponse])
async def my_orders(user: CurrentUser, db: DbSession) -> list[OrderResponse]:
    return [
        OrderResponse.model_validate(o)
        for o in OrderService(db).list_my_orders(user.id)
    ]


@orders_router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: int, user: CurrentUser, db: DbSession
) -> OrderResponse:
    return OrderResponse.model_validate(OrderService(db).get_order(user, order_id))


@orders_router.post("/{order_id}/cancel", response_model=OrderResponse)
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


@orders_router.post("/{order_id}/return", response_model=OrderResponse)
async def return_order(
    order_id: int, payload: ReturnOrderRequest, user: CurrentUser, db: DbSession
) -> OrderResponse:
    return OrderResponse.model_validate(
        OrderService(db).request_return(user, order_id, payload.reason)
    )


@orders_router.get("/{order_id}/track")
async def track_order(order_id: int, user: CurrentUser, db: DbSession) -> dict:
    return OrderService(db).tracking(user, order_id)


@orders_router.get("/{order_id}/invoice")
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


@payments_router.post(
    "/orders/{order_id}/confirm", response_model=OrderResponse
)
async def confirm_payment(
    order_id: int,
    payload: PaymentConfirmRequest,
    user: CurrentUser,
    db: DbSession,
) -> OrderResponse:
    """Confirm payment success or failure (Stripe sandbox / simulation)."""
    return OrderService(db).confirm_payment(user, order_id, payload)


@admin_router.get("/orders", response_model=list[OrderResponse])
async def admin_orders(
    _: AdminUser,
    db: DbSession,
    status: Optional[OrderStatus] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> list[OrderResponse]:
    items, _ = OrderService(db).admin_list(status=status, skip=skip, limit=limit)
    return [OrderResponse.model_validate(o) for o in items]


@admin_router.patch("/orders/{order_id}/status", response_model=OrderResponse)
async def admin_update_order_status(
    order_id: int, payload: OrderStatusUpdate, _: AdminUser, db: DbSession
) -> OrderResponse:
    return OrderResponse.model_validate(
        OrderService(db).update_status(order_id, payload.status)
    )


@admin_router.post("/orders/{order_id}/tracking", response_model=OrderResponse)
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


@admin_router.post("/orders/{order_id}/approve-return", response_model=OrderResponse)
async def admin_approve_return(
    order_id: int, _: AdminUser, db: DbSession
) -> OrderResponse:
    return OrderResponse.model_validate(OrderService(db).approve_return(order_id))


@admin_router.get("/customers", response_model=list[UserResponse])
async def admin_customers(
    _: AdminUser,
    db: DbSession,
    skip: int = 0,
    limit: int = 50,
) -> list[UserResponse]:
    items, _ = UserService(db).list_customers(skip=skip, limit=limit)
    return [UserResponse.model_validate(u) for u in items]


@admin_router.post("/products", response_model=ProductResponse, status_code=201)
async def admin_create_product(
    payload: ProductCreate, _: AdminUser, db: DbSession
) -> ProductResponse:
    return ProductResponse.model_validate(ProductService(db).create(payload))


@admin_router.patch("/products/{product_id}", response_model=ProductResponse)
async def admin_update_product(
    product_id: int, payload: ProductUpdate, _: AdminUser, db: DbSession
) -> ProductResponse:
    return ProductResponse.model_validate(
        ProductService(db).update(product_id, payload)
    )


@admin_router.delete("/products/{product_id}", response_model=MessageResponse)
async def admin_delete_product(
    product_id: int, _: AdminUser, db: DbSession
) -> MessageResponse:
    ProductService(db).delete(product_id)
    return MessageResponse(message="Product deleted")


@analytics_router.get("/overview", response_model=AnalyticsOverview)
async def analytics_overview(_: AdminUser, db: DbSession) -> AnalyticsOverview:
    return AnalyticsService(db).overview()


@analytics_router.get("/sales", response_model=SalesReportResponse)
async def sales_report(
    _: AdminUser, db: DbSession, days: int = Query(30, ge=1, le=365)
) -> SalesReportResponse:
    return AnalyticsService(db).sales_report(days=days)


@analytics_router.get("/inventory", response_model=InventoryReportResponse)
async def inventory_report(
    _: AdminUser, db: DbSession, threshold: int = Query(5, ge=0)
) -> InventoryReportResponse:
    return AnalyticsService(db).inventory_report(low_stock_threshold=threshold)


@analytics_router.get("/dashboard")
async def analytics_dashboard(_: AdminUser, db: DbSession) -> dict:
    """Sales, revenue, best sellers, low stock, monthly orders, customer growth."""
    return AnalyticsService(db).dashboard()
