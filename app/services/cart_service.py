"""Shopping cart, wishlist, and coupon services."""

from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from sqlalchemy.orm import Session

from app.config import get_settings
from app.utils.enums import CartItemStatus, CouponType
from app.utils.exceptions import ConflictError, NotFoundError, ValidationAppError
from app.models.cart import CartItem, WishlistItem
from app.models.coupon import Coupon
from app.repositories.cart_repository import (
    CartRepository,
    CouponRepository,
    WishlistRepository,
)
from app.repositories.product_repository import ProductRepository
from app.schemas.cart import (
    ApplyCouponRequest,
    CartItemCreate,
    CartItemResponse,
    CartItemUpdate,
    CartSummary,
    CouponCreate,
    CouponUpdate,
    WishlistItemResponse,
)
from app.schemas.product import CartProductSummary, ProductResponse

settings = get_settings()
MONEY = Decimal("0.01")


def _money(value: Decimal | float | int) -> Decimal:
    return Decimal(str(value)).quantize(MONEY, rounding=ROUND_HALF_UP)


class CouponService:
    def __init__(self, db: Session) -> None:
        self.repo = CouponRepository(db)

    def create(self, payload: CouponCreate) -> Coupon:
        code = payload.code.upper()
        if self.repo.get_by_code(code):
            raise ConflictError("Coupon code already exists")
        entity = Coupon(
            code=code,
            description=payload.description,
            coupon_type=payload.coupon_type,
            discount=payload.value,
            min_order_amount=payload.min_order_amount,
            max_discount=payload.max_discount,
            usage_limit=payload.usage_limit,
            starts_at=payload.starts_at,
            expiry=payload.ends_at,
            active=payload.is_active,
        )
        return self.repo.create(entity)

    def list(self) -> list[Coupon]:
        return self.repo.list(limit=500, order_by=Coupon.created_at.desc())

    def get(self, coupon_id: int) -> Coupon:
        entity = self.repo.get_by_id(coupon_id)
        if entity is None:
            raise NotFoundError("Coupon not found")
        return entity

    def update(self, coupon_id: int, payload: CouponUpdate) -> Coupon:
        entity = self.get(coupon_id)
        data = payload.model_dump(exclude_unset=True)
        # Map API field names onto design columns
        if "value" in data:
            data["discount"] = data.pop("value")
        if "ends_at" in data:
            data["expiry"] = data.pop("ends_at")
        if "is_active" in data:
            data["active"] = data.pop("is_active")
        return self.repo.update(entity, data)

    def delete(self, coupon_id: int) -> None:
        self.repo.delete(self.get(coupon_id))

    def validate_and_compute(self, code: str, subtotal: Decimal) -> tuple[Coupon, Decimal]:
        coupon = self.repo.get_by_code(code.upper())
        if coupon is None or not coupon.is_active:
            raise ValidationAppError("Invalid or inactive coupon")
        now = datetime.now(timezone.utc)
        if coupon.starts_at and coupon.starts_at.replace(tzinfo=timezone.utc) > now:
            raise ValidationAppError("Coupon is not yet active")
        if coupon.ends_at and coupon.ends_at.replace(tzinfo=timezone.utc) < now:
            raise ValidationAppError("Coupon has expired")
        if coupon.usage_limit is not None and coupon.used_count >= coupon.usage_limit:
            raise ValidationAppError("Coupon usage limit reached")
        if subtotal < coupon.min_order_amount:
            raise ValidationAppError(
                f"Minimum order amount of {coupon.min_order_amount} required"
            )
        if coupon.coupon_type == CouponType.PERCENTAGE:
            discount = _money(subtotal * (coupon.value / Decimal("100")))
        else:
            discount = _money(coupon.value)
        if coupon.max_discount is not None:
            discount = min(discount, _money(coupon.max_discount))
        discount = min(discount, subtotal)
        return coupon, discount

    def increment_usage(self, coupon: Coupon) -> None:
        coupon.used_count += 1
        self.repo.save(coupon)


