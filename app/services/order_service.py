"""Checkout, order, payment, and analytics services."""

import logging
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

import stripe
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.order import Order, OrderItem, Payment
from app.models.product import Product
from app.models.user import User
from app.repositories.cart_repository import CartRepository
from app.repositories.order_repository import OrderRepository, PaymentRepository
from app.repositories.product_repository import ProductRepository
from app.repositories.user_repository import UserRepository
from app.schemas.order import (
    AnalyticsOverview,
    CheckoutRequest,
    InventoryReportItem,
    InventoryReportResponse,
    OrderResponse,
    PaymentConfirmRequest,
    PaymentIntentResponse,
    SalesReportItem,
    SalesReportResponse,
)
from app.services.cart_service import CartService, CouponService, _money
from app.services.loyalty_service import LoyaltyService
from app.services.qr_service import payment_qr
from app.utils.enums import OrderStatus, PaymentMethod, PaymentStatus, UserRole
from app.utils.exceptions import ForbiddenError, NotFoundError, PaymentError, ValidationAppError
from app.utils.helpers import generate_order_number

logger = logging.getLogger(__name__)
settings = get_settings()

PAYMENT_METHOD_LABELS = {
    PaymentMethod.CARD: "Card / Stripe",
    PaymentMethod.UPI: "UPI",
    PaymentMethod.QR: "QR Code",
    PaymentMethod.NETBANKING: "Internet Banking",
    PaymentMethod.WALLET: "Digital Wallet",
    PaymentMethod.COD: "Cash on Delivery",
}


