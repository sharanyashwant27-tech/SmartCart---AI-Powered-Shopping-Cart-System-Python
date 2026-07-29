"""Addresses, reviews, product images, and forgot-password routes."""

from fastapi import APIRouter

from app.utils.dependencies import AdminUser, CurrentUser, DbSession
from app.utils.enums import UserRole
from app.schemas.extra import (
    AddressCreate,
    AddressResponse,
    AddressUpdate,
    ForgotPasswordRequest,
    ProductImageCreate,
    ProductImageResponse,
    ResetPasswordRequest,
    ReviewCreate,
    ReviewResponse,
    ReviewUpdate,
)
from app.schemas.user import MessageResponse
from app.services.address_service import AddressService, PasswordResetService
from app.services.review_service import ProductImageService, ReviewService

addresses_router = APIRouter(prefix="/addresses", tags=["Address Book"])
reviews_router = APIRouter(tags=["Reviews"])
images_router = APIRouter(tags=["Product Images"])
password_router = APIRouter(prefix="/auth", tags=["Authentication"])


@password_router.post("/forgot-password")
async def forgot_password(payload: ForgotPasswordRequest, db: DbSession) -> dict:
    """Request a password reset token (returned in sandbox/dev responses)."""
    return PasswordResetService(db).request_reset(payload.email)


@password_router.post("/reset-password", response_model=MessageResponse)
async def reset_password(payload: ResetPasswordRequest, db: DbSession) -> MessageResponse:
    return PasswordResetService(db).reset_password(payload)


@addresses_router.get("", response_model=list[AddressResponse])
async def list_addresses(user: CurrentUser, db: DbSession) -> list[AddressResponse]:
    return AddressService(db).list(user.id)


@addresses_router.post("", response_model=AddressResponse, status_code=201)
async def create_address(
    payload: AddressCreate, user: CurrentUser, db: DbSession
) -> AddressResponse:
    return AddressService(db).create(user.id, payload)


@addresses_router.patch("/{address_id}", response_model=AddressResponse)
async def update_address(
    address_id: int, payload: AddressUpdate, user: CurrentUser, db: DbSession
) -> AddressResponse:
    return AddressService(db).update(user.id, address_id, payload)


@addresses_router.delete("/{address_id}", response_model=MessageResponse)
async def delete_address(
    address_id: int, user: CurrentUser, db: DbSession
) -> MessageResponse:
    AddressService(db).delete(user.id, address_id)
    return MessageResponse(message="Address deleted")


@reviews_router.get("/products/{product_id}/reviews", response_model=list[ReviewResponse])
async def list_reviews(product_id: int, db: DbSession) -> list[ReviewResponse]:
    return ReviewService(db).list_for_product(product_id)


@reviews_router.get("/products/{product_id}/ratings")
async def product_ratings(product_id: int, db: DbSession) -> dict:
    return ReviewService(db).summary(product_id)


@reviews_router.post(
    "/products/{product_id}/reviews", response_model=ReviewResponse, status_code=201
)
async def create_review(
    product_id: int, payload: ReviewCreate, user: CurrentUser, db: DbSession
) -> ReviewResponse:
    return ReviewService(db).create(user.id, product_id, payload)


@reviews_router.patch("/reviews/{review_id}", response_model=ReviewResponse)
async def update_review(
    review_id: int, payload: ReviewUpdate, user: CurrentUser, db: DbSession
) -> ReviewResponse:
    return ReviewService(db).update(user.id, review_id, payload)


@reviews_router.delete("/reviews/{review_id}", response_model=MessageResponse)
async def delete_review(
    review_id: int, user: CurrentUser, db: DbSession
) -> MessageResponse:
    ReviewService(db).delete(
        user.id, review_id, is_admin=user.role == UserRole.ADMIN
    )
    return MessageResponse(message="Review deleted")


@images_router.get(
    "/products/{product_id}/images", response_model=list[ProductImageResponse]
)
async def list_images(product_id: int, db: DbSession) -> list[ProductImageResponse]:
    return ProductImageService(db).list(product_id)


@images_router.post(
    "/products/{product_id}/images",
    response_model=ProductImageResponse,
    status_code=201,
)
async def add_image(
    product_id: int,
    payload: ProductImageCreate,
    _: AdminUser,
    db: DbSession,
) -> ProductImageResponse:
    return ProductImageService(db).add(product_id, payload)


@images_router.delete("/products/images/{image_id}", response_model=MessageResponse)
async def delete_image(image_id: int, _: AdminUser, db: DbSession) -> MessageResponse:
    ProductImageService(db).delete(image_id)
    return MessageResponse(message="Image deleted")
