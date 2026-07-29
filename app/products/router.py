"""Product API routes."""

from typing import Optional

from fastapi import APIRouter, Query

from app.utils.dependencies import AdminUser, DbSession
from app.schemas.product import (
    ProductCreate,
    ProductListResponse,
    ProductResponse,
    ProductUpdate,
)
from app.schemas.user import MessageResponse
from app.services.product_service import ProductService

router = APIRouter(prefix="/products", tags=["Products"])


@router.get("", response_model=ProductListResponse)
async def list_products(
    db: DbSession,
    q: Optional[str] = None,
    category_id: Optional[int] = None,
    brand_id: Optional[int] = None,
    featured: Optional[bool] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    active_only: bool = True,
) -> ProductListResponse:
    return ProductService(db).list_products(
        q=q,
        category_id=category_id,
        brand_id=brand_id,
        featured=featured,
        active_only=active_only,
        page=page,
        page_size=page_size,
    )


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(product_id: int, db: DbSession) -> ProductResponse:
    return ProductResponse.model_validate(ProductService(db).get(product_id))


@router.get("/slug/{slug}", response_model=ProductResponse)
async def get_product_by_slug(slug: str, db: DbSession) -> ProductResponse:
    return ProductResponse.model_validate(ProductService(db).get_by_slug(slug))


@router.post("", response_model=ProductResponse, status_code=201)
async def create_product(
    payload: ProductCreate, _: AdminUser, db: DbSession
) -> ProductResponse:
    return ProductResponse.model_validate(ProductService(db).create(payload))


@router.patch("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: int, payload: ProductUpdate, _: AdminUser, db: DbSession
) -> ProductResponse:
    return ProductResponse.model_validate(
        ProductService(db).update(product_id, payload)
    )


@router.delete("/{product_id}", response_model=MessageResponse)
async def delete_product(
    product_id: int, _: AdminUser, db: DbSession
) -> MessageResponse:
    ProductService(db).delete(product_id)
    return MessageResponse(message="Product deleted")
