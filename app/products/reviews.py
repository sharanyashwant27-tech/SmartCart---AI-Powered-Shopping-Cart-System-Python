"""Product reviews and gallery image routes."""

from fastapi import APIRouter

from app.utils.dependencies import AdminUser, CurrentUser, DbSession
from app.utils.enums import UserRole
from app.schemas.extra import (
    ProductImageCreate,
    ProductImageResponse,
    ReviewCreate,
    ReviewResponse,
    ReviewUpdate,
)
from app.schemas.user import MessageResponse
from app.services.review_service import ProductImageService, ReviewService

reviews_router = APIRouter(tags=["Reviews"])
images_router = APIRouter(tags=["Product Images"])


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
