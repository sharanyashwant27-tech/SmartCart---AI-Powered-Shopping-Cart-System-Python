"""Loyalty points service — earn / redeem for guest (customer) users."""

from __future__ import annotations

from decimal import Decimal
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.loyalty import LoyaltyTransaction
from app.models.order import Order
from app.models.user import User
from app.schemas.loyalty import (
    LoyaltyAccountResponse,
    LoyaltyPreviewResponse,
    LoyaltyRules,
    LoyaltyTransactionResponse,
)
from app.utils.enums import UserRole
from app.utils.exceptions import ForbiddenError, ValidationAppError
from app.services.cart_service import CartService, _money

settings = get_settings()


class LoyaltyService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def rules(self) -> LoyaltyRules:
        return LoyaltyRules(
            points_per_dollar=settings.loyalty_points_per_dollar,
            cents_per_point=settings.loyalty_cents_per_point,
            min_redeem_points=settings.loyalty_min_redeem_points,
            signup_bonus=settings.loyalty_signup_bonus,
        )

    def is_guest_customer(self, user: User) -> bool:
        return user.role == UserRole.CUSTOMER

    def get_balance(self, user: User) -> int:
        return int(getattr(user, "loyalty_points", 0) or 0)

    def account(self, user: User, limit: int = 20) -> LoyaltyAccountResponse:
        if not self.is_guest_customer(user):
            # Admins see empty loyalty account (feature is for guests)
            return LoyaltyAccountResponse(
                balance=0,
                lifetime_earned=0,
                lifetime_redeemed=0,
                rules=self.rules(),
                recent=[],
            )
        earned = (
            self.db.query(func.coalesce(func.sum(LoyaltyTransaction.points), 0))
            .filter(
                LoyaltyTransaction.user_id == user.id,
                LoyaltyTransaction.points > 0,
            )
            .scalar()
        )
        redeemed = (
            self.db.query(func.coalesce(func.sum(LoyaltyTransaction.points), 0))
            .filter(
                LoyaltyTransaction.user_id == user.id,
                LoyaltyTransaction.points < 0,
            )
            .scalar()
        )
        recent = (
            self.db.query(LoyaltyTransaction)
            .filter(LoyaltyTransaction.user_id == user.id)
            .order_by(LoyaltyTransaction.created_at.desc())
            .limit(limit)
            .all()
        )
        return LoyaltyAccountResponse(
            balance=self.get_balance(user),
            lifetime_earned=int(earned or 0),
            lifetime_redeemed=abs(int(redeemed or 0)),
            rules=self.rules(),
            recent=[LoyaltyTransactionResponse.model_validate(t) for t in recent],
        )

    def points_to_money(self, points: int) -> Decimal:
        return _money(Decimal(points) * Decimal(settings.loyalty_cents_per_point) / Decimal(100))

    def money_to_earn_points(self, amount: Decimal) -> int:
        if amount <= 0:
            return 0
        return int(amount) * int(settings.loyalty_points_per_dollar)

    def max_redeemable_for_total(self, balance: int, payable: Decimal) -> int:
        """Max points that can be applied without exceeding payable amount."""
        if balance <= 0 or payable <= 0:
            return 0
        cents = int(settings.loyalty_cents_per_point) or 1
        max_by_money = int((payable * 100) // cents)
        return max(0, min(balance, max_by_money))

    def validate_redeem(self, user: User, points: int, payable: Decimal) -> tuple[int, Decimal]:
        if points <= 0:
            return 0, Decimal("0.00")
        if not self.is_guest_customer(user):
            raise ForbiddenError("Loyalty points are for guest customers only")
        balance = self.get_balance(user)
        if points > balance:
            raise ValidationAppError(f"Not enough points (balance: {balance})")
        min_pts = settings.loyalty_min_redeem_points
        if points < min_pts:
            raise ValidationAppError(f"Redeem at least {min_pts} points")
        max_pts = self.max_redeemable_for_total(balance, payable)
        if points > max_pts:
            raise ValidationAppError(
                f"Can redeem at most {max_pts} points for this order"
            )
        return points, self.points_to_money(points)

    def preview(
        self, user: User, redeem_points: int = 0, coupon_code: Optional[str] = None
    ) -> LoyaltyPreviewResponse:
        cart = CartService(self.db).calculate_totals(user.id, coupon_code)
        balance = self.get_balance(user) if self.is_guest_customer(user) else 0
        pts = 0
        discount = Decimal("0.00")
        if redeem_points and self.is_guest_customer(user):
            # Soft-clamp for preview (don't raise for UI typing)
            max_pts = self.max_redeemable_for_total(balance, cart.total)
            min_pts = settings.loyalty_min_redeem_points
            if redeem_points >= min_pts:
                pts = min(redeem_points, max_pts)
                discount = self.points_to_money(pts)
        total_after = _money(max(cart.total - discount, Decimal("0")))
        return LoyaltyPreviewResponse(
            balance=balance,
            redeem_points=pts,
            points_discount=float(discount),
            estimated_earn=self.money_to_earn_points(total_after)
            if self.is_guest_customer(user)
            else 0,
            cart_total=float(total_after),
            rules=self.rules(),
        )

    def _apply_delta(
        self,
        user: User,
        delta: int,
        tx_type: str,
        note: Optional[str] = None,
        order_id: Optional[int] = None,
        commit: bool = False,
    ) -> LoyaltyTransaction:
        if delta == 0:
            raise ValidationAppError("Points delta cannot be zero")
        balance = self.get_balance(user)
        new_balance = balance + delta
        if new_balance < 0:
            raise ValidationAppError("Insufficient loyalty points")
        user.loyalty_points = new_balance
        tx = LoyaltyTransaction(
            user_id=user.id,
            order_id=order_id,
            points=delta,
            balance_after=new_balance,
            tx_type=tx_type,
            note=note,
        )
        self.db.add(tx)
        if commit:
            self.db.commit()
            self.db.refresh(tx)
        else:
            self.db.flush()
        return tx

    def grant_signup_bonus(self, user: User) -> Optional[LoyaltyTransaction]:
        bonus = int(settings.loyalty_signup_bonus or 0)
        if bonus <= 0 or not self.is_guest_customer(user):
            return None
        if self.get_balance(user) > 0:
            return None
        existing = (
            self.db.query(LoyaltyTransaction)
            .filter(
                LoyaltyTransaction.user_id == user.id,
                LoyaltyTransaction.tx_type == "signup",
            )
            .first()
        )
        if existing:
            return None
        return self._apply_delta(
            user,
            bonus,
            "signup",
            note=f"Welcome bonus · {bonus} points",
            commit=True,
        )

    def redeem_for_order(self, user: User, order: Order, points: int) -> Decimal:
        """Debit points at checkout; returns money discount applied."""
        if points <= 0:
            order.points_redeemed = 0
            return Decimal("0.00")
        pts, money = self.validate_redeem(user, points, order.total_amount + Decimal("0"))
        # Note: caller should pass payable before points discount
        self._apply_delta(
            user,
            -pts,
            "redeem",
            note=f"Redeemed on order {order.order_number}",
            order_id=order.id,
        )
        order.points_redeemed = pts
        return money

    def redeem_against_payable(
        self, user: User, order: Order, points: int, payable_before: Decimal
    ) -> Decimal:
        if points <= 0:
            order.points_redeemed = 0
            return Decimal("0.00")
        pts, money = self.validate_redeem(user, points, payable_before)
        self._apply_delta(
            user,
            -pts,
            "redeem",
            note=f"Redeemed on order {order.order_number}",
            order_id=order.id,
        )
        order.points_redeemed = pts
        return money

    def earn_for_paid_order(self, user: User, order: Order) -> int:
        if not self.is_guest_customer(user):
            order.points_earned = 0
            return 0
        # Don't double-earn
        existing = (
            self.db.query(LoyaltyTransaction)
            .filter(
                LoyaltyTransaction.order_id == order.id,
                LoyaltyTransaction.tx_type == "earn",
            )
            .first()
        )
        if existing:
            return existing.points
        pts = self.money_to_earn_points(Decimal(str(order.total_amount)))
        if pts <= 0:
            order.points_earned = 0
            return 0
        self._apply_delta(
            user,
            pts,
            "earn",
            note=f"Earned from order {order.order_number}",
            order_id=order.id,
        )
        order.points_earned = pts
        return pts

    def restore_redeem_on_failed_payment(self, user: User, order: Order) -> None:
        pts = int(getattr(order, "points_redeemed", 0) or 0)
        if pts <= 0:
            return
        existing = (
            self.db.query(LoyaltyTransaction)
            .filter(
                LoyaltyTransaction.order_id == order.id,
                LoyaltyTransaction.tx_type == "redeem_refund",
            )
            .first()
        )
        if existing:
            return
        self._apply_delta(
            user,
            pts,
            "redeem_refund",
            note=f"Restored points · payment failed for {order.order_number}",
            order_id=order.id,
        )

    def reverse_earn_on_refund(self, user: User, order: Order) -> None:
        pts = int(getattr(order, "points_earned", 0) or 0)
        if pts <= 0:
            return
        existing = (
            self.db.query(LoyaltyTransaction)
            .filter(
                LoyaltyTransaction.order_id == order.id,
                LoyaltyTransaction.tx_type == "earn_reversal",
            )
            .first()
        )
        if existing:
            return
        # Cap reversal to available balance
        balance = self.get_balance(user)
        take = min(pts, balance)
        if take <= 0:
            order.points_earned = 0
            return
        self._apply_delta(
            user,
            -take,
            "earn_reversal",
            note=f"Reversed earn · refund/cancel {order.order_number}",
            order_id=order.id,
        )
        order.points_earned = max(0, pts - take)
