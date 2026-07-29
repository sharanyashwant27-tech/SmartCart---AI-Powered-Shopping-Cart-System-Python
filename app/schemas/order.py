"""Order, checkout, payment, and analytics schemas."""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.utils.enums import OrderStatus, PaymentMethod, PaymentStatus


class CheckoutRequest(BaseModel):
    shipping_address: str = Field("", min_length=0, max_length=2000)
    billing_address: Optional[str] = Field(None, max_length=2000)
    coupon_code: Optional[str] = None
    notes: Optional[str] = None
    payment_method: PaymentMethod = PaymentMethod.CARD
    payment_details: Optional[dict] = None
    redeem_points: int = Field(0, ge=0, description="Loyalty points to redeem (guests)")

    def resolved_shipping(self) -> str:
        ship = (self.shipping_address or "").strip()
        bill = (self.billing_address or "").strip()
        if len(ship) >= 10:
            return ship
        if len(bill) >= 10:
            return bill
        return ship

    def resolved_billing(self) -> str:
        bill = (self.billing_address or "").strip()
        ship = self.resolved_shipping()
        return bill if len(bill) >= 10 else ship


class OrderItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: Optional[int]
    product_name: str
    product_sku: str
    price: Decimal
    unit_price: Optional[Decimal] = None
    quantity: int
    line_total: Decimal


class PaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    amount: Decimal
    currency: str
    status: PaymentStatus
    provider: str
    stripe_payment_intent_id: Optional[str]
    stripe_client_secret: Optional[str]
    failure_reason: Optional[str]
    created_at: datetime


class OrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_number: str
    user_id: int
    status: OrderStatus
    payment_status: PaymentStatus
    order_date: datetime
    subtotal: Decimal
    discount_amount: Decimal
    shipping_amount: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    coupon_code: Optional[str]
    points_earned: int = 0
    points_redeemed: int = 0
    shipping_address: str
    billing_address: Optional[str]
    notes: Optional[str]
    tracking_number: Optional[str] = None
    carrier: Optional[str] = None
    estimated_delivery: Optional[datetime] = None
    cancel_reason: Optional[str] = None
    return_reason: Optional[str] = None
    cancelled_at: Optional[datetime] = None
    returned_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: datetime
    items: list[OrderItemResponse] = []
    payment: Optional[PaymentResponse] = None


class OrderStatusUpdate(BaseModel):
    status: OrderStatus


class PaymentConfirmRequest(BaseModel):
    payment_intent_id: Optional[str] = None
    success: bool = True
    failure_reason: Optional[str] = None
    payment_reference: Optional[str] = None


class PaymentIntentResponse(BaseModel):
    order: OrderResponse
    client_secret: Optional[str]
    publishable_key: str
    simulated: bool = False
    message: str
    payment_method: PaymentMethod = PaymentMethod.CARD
    payment_instructions: Optional[str] = None
    invoice_url: Optional[str] = None
    # QR Code Payments (UPI deep-link encoded as PNG)
    qr_payload: Optional[str] = None
    qr_image_base64: Optional[str] = None
    qr_vpa: Optional[str] = None


class SalesReportItem(BaseModel):
    date: str
    orders: int
    revenue: Decimal


class SalesReportResponse(BaseModel):
    total_orders: int
    total_revenue: Decimal
    average_order_value: Decimal
    by_day: list[SalesReportItem]


class InventoryReportItem(BaseModel):
    product_id: int
    name: str
    sku: str
    stock_quantity: int
    price: Decimal
    is_low_stock: bool


class InventoryReportResponse(BaseModel):
    total_products: int
    low_stock_count: int
    out_of_stock_count: int
    items: list[InventoryReportItem]


class AnalyticsOverview(BaseModel):
    total_customers: int
    total_products: int
    total_orders: int
    total_revenue: Decimal
    pending_orders: int
    low_stock_products: int
    top_products: list[dict]