class OrderService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.orders = OrderRepository(db)
        self.payments = PaymentRepository(db)
        self.cart = CartService(db)
        self.cart_repo = CartRepository(db)
        self.products = ProductRepository(db)
        self.coupons = CouponService(db)
        self.loyalty = LoyaltyService(db)

    def checkout(self, user: User, payload: CheckoutRequest) -> PaymentIntentResponse:
        summary = self.cart.calculate_totals(user.id, payload.coupon_code)
        if not summary.items:
            raise ValidationAppError("Cart is empty")

        shipping_address = payload.resolved_shipping()
        billing_address = payload.resolved_billing()
        if len(shipping_address) < 10:
            raise ValidationAppError(
                "Enter a full shipping or billing address (at least 10 characters)"
            )

        for item in summary.items:
            product = self.products.get_by_id(item.product_id)
            if product is None or product.stock_quantity < item.quantity:
                raise ValidationAppError(f"Insufficient stock for {item.product.name}")

        redeem_points = int(payload.redeem_points or 0)
        points_discount = Decimal("0.00")
        if redeem_points > 0:
            points_discount = self.loyalty.points_to_money(redeem_points)
            # Validate against payable before applying (will debit after order flush)
            self.loyalty.validate_redeem(user, redeem_points, summary.total)

        discount_amount = _money(summary.discount_amount + points_discount)
        total_amount = _money(max(summary.total - points_discount, Decimal("0")))

        method = payload.payment_method or PaymentMethod.CARD
        order = Order(
            order_number=generate_order_number(),
            user_id=user.id,
            status=OrderStatus.PENDING,
            payment_status=PaymentStatus.PENDING,
            subtotal=summary.subtotal,
            discount_amount=discount_amount,
            shipping_amount=summary.shipping_amount,
            tax_amount=summary.tax_amount,
            total_amount=total_amount,
            coupon_code=summary.coupon_code,
            points_earned=0,
            points_redeemed=0,
            shipping_address=shipping_address,
            billing_address=billing_address or shipping_address,
            notes=payload.notes,
        )
        self.db.add(order)
        self.db.flush()

        if redeem_points > 0:
            self.loyalty.redeem_against_payable(
                user, order, redeem_points, summary.total
            )
            # Re-apply final totals after validation
            order.discount_amount = discount_amount
            order.total_amount = total_amount

        for item in summary.items:
            self.db.add(
                OrderItem(
                    order_id=order.id,
                    product_id=item.product_id,
                    product_name=item.product.name,
                    product_sku=item.product.sku,
                    price=item.product.price,
                    quantity=item.quantity,
                    line_total=item.line_total,
                )
            )
            product = self.products.get_by_id(item.product_id)
            if product:
                product.stock -= item.quantity

        if summary.coupon_code:
            coupon, _ = self.coupons.validate_and_compute(
                summary.coupon_code, summary.subtotal
            )
            coupon.used_count += 1

        payment = Payment(
            order_id=order.id,
            amount=order.total_amount,
            currency=settings.currency,
            status=PaymentStatus.PENDING,
            provider=method.value,
        )
        self.db.add(payment)
        self.db.commit()

        order = self.orders.get_by_id(order.id)
        assert order is not None
        return self._create_payment_intent(order, method, payload.payment_details)

    def _create_payment_intent(
        self,
        order: Order,
        method: PaymentMethod = PaymentMethod.CARD,
        details: Optional[dict] = None,
    ) -> PaymentIntentResponse:
        details = details or {}
        amount_cents = int(_money(order.total_amount) * 100)
        simulated = True
        client_secret: Optional[str] = None
        intent_id: Optional[str] = None
        instructions = ""
        qr_payload: Optional[str] = None
        qr_image_base64: Optional[str] = None
        qr_vpa: Optional[str] = None

        if method == PaymentMethod.CARD:
            if (
                settings.stripe_secret_key.startswith("sk_test_")
                and "your_stripe" not in settings.stripe_secret_key
            ):
                try:
                    stripe.api_key = settings.stripe_secret_key
                    intent = stripe.PaymentIntent.create(
                        amount=amount_cents,
                        currency=settings.currency,
                        metadata={
                            "order_id": str(order.id),
                            "order_number": order.order_number,
                            "payment_method": method.value,
                        },
                        automatic_payment_methods={"enabled": True},
                    )
                    intent_id = intent.id
                    client_secret = intent.client_secret
                    simulated = False
                    message = "Stripe PaymentIntent created — complete card payment"
                    instructions = "Pay securely with your debit/credit card."
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Stripe error, falling back to simulation: %s", exc)
                    intent_id = f"pi_sim_{uuid.uuid4().hex}"
                    client_secret = f"{intent_id}_secret_sim"
                    message = "Card payment (sandbox) — Stripe unavailable"
                    instructions = "Use the sandbox card form to complete payment."
            else:
                intent_id = f"pi_sim_{uuid.uuid4().hex}"
                client_secret = f"{intent_id}_secret_sim"
                message = "Card payment (sandbox)"
                instructions = "Use test card 4242 4242 4242 4242 to pay."

        elif method in {PaymentMethod.UPI, PaymentMethod.QR}:
            vpa = str(
                details.get("upi_id")
                or details.get("vpa")
                or details.get("merchant_vpa")
                or "smartcart@upi"
            )
            qr = payment_qr(
                amount=order.total_amount,
                order_number=order.order_number,
                vpa=vpa,
                payee_name="SmartCart",
                currency=(settings.currency or "inr").upper()
                if (settings.currency or "").lower() == "inr"
                else "INR",
            )
            qr_payload = qr["payload"]
            qr_image_base64 = qr["image_base64"]
            qr_vpa = qr["vpa"]
            if method == PaymentMethod.QR:
                intent_id = f"qr_{uuid.uuid4().hex}"
                message = "Scan QR code to pay for your cart"
                instructions = (
                    f"Scan the QR with any UPI app (GPay, PhonePe, BHIM) and pay "
                    f"<b>${float(order.total_amount):.2f}</b> to <b>{vpa}</b>. "
                    "After payment, confirm below to generate your bill. (Sandbox)"
                )
            else:
                intent_id = f"upi_{uuid.uuid4().hex}"
                message = f"UPI payment initiated to {vpa}"
                instructions = (
                    f"Scan the QR or pay ${float(order.total_amount):.2f} to "
                    f"<b>{vpa}</b> in your UPI app, then confirm. (Sandbox)"
                )
            client_secret = intent_id

        elif method == PaymentMethod.NETBANKING:
            bank = str(details.get("bank") or "Demo Bank")
            intent_id = f"nb_{uuid.uuid4().hex}"
            client_secret = intent_id
            message = f"Internet banking via {bank}"
            instructions = (
                f"You will be redirected to <b>{bank}</b> net-banking. "
                f"Authorize payment of ${float(order.total_amount):.2f}. (Sandbox simulation)"
            )

        elif method == PaymentMethod.WALLET:
            wallet = str(details.get("wallet") or "SmartPay Wallet")
            intent_id = f"wallet_{uuid.uuid4().hex}"
            client_secret = intent_id
            message = f"Wallet payment via {wallet}"
            instructions = (
                f"Confirm debit of ${float(order.total_amount):.2f} from "
                f"<b>{wallet}</b>. (Sandbox simulation)"
            )

        else:
            intent_id = f"cod_{uuid.uuid4().hex}"
            client_secret = intent_id
            message = "Cash on Delivery selected"
            instructions = (
                f"Pay <b>${float(order.total_amount):.2f}</b> in cash when your order is delivered. "
                "Confirm to place the COD order and generate your bill."
            )

        if order.payment:
            order.payment.provider = method.value
            order.payment.stripe_payment_intent_id = intent_id
            order.payment.stripe_client_secret = client_secret
            self.db.commit()
            self.db.refresh(order)

        return PaymentIntentResponse(
            order=OrderResponse.model_validate(order),
            client_secret=client_secret,
            publishable_key=settings.stripe_publishable_key,
            simulated=simulated,
            message=message,
            payment_method=method,
            payment_instructions=instructions,
            invoice_url=f"/api/v1/orders/{order.id}/invoice",
            qr_payload=qr_payload,
            qr_image_base64=qr_image_base64,
            qr_vpa=qr_vpa,
        )

    def confirm_payment(
        self, user: User, order_id: int, payload: PaymentConfirmRequest
    ) -> OrderResponse:
        order = self.orders.get_by_id(order_id)
        if order is None:
            raise NotFoundError("Order not found")
        if order.user_id != user.id and user.role != UserRole.ADMIN:
            raise ForbiddenError("Not your order")
        if order.payment is None:
            raise PaymentError("No payment record for order")

        stored = order.payment.stripe_payment_intent_id or ""
        provided = payload.payment_intent_id or payload.payment_reference or stored
        sandbox_prefixes = ("pi_sim_", "upi_", "qr_", "nb_", "wallet_", "cod_")
        if (
            stored
            and provided
            and stored != provided
            and not any(stored.startswith(p) for p in sandbox_prefixes)
        ):
            raise PaymentError("Payment intent mismatch")

        if payload.success:
            order.payment.status = PaymentStatus.SUCCEEDED
            order.payment.failure_reason = None
            order.payment_status = PaymentStatus.SUCCEEDED
            order.status = OrderStatus.PAID
            if payload.payment_reference:
                order.payment.stripe_payment_intent_id = (
                    f"{stored or provided}|ref:{payload.payment_reference}"
                )
            self.cart_repo.clear_active(order.user_id)
            owner = order.user
            if owner is None:
                owner = self.db.get(User, order.user_id)
            if owner is not None:
                self.loyalty.earn_for_paid_order(owner, order)
            message_status = "succeeded"
        else:
            order.payment.status = PaymentStatus.FAILED
            order.payment.failure_reason = payload.failure_reason or "Payment failed"
            order.payment_status = PaymentStatus.FAILED
            order.status = OrderStatus.CANCELLED
            for item in order.items:
                if item.product_id:
                    product = self.products.get_by_id(item.product_id)
                    if product:
                        product.stock += item.quantity
            owner = order.user
            if owner is None:
                owner = self.db.get(User, order.user_id)
            if owner is not None:
                self.loyalty.restore_redeem_on_failed_payment(owner, order)
            message_status = "failed"

        self.db.commit()
        order = self.orders.get_by_id(order_id)
        assert order is not None
        logger.info("Payment %s for order %s", message_status, order.order_number)
        return OrderResponse.model_validate(order)

    def get_order(self, user: User, order_id: int) -> Order:
        order = self.orders.get_by_id(order_id)
        if order is None:
            raise NotFoundError("Order not found")
        if order.user_id != user.id and user.role != UserRole.ADMIN:
            raise ForbiddenError("Not your order")
        return order

    def list_my_orders(self, user_id: int) -> list[Order]:
        return self.orders.list_for_user(user_id)

    def admin_list(
        self, status: Optional[OrderStatus] = None, skip: int = 0, limit: int = 50
    ) -> tuple[list[Order], int]:
        return self.orders.list_all(status=status, skip=skip, limit=limit)

    def update_status(self, order_id: int, status: OrderStatus) -> Order:
        order = self.orders.get_by_id(order_id)
        if order is None:
            raise NotFoundError("Order not found")
        order.status = status
        self.db.commit()
        self.db.refresh(order)
        return order

    def cancel_order(self, user: User, order_id: int, reason: Optional[str] = None) -> Order:
        order = self.get_order(user, order_id)
        if order.status in {
            OrderStatus.SHIPPED,
            OrderStatus.DELIVERED,
            OrderStatus.CANCELLED,
            OrderStatus.REFUNDED,
            OrderStatus.RETURNED,
        }:
            raise ValidationAppError(f"Cannot cancel order in status '{order.status.value}'")
        # Restock if inventory was reserved
        if order.status in {
            OrderStatus.PENDING,
            OrderStatus.PAID,
            OrderStatus.PROCESSING,
        }:
            for item in order.items:
                if item.product_id:
                    product = self.products.get_by_id(item.product_id)
                    if product:
                        product.stock_quantity += item.quantity
        order.status = OrderStatus.CANCELLED
        order.cancelled_at = datetime.now(timezone.utc)
        order.cancel_reason = reason
        if order.payment and order.payment.status == PaymentStatus.SUCCEEDED:
            order.payment.status = PaymentStatus.REFUNDED
            order.payment_status = PaymentStatus.REFUNDED
            order.status = OrderStatus.REFUNDED
            owner = order.user or self.db.get(User, order.user_id)
            if owner is not None:
                self.loyalty.reverse_earn_on_refund(owner, order)
        elif order.payment and order.payment.status == PaymentStatus.PENDING:
            order.payment.status = PaymentStatus.CANCELLED
            order.payment_status = PaymentStatus.CANCELLED
            owner = order.user or self.db.get(User, order.user_id)
            if owner is not None:
                self.loyalty.restore_redeem_on_failed_payment(owner, order)
        self.db.commit()
        self.db.refresh(order)
        return order

    def request_return(self, user: User, order_id: int, reason: str) -> Order:
        order = self.get_order(user, order_id)
        if order.status not in {OrderStatus.DELIVERED, OrderStatus.SHIPPED}:
            raise ValidationAppError("Returns are only available after shipping/delivery")
        order.status = OrderStatus.RETURN_REQUESTED
        order.return_reason = reason
        self.db.commit()
        self.db.refresh(order)
        return order

    def approve_return(self, order_id: int) -> Order:
        order = self.orders.get_by_id(order_id)
        if order is None:
            raise NotFoundError("Order not found")
        if order.status != OrderStatus.RETURN_REQUESTED:
            raise ValidationAppError("Order is not awaiting return approval")
        for item in order.items:
            if item.product_id:
                product = self.products.get_by_id(item.product_id)
                if product:
                    product.stock_quantity += item.quantity
        order.status = OrderStatus.RETURNED
        order.returned_at = datetime.now(timezone.utc)
        if order.payment:
            order.payment.status = PaymentStatus.REFUNDED
            order.payment_status = PaymentStatus.REFUNDED
        owner = order.user or self.db.get(User, order.user_id)
        if owner is not None:
            self.loyalty.reverse_earn_on_refund(owner, order)
        self.db.commit()
        self.db.refresh(order)
        return order

    def update_tracking(
        self,
        order_id: int,
        *,
        tracking_number: str,
        carrier: Optional[str] = None,
        estimated_delivery: Optional[datetime] = None,
        status: Optional[OrderStatus] = None,
    ) -> Order:
        order = self.orders.get_by_id(order_id)
        if order is None:
            raise NotFoundError("Order not found")
        order.tracking_number = tracking_number
        order.carrier = carrier
        order.estimated_delivery = estimated_delivery
        if status:
            order.status = status
        elif order.status in {OrderStatus.PAID, OrderStatus.PROCESSING}:
            order.status = OrderStatus.SHIPPED
        self.db.commit()
        self.db.refresh(order)
        return order

    def tracking(self, user: User, order_id: int) -> dict:
        order = self.get_order(user, order_id)
        timeline = [
            {"status": "placed", "at": order.created_at.isoformat() if order.created_at else None},
        ]
        if order.payment and order.payment.status == PaymentStatus.SUCCEEDED:
            timeline.append({"status": "paid", "at": order.updated_at.isoformat()})
        if order.status in {
            OrderStatus.PROCESSING,
            OrderStatus.SHIPPED,
            OrderStatus.DELIVERED,
            OrderStatus.RETURN_REQUESTED,
            OrderStatus.RETURNED,
        }:
            timeline.append({"status": "processing", "at": None})
        if order.tracking_number:
            timeline.append(
                {
                    "status": "shipped",
                    "tracking_number": order.tracking_number,
                    "carrier": order.carrier,
                    "estimated_delivery": order.estimated_delivery.isoformat()
                    if order.estimated_delivery
                    else None,
                }
            )
        if order.status == OrderStatus.DELIVERED:
            timeline.append({"status": "delivered", "at": order.updated_at.isoformat()})
        if order.cancelled_at:
            timeline.append(
                {
                    "status": "cancelled",
                    "at": order.cancelled_at.isoformat(),
                    "reason": order.cancel_reason,
                }
            )
        if order.status in {OrderStatus.RETURN_REQUESTED, OrderStatus.RETURNED}:
            timeline.append(
                {
                    "status": order.status.value,
                    "reason": order.return_reason,
                    "at": order.returned_at.isoformat() if order.returned_at else None,
                }
            )
        return {
            "order_number": order.order_number,
            "status": order.status.value,
            "tracking_number": order.tracking_number,
            "carrier": order.carrier,
            "estimated_delivery": order.estimated_delivery,
            "timeline": timeline,
            "shipping_address": order.shipping_address,
        }


