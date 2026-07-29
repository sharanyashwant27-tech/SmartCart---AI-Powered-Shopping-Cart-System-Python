"""Wishlist domain routes."""

from fastapi import APIRouter

from app.utils.dependencies import CurrentUser, DbSession
from app.schemas.cart import WishlistItemCreate, WishlistItemResponse
from app.schemas.user import MessageResponse
from app.services.cart_service import WishlistService

router = APIRouter(prefix="/wishlist", tags=["Wishlist"])


@router.get("", response_model=list[WishlistItemResponse])
async def get_wishlist(user: CurrentUser, db: DbSession) -> list[WishlistItemResponse]:
    return WishlistService(db).list(user.id)


@router.post("", response_model=WishlistItemResponse, status_code=201)
async def add_wishlist(
    payload: WishlistItemCreate, user: CurrentUser, db: DbSession
) -> WishlistItemResponse:
    item = WishlistService(db).add(user.id, payload.product_id)
    items = WishlistService(db).list(user.id)
    return next(i for i in items if i.id == item.id)


@router.delete("/{item_id}", response_model=MessageResponse)
async def remove_wishlist(
    item_id: int, user: CurrentUser, db: DbSession
) -> MessageResponse:
    WishlistService(db).remove(user.id, item_id)
    return MessageResponse(message="Removed from wishlist")
