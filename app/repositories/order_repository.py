"""Order and payment repositories."""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload, noload

from app.utils.enums import OrderStatus, PaymentStatus
from app.models.order import Order, OrderItem, Payment
from app.repositories.base import BaseRepository


class OrderRepository(BaseRepository[Order]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, Order)

    def get_by_id(self, entity_id: int) -> Optional[Order]:
        return (
            self.db.query(Order)
            .options(
                joinedload(Order.items),
                joinedload(Order.payment),
            )
            .filter(Order.id == entity_id)
            .first()
        )

    def get_by_number(self, order_number: str) -> Optional[Order]:
        return (
            self.db.query(Order)
            .options(joinedload(Order.items), joinedload(Order.payment))
            .filter(Order.order_number == order_number)
            .first()
        )

    def list_for_user(self, user_id: int, skip: int = 0, limit: int = 50) -> list[Order]:
        # List views do not render line items — skip that join entirely
        return (
            self.db.query(Order)
            .options(joinedload(Order.payment), noload(Order.items))
            .filter(Order.user_id == user_id)
            .order_by(Order.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def list_all(
        self,
        *,
        status: Optional[OrderStatus] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[Order], int]:
        filters = []
        if status is not None:
            filters.append(Order.status == status)
        count_q = self.db.query(Order)
        for f in filters:
            count_q = count_q.filter(f)
        total = count_q.count()

        query = self.db.query(Order).options(
            joinedload(Order.payment), noload(Order.items)
        )
        for f in filters:
            query = query.filter(f)
        items = query.order_by(Order.created_at.desc()).offset(skip).limit(limit).all()
        return items, total

    def sales_by_day(
        self, start: datetime, end: datetime
    ) -> list[tuple[str, int, Decimal]]:
        rows = (
            self.db.query(
                func.date(Order.created_at).label("day"),
                func.count(Order.id),
                func.coalesce(func.sum(Order.total_amount), 0),
            )
            .filter(
                Order.created_at >= start,
                Order.created_at <= end,
                Order.status.in_(
                    [
                        OrderStatus.PAID,
                        OrderStatus.PROCESSING,
                        OrderStatus.SHIPPED,
                        OrderStatus.DELIVERED,
                    ]
                ),
            )
            .group_by(func.date(Order.created_at))
            .order_by(func.date(Order.created_at))
            .all()
        )
        return [(str(r[0]), int(r[1]), Decimal(str(r[2]))) for r in rows]


class PaymentRepository(BaseRepository[Payment]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, Payment)

    def get_by_intent(self, intent_id: str) -> Optional[Payment]:
        return (
            self.db.query(Payment)
            .filter(Payment.stripe_payment_intent_id == intent_id)
            .first()
        )

    def update_status(
        self,
        payment: Payment,
        status: PaymentStatus,
        failure_reason: Optional[str] = None,
    ) -> Payment:
        payment.status = status
        if failure_reason is not None:
            payment.failure_reason = failure_reason
        self.db.commit()
        self.db.refresh(payment)
        return payment
