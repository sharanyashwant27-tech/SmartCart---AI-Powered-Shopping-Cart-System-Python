"""Product reviews and gallery image services."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.utils.enums import OrderStatus
from app.utils.exceptions import ConflictError, ForbiddenError, NotFoundError, ValidationAppError
from app.models.order import Order, OrderItem
from app.models.review import ProductImage, Review
from app.repositories.base import BaseRepository
from app.repositories.product_repository import ProductRepository
from app.schemas.extra import (
    ProductImageCreate,
    ProductImageResponse,
    ReviewCreate,
    ReviewResponse,
    ReviewUpdate,
)


class ReviewService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.products = ProductRepository(db)

    def create(self, user_id: int, product_id: int, payload: ReviewCreate) -> ReviewResponse:
        product = self.products.get_by_id(product_id)
        if product is None:
            raise NotFoundError("Product not found")
        existing = (
            self.db.query(Review)
            .filter(Review.user_id == user_id, Review.product_id == product_id)
            .first()
        )
        if existing:
            raise ConflictError("You already reviewed this product")
        verified = (
            self.db.query(OrderItem.id)
            .join(Order)
            .filter(
                Order.user_id == user_id,
                OrderItem.product_id == product_id,
                Order.status.in_(
                    [
                        OrderStatus.PAID,
                        OrderStatus.PROCESSING,
                        OrderStatus.SHIPPED,
                        OrderStatus.DELIVERED,
                    ]
                ),
            )
            .first()
            is not None
        )
        review = Review(
            user_id=user_id,
            product_id=product_id,
            rating=payload.rating,
            title=payload.title,
            body=payload.body,
            is_verified_purchase=verified,
        )
        self.db.add(review)
        self.db.commit()
        self.db.refresh(review)
        self._refresh_product_rating(product_id)
        return self._to_response(review)

    def list_for_product(self, product_id: int) -> list[ReviewResponse]:
        rows = (
            self.db.query(Review)
            .options(joinedload(Review.user))
            .filter(Review.product_id == product_id)
            .order_by(Review.created_at.desc())
            .all()
        )
        return [self._to_response(r) for r in rows]

    def summary(self, product_id: int) -> dict:
        avg, count = (
            self.db.query(func.avg(Review.rating), func.count(Review.id))
            .filter(Review.product_id == product_id)
            .one()
        )
        return {
            "product_id": product_id,
            "average_rating": round(float(avg or 0), 2),
            "review_count": int(count or 0),
        }

    def update(self, user_id: int, review_id: int, payload: ReviewUpdate) -> ReviewResponse:
        review = self.db.get(Review, review_id)
        if review is None:
            raise NotFoundError("Review not found")
        if review.user_id != user_id:
            raise ForbiddenError("Not your review")
        for k, v in payload.model_dump(exclude_unset=True).items():
            setattr(review, k, v)
        self.db.commit()
        self.db.refresh(review)
        self._refresh_product_rating(review.product_id)
        return self._to_response(review)

    def delete(self, user_id: int, review_id: int, *, is_admin: bool = False) -> None:
        review = self.db.get(Review, review_id)
        if review is None:
            raise NotFoundError("Review not found")
        if review.user_id != user_id and not is_admin:
            raise ForbiddenError("Not your review")
        product_id = review.product_id
        self.db.delete(review)
        self.db.commit()
        self._refresh_product_rating(product_id)

    def _refresh_product_rating(self, product_id: int) -> None:
        avg, _count = (
            self.db.query(func.avg(Review.rating), func.count(Review.id))
            .filter(Review.product_id == product_id)
            .one()
        )
        product = self.products.get_by_id(product_id)
        if product is not None:
            product.rating = Decimal(str(round(float(avg or 0), 2)))
            self.db.commit()

    def _to_response(self, review: Review) -> ReviewResponse:
        name = None
        if getattr(review, "user", None) is not None:
            name = review.user.full_name
        return ReviewResponse(
            id=review.id,
            product_id=review.product_id,
            user_id=review.user_id,
            rating=review.rating,
            title=review.title,
            body=review.body,
            is_verified_purchase=review.is_verified_purchase,
            created_at=review.created_at,
            user_name=name,
        )


class ProductImageService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.products = ProductRepository(db)
        self.repo = BaseRepository(db, ProductImage)

    def list(self, product_id: int) -> list[ProductImageResponse]:
        rows = (
            self.db.query(ProductImage)
            .filter(ProductImage.product_id == product_id)
            .order_by(ProductImage.sort_order.asc(), ProductImage.id.asc())
            .all()
        )
        return [ProductImageResponse.model_validate(r) for r in rows]

    def add(self, product_id: int, payload: ProductImageCreate) -> ProductImageResponse:
        if self.products.get_by_id(product_id) is None:
            raise NotFoundError("Product not found")
        if payload.is_primary:
            self._clear_primary(product_id)
        img = ProductImage(product_id=product_id, **payload.model_dump())
        self.db.add(img)
        self.db.commit()
        self.db.refresh(img)
        return ProductImageResponse.model_validate(img)

    def delete(self, image_id: int) -> None:
        img = self.db.get(ProductImage, image_id)
        if img is None:
            raise NotFoundError("Image not found")
        self.db.delete(img)
        self.db.commit()

    def _clear_primary(self, product_id: int) -> None:
        (
            self.db.query(ProductImage)
            .filter(ProductImage.product_id == product_id, ProductImage.is_primary.is_(True))
            .update({"is_primary": False})
        )
        self.db.commit()