class CartService:
    def __init__(self, db: Session) -> None:
        self.cart = CartRepository(db)
        self.products = ProductRepository(db)
        self.coupons = CouponService(db)
        self._applied_coupon: Optional[str] = None

    def add_item(self, user_id: int, payload: CartItemCreate) -> CartItem:
        product = self.products.get_by_id(payload.product_id)
        if product is None or not product.is_active:
            raise NotFoundError("Product not found")
        if product.stock_quantity < payload.quantity:
            raise ValidationAppError("Insufficient stock")
        existing = self.cart.get_item(user_id, payload.product_id, CartItemStatus.ACTIVE)
        if existing:
            new_qty = existing.quantity + payload.quantity
            if product.stock_quantity < new_qty:
                raise ValidationAppError("Insufficient stock")
            existing.quantity = new_qty
            existing.refresh_totals()
            return self.cart.save(existing)
        item = CartItem(
            user_id=user_id,
            product_id=payload.product_id,
            quantity=payload.quantity,
            status=CartItemStatus.ACTIVE,
            price=Decimal(str(product.price)),
            subtotal=Decimal(str(product.price)) * payload.quantity,
        )
        return self.cart.create(item)

    def update_quantity(self, user_id: int, item_id: int, payload: CartItemUpdate) -> CartItem:
        item = self.cart.get_user_item_by_id(user_id, item_id)
        if item is None:
            raise NotFoundError("Cart item not found")
        if item.product.stock_quantity < payload.quantity:
            raise ValidationAppError("Insufficient stock")
        item.quantity = payload.quantity
        item.refresh_totals()
        return self.cart.save(item)

    def remove_item(self, user_id: int, item_id: int) -> None:
        item = self.cart.get_user_item_by_id(user_id, item_id)
        if item is None:
            raise NotFoundError("Cart item not found")
        self.cart.delete(item)

    def save_for_later(self, user_id: int, item_id: int) -> CartItem:
        item = self.cart.get_user_item_by_id(user_id, item_id)
        if item is None:
            raise NotFoundError("Cart item not found")
        if item.status == CartItemStatus.SAVED_FOR_LATER:
            return item
        # Merge if already saved
        saved = self.cart.get_item(user_id, item.product_id, CartItemStatus.SAVED_FOR_LATER)
        if saved:
            saved.quantity += item.quantity
            self.cart.delete(item)
            return self.cart.save(saved)
        item.status = CartItemStatus.SAVED_FOR_LATER
        return self.cart.save(item)

    def move_to_cart(self, user_id: int, item_id: int) -> CartItem:
        item = self.cart.get_user_item_by_id(user_id, item_id)
        if item is None:
            raise NotFoundError("Cart item not found")
        active = self.cart.get_item(user_id, item.product_id, CartItemStatus.ACTIVE)
        if active:
            active.quantity += item.quantity
            self.cart.delete(item)
            return self.cart.save(active)
        item.status = CartItemStatus.ACTIVE
        return self.cart.save(item)

    def _to_response(self, item: CartItem) -> CartItemResponse:
        line = _money(Decimal(str(item.product.price)) * item.quantity)
        return CartItemResponse(
            id=item.id,
            product_id=item.product_id,
            quantity=item.quantity,
            status=item.status,
            product=CartProductSummary.model_validate(item.product),
            line_total=line,
            created_at=item.created_at,
        )

    def calculate_totals(
        self, user_id: int, coupon_code: Optional[str] = None
    ) -> CartSummary:
        active = self.cart.get_user_items(user_id, CartItemStatus.ACTIVE)
        # Skip saved-for-later query on the hot cart path (SPA does not render it)
        active_resp = [self._to_response(i) for i in active]
        saved_resp: list[CartItemResponse] = []
        subtotal = _money(sum((i.line_total for i in active_resp), Decimal("0")))
        discount = Decimal("0.00")
        applied = None
        if coupon_code:
            _, discount = self.coupons.validate_and_compute(coupon_code, subtotal)
            applied = coupon_code.upper()
        taxable = max(subtotal - discount, Decimal("0"))
        if taxable >= Decimal(str(settings.free_shipping_threshold)):
            shipping = Decimal("0.00")
        else:
            shipping = _money(settings.default_shipping_flat) if active_resp else Decimal("0.00")
        tax = _money(taxable * Decimal(str(settings.default_tax_rate)))
        total = _money(taxable + shipping + tax)
        return CartSummary(
            items=active_resp,
            saved_for_later=saved_resp,
            subtotal=subtotal,
            discount_amount=discount,
            shipping_amount=shipping,
            tax_amount=tax,
            total=total,
            coupon_code=applied,
            item_count=sum(i.quantity for i in active_resp),
        )

    def apply_coupon(self, user_id: int, payload: ApplyCouponRequest) -> CartSummary:
        return self.calculate_totals(user_id, payload.code)


class WishlistService:
    def __init__(self, db: Session) -> None:
        self.repo = WishlistRepository(db)
        self.products = ProductRepository(db)

    def add(self, user_id: int, product_id: int) -> WishlistItem:
        product = self.products.get_by_id(product_id)
        if product is None or not product.is_active:
            raise NotFoundError("Product not found")
        existing = self.repo.get_item(user_id, product_id)
        if existing:
            return existing
        return self.repo.create(WishlistItem(user_id=user_id, product_id=product_id))

    def list(self, user_id: int) -> list[WishlistItemResponse]:
        items = self.repo.get_user_items(user_id)
        return [
            WishlistItemResponse(
                id=i.id,
                product_id=i.product_id,
                product=ProductResponse.model_validate(i.product),
                created_at=i.created_at,
            )
            for i in items
        ]

    def remove(self, user_id: int, item_id: int) -> None:
        item = self.repo.get_by_id(item_id)
        if item is None or item.user_id != user_id:
            raise NotFoundError("Wishlist item not found")
        self.repo.delete(item)
