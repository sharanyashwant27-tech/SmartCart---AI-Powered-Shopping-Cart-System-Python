"""Analytics domain routes."""

from fastapi import APIRouter, Query

from app.utils.dependencies import AdminUser, DbSession
from app.schemas.order import (
    AnalyticsOverview,
    InventoryReportResponse,
    SalesReportResponse,
)
from app.services.order_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/overview", response_model=AnalyticsOverview)
async def analytics_overview(_: AdminUser, db: DbSession) -> AnalyticsOverview:
    return AnalyticsService(db).overview()


@router.get("/sales", response_model=SalesReportResponse)
async def sales_report(
    _: AdminUser, db: DbSession, days: int = Query(30, ge=1, le=365)
) -> SalesReportResponse:
    return AnalyticsService(db).sales_report(days=days)


@router.get("/inventory", response_model=InventoryReportResponse)
async def inventory_report(
    _: AdminUser, db: DbSession, threshold: int = Query(5, ge=0)
) -> InventoryReportResponse:
    return AnalyticsService(db).inventory_report(low_stock_threshold=threshold)


@router.get("/dashboard")
async def analytics_dashboard(_: AdminUser, db: DbSession) -> dict:
    """Admin dashboard: today's/monthly revenue, orders, users, top products, low stock, coupons, inventory."""
    return AnalyticsService(db).dashboard()
