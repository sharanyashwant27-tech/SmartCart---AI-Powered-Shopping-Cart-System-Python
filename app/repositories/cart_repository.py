"""Cart, wishlist, and coupon repositories."""

from typing import Optional

from sqlalchemy.orm import Session, joinedload

from app.utils.enums import CartItemStatus
from app.models.cart import CartItem, WishlistItem
from app.models.coupon import Coupon
from app.repositories.base import BaseRepository


class CartRepository(BaseRepository[CartItem]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, CartItem)

    def get_user_items(
        self, user_id: int, status: Optional[CartItemStatus] = None
    ) -> list[CartItem]:
        query = (
            self.db.query(CartItem)
            .options(joinedload(CartItem.product))
            .filter(CartItem.user_id == user_id)
        )
        if status is not None:
            query = query.filter(CartItem.status == status)
        return query.order_by(CartItem.updated_at.desc()).all()

    def get_item(
        self, user_id: int, product_id: int, status: CartItemStatus
    ) -> Optional[CartItem]:
        return (
            self.db.query(CartItem)
            .options(joinedload(CartItem.product))
            .filter(
                CartItem.user_id == user_id,
                CartItem.product_id == product_id,
                CartItem.status == status,
            )
            .first()
        )

    def get_user_item_by_id(self, user_id: int, item_id: int) -> Optional[CartItem]:
        return (
            self.db.query(CartItem)
            .options(joinedload(CartItem.product))
            .filter(CartItem.id == item_id, CartItem.user_id == user_id)
            .first()
        )

    def clear_active(self, user_id: int) -> None:
        (
            self.db.query(CartItem)
            .filter(
                CartItem.user_id == user_id,
                CartItem.status == CartItemStatus.ACTIVE,
            )
            .delete(synchronize_session=False)
        )
        self.db.commit()


class WishlistRepository(BaseRepository[WishlistItem]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, WishlistItem)

    def get_user_items(self, user_id: int) -> list[WishlistItem]:
        return (
            self.db.query(WishlistItem)
            .options(joinedload(WishlistItem.product))
            .filter(WishlistItem.user_id == user_id)
            .order_by(WishlistItem.created_at.desc())
            .all()
        )

    def get_item(self, user_id: int, product_id: int) -> Optional[WishlistItem]:
        return (
            self.db.query(WishlistItem)
            .filter(
                WishlistItem.user_id == user_id,
                WishlistItem.product_id == product_id,
            )
            .first()
        )


class CouponRepository(BaseRepository[Coupon]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, Coupon)

    def get_by_code(self, code: str) -> Optional[Coupon]:
        return (
            self.db.query(Coupon)
            .filter(Coupon.code == code.upper())
            .first()
        )