class AnalyticsService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.orders = OrderRepository(db)
        self.products = ProductRepository(db)
        self.users = UserRepository(db)

    def overview(self) -> AnalyticsOverview:
        total_customers = self.users.count([User.role == UserRole.CUSTOMER])
        total_products = self.products.count()
        total_orders = self.orders.count()
        revenue = (
            self.db.query(func.coalesce(func.sum(Order.total_amount), 0))
            .filter(
                Order.status.in_(
                    [
                        OrderStatus.PAID,
                        OrderStatus.PROCESSING,
                        OrderStatus.SHIPPED,
                        OrderStatus.DELIVERED,
                    ]
                )
            )
            .scalar()
        )
        pending = self.orders.count([Order.status == OrderStatus.PENDING])
        low_stock = self.products.count([Product.stock <= 5])

        top = (
            self.db.query(
                OrderItem.product_name,
                func.sum(OrderItem.quantity).label("qty"),
                func.sum(OrderItem.line_total).label("revenue"),
            )
            .group_by(OrderItem.product_name)
            .order_by(func.sum(OrderItem.quantity).desc())
            .limit(5)
            .all()
        )
        return AnalyticsOverview(
            total_customers=total_customers,
            total_products=total_products,
            total_orders=total_orders,
            total_revenue=_money(revenue or 0),
            pending_orders=pending,
            low_stock_products=low_stock,
            top_products=[
                {"name": r[0], "quantity": int(r[1]), "revenue": float(r[2])} for r in top
            ],
        )

    def sales_report(self, days: int = 30) -> SalesReportResponse:
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=days)
        by_day = self.orders.sales_by_day(start, end)
        items = [
            SalesReportItem(date=d, orders=o, revenue=r) for d, o, r in by_day
        ]
        total_orders = sum(i.orders for i in items)
        total_revenue = _money(sum((i.revenue for i in items), Decimal("0")))
        aov = _money(total_revenue / total_orders) if total_orders else Decimal("0.00")
        return SalesReportResponse(
            total_orders=total_orders,
            total_revenue=total_revenue,
            average_order_value=aov,
            by_day=items,
        )

    def inventory_report(self, low_stock_threshold: int = 5) -> InventoryReportResponse:
        products = self.products.list(limit=1000, order_by=Product.name.asc())
        items = [
            InventoryReportItem(
                product_id=p.id,
                name=p.name,
                sku=p.sku,
                stock_quantity=p.stock_quantity,
                price=p.price,
                is_low_stock=p.stock_quantity <= low_stock_threshold,
            )
            for p in products
        ]
        return InventoryReportResponse(
            total_products=len(items),
            low_stock_count=sum(1 for i in items if i.is_low_stock and i.stock_quantity > 0),
            out_of_stock_count=sum(1 for i in items if i.stock_quantity == 0),
            items=items,
        )

    def dashboard(self) -> dict:
        """Admin dashboard KPIs: revenue, orders, users, products, coupons, inventory."""
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        paid_like = [
            OrderStatus.PAID,
            OrderStatus.PROCESSING,
            OrderStatus.SHIPPED,
            OrderStatus.DELIVERED,
        ]

        def _revenue_between(start: datetime, end: datetime | None = None) -> Decimal:
            q = self.db.query(func.coalesce(func.sum(Order.total_amount), 0)).filter(
                Order.order_date >= start,
                Order.status.in_(paid_like),
            )
            if end is not None:
                q = q.filter(Order.order_date < end)
            return _money(q.scalar() or 0)

        today_revenue = _revenue_between(today_start)
        monthly_revenue = _revenue_between(month_start)
        total_revenue = _money(
            self.db.query(func.coalesce(func.sum(Order.total_amount), 0))
            .filter(Order.status.in_(paid_like))
            .scalar()
            or 0
        )

        total_orders = self.orders.count()
        pending_orders = self.orders.count([Order.status == OrderStatus.PENDING])
        cancelled_orders = self.orders.count(
            [Order.status.in_([OrderStatus.CANCELLED, OrderStatus.REFUNDED])]
        )
        total_users = self.users.count([User.role == UserRole.CUSTOMER])
        total_products = self.products.count()

        top_products = (
            self.db.query(
                OrderItem.product_name,
                func.sum(OrderItem.quantity).label("qty"),
                func.sum(OrderItem.line_total).label("revenue"),
            )
            .group_by(OrderItem.product_name)
            .order_by(func.sum(OrderItem.quantity).desc())
            .limit(10)
            .all()
        )

        inventory = self.inventory_report()
        low_stock = [i.model_dump() for i in inventory.items if i.is_low_stock][:20]

        from app.models.coupon import Coupon

        coupons = (
            self.db.query(Coupon).order_by(Coupon.created_at.desc()).limit(50).all()
        )
        coupon_rows = [
            {
                "id": c.id,
                "code": c.code,
                "discount": float(c.discount),
                "coupon_type": c.coupon_type.value,
                "expiry": c.expiry.isoformat() if c.expiry else None,
                "active": c.active,
                "used_count": c.used_count,
            }
            for c in coupons
        ]

        monthly = []
        for i in range(5, -1, -1):
            ms = (now.replace(day=1) - timedelta(days=30 * i)).replace(day=1)
            next_month = (ms + timedelta(days=32)).replace(day=1)
            count = (
                self.db.query(func.count(Order.id))
                .filter(Order.order_date >= ms, Order.order_date < next_month)
                .scalar()
            )
            revenue = (
                self.db.query(func.coalesce(func.sum(Order.total_amount), 0))
                .filter(
                    Order.order_date >= ms,
                    Order.order_date < next_month,
                    Order.status.in_(paid_like),
                )
                .scalar()
            )
            monthly.append(
                {
                    "month": ms.strftime("%Y-%m"),
                    "orders": int(count or 0),
                    "revenue": float(revenue or 0),
                }
            )

        sales = self.sales_report(days=30)
        overview = self.overview()
        top_rows = [
            {"name": r[0], "quantity": int(r[1]), "revenue": float(r[2])}
            for r in top_products
        ]

        return {
            "kpis": {
                "today_revenue": float(today_revenue),
                "monthly_revenue": float(monthly_revenue),
                "total_revenue": float(total_revenue),
                "total_orders": total_orders,
                "pending_orders": pending_orders,
                "cancelled_orders": cancelled_orders,
                "users": total_users,
                "products": total_products,
                "low_stock_count": inventory.low_stock_count,
                "out_of_stock_count": inventory.out_of_stock_count,
                "active_coupons": sum(1 for c in coupon_rows if c["active"]),
            },
            "top_products": top_rows,
            "low_stock": low_stock,
            "coupons": coupon_rows,
            "inventory": inventory.model_dump(),
            "monthly_orders": monthly,
            "overview": overview.model_dump(),
            "sales": sales.model_dump(),
            "best_sellers": top_rows[:5],
            "customer_growth": [],
            "revenue": float(total_revenue),
        }

