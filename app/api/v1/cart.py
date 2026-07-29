"""Cart, wishlist, and coupon API routes."""

from fastapi import APIRouter

from app.utils.dependencies import AdminUser, CurrentUser, DbSession
from app.schemas.cart import (
    ApplyCouponRequest,
    CartItemCreate,
    CartItemResponse,
    CartItemUpdate,
    CartSummary,
    CouponCreate,
    CouponResponse,
    CouponUpdate,
    WishlistItemCreate,
    WishlistItemResponse,
)
from app.schemas.product import ProductResponse
from app.schemas.user import MessageResponse
from app.services.cart_service import CartService, CouponService, WishlistService

cart_router = APIRouter(prefix="/cart", tags=["Shopping Cart"])
wishlist_router = APIRouter(prefix="/wishlist", tags=["Wishlist"])
coupons_router = APIRouter(prefix="/coupons", tags=["Coupons"])


def _item_response(item) -> CartItemResponse:  # noqa: ANN001
    from decimal import Decimal

    from app.services.cart_service import _money

    line = _money(Decimal(str(item.product.price)) * item.quantity)
    return CartItemResponse(
        id=item.id,
        product_id=item.product_id,
        quantity=item.quantity,
        status=item.status,
        product=ProductResponse.model_validate(item.product),
        line_total=line,
        created_at=item.created_at,
    )


@cart_router.get("", response_model=CartSummary)
async def get_cart(user: CurrentUser, db: DbSession) -> CartSummary:
    return CartService(db).calculate_totals(user.id)


@cart_router.post("/items", response_model=CartItemResponse, status_code=201)
async def add_to_cart(
    payload: CartItemCreate, user: CurrentUser, db: DbSession
) -> CartItemResponse:
    item = CartService(db).add_item(user.id, payload)
    # Reload with product
    item = CartService(db).cart.get_user_item_by_id(user.id, item.id)
    return _item_response(item)


@cart_router.patch("/items/{item_id}", response_model=CartItemResponse)
async def update_cart_item(
    item_id: int, payload: CartItemUpdate, user: CurrentUser, db: DbSession
) -> CartItemResponse:
    item = CartService(db).update_quantity(user.id, item_id, payload)
    return _item_response(item)


@cart_router.delete("/items/{item_id}", response_model=MessageResponse)
async def remove_cart_item(
    item_id: int, user: CurrentUser, db: DbSession
) -> MessageResponse:
    CartService(db).remove_item(user.id, item_id)
    return MessageResponse(message="Item removed from cart")


@cart_router.post("/items/{item_id}/save-for-later", response_model=CartItemResponse)
async def save_for_later(
    item_id: int, user: CurrentUser, db: DbSession
) -> CartItemResponse:
    item = CartService(db).save_for_later(user.id, item_id)
    return _item_response(item)


@cart_router.post("/items/{item_id}/move-to-cart", response_model=CartItemResponse)
async def move_to_cart(
    item_id: int, user: CurrentUser, db: DbSession
) -> CartItemResponse:
    item = CartService(db).move_to_cart(user.id, item_id)
    return _item_response(item)


@cart_router.post("/apply-coupon", response_model=CartSummary)
async def apply_coupon(
    payload: ApplyCouponRequest, user: CurrentUser, db: DbSession
) -> CartSummary:
    return CartService(db).apply_coupon(user.id, payload)


@wishlist_router.get("", response_model=list[WishlistItemResponse])
async def get_wishlist(
    user: CurrentUser, db: DbSession
) -> list[WishlistItemResponse]:
    return WishlistService(db).list(user.id)


@wishlist_router.post("", response_model=WishlistItemResponse, status_code=201)
async def add_wishlist(
    payload: WishlistItemCreate, user: CurrentUser, db: DbSession
) -> WishlistItemResponse:
    item = WishlistService(db).add(user.id, payload.product_id)
    items = WishlistService(db).list(user.id)
    return next(i for i in items if i.id == item.id)


@wishlist_router.delete("/{item_id}", response_model=MessageResponse)
async def remove_wishlist(
    item_id: int, user: CurrentUser, db: DbSession
) -> MessageResponse:
    WishlistService(db).remove(user.id, item_id)
    return MessageResponse(message="Removed from wishlist")


@coupons_router.get("", response_model=list[CouponResponse])
async def list_coupons(_: AdminUser, db: DbSession) -> list[CouponResponse]:
    return [CouponResponse.model_validate(c) for c in CouponService(db).list()]


@coupons_router.post("", response_model=CouponResponse, status_code=201)
async def create_coupon(
    payload: CouponCreate, _: AdminUser, db: DbSession
) -> CouponResponse:
    return CouponResponse.model_validate(CouponService(db).create(payload))


@coupons_router.patch("/{coupon_id}", response_model=CouponResponse)
async def update_coupon(
    coupon_id: int, payload: CouponUpdate, _: AdminUser, db: DbSession
) -> CouponResponse:
    return CouponResponse.model_validate(
        CouponService(db).update(coupon_id, payload)
    )


@coupons_router.delete("/{coupon_id}", response_model=MessageResponse)
async def delete_coupon(
    coupon_id: int, _: AdminUser, db: DbSession
) -> MessageResponse:
    CouponService(db).delete(coupon_id)
    return MessageResponse(message="Coupon deleted")
