"""Category and brand API routes."""

from fastapi import APIRouter, Query

from app.utils.dependencies import AdminUser, DbSession
from app.schemas.product import (
    BrandCreate,
    BrandResponse,
    BrandUpdate,
    CategoryCreate,
    CategoryResponse,
    CategoryUpdate,
)
from app.schemas.user import MessageResponse
from app.services.product_service import BrandService, CategoryService

categories_router = APIRouter(prefix="/categories", tags=["Categories"])
brands_router = APIRouter(prefix="/brands", tags=["Brands"])


@categories_router.get("", response_model=list[CategoryResponse])
async def list_categories(
    db: DbSession, active_only: bool = Query(True)
) -> list[CategoryResponse]:
    return [
        CategoryResponse.model_validate(c)
        for c in CategoryService(db).list(active_only=active_only)
    ]


@categories_router.get("/{category_id}", response_model=CategoryResponse)
async def get_category(category_id: int, db: DbSession) -> CategoryResponse:
    return CategoryResponse.model_validate(CategoryService(db).get(category_id))


@categories_router.post("", response_model=CategoryResponse, status_code=201)
async def create_category(
    payload: CategoryCreate, _: AdminUser, db: DbSession
) -> CategoryResponse:
    return CategoryResponse.model_validate(CategoryService(db).create(payload))


@categories_router.patch("/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: int, payload: CategoryUpdate, _: AdminUser, db: DbSession
) -> CategoryResponse:
    return CategoryResponse.model_validate(
        CategoryService(db).update(category_id, payload)
    )


@categories_router.delete("/{category_id}", response_model=MessageResponse)
async def delete_category(
    category_id: int, _: AdminUser, db: DbSession
) -> MessageResponse:
    CategoryService(db).delete(category_id)
    return MessageResponse(message="Category deleted")


@brands_router.get("", response_model=list[BrandResponse])
async def list_brands(
    db: DbSession, active_only: bool = Query(True)
) -> list[BrandResponse]:
    return [
        BrandResponse.model_validate(b)
        for b in BrandService(db).list(active_only=active_only)
    ]


@brands_router.post("", response_model=BrandResponse, status_code=201)
async def create_brand(
    payload: BrandCreate, _: AdminUser, db: DbSession
) -> BrandResponse:
    return BrandResponse.model_validate(BrandService(db).create(payload))


@brands_router.patch("/{brand_id}", response_model=BrandResponse)
async def update_brand(
    brand_id: int, payload: BrandUpdate, _: AdminUser, db: DbSession
) -> BrandResponse:
    return BrandResponse.model_validate(BrandService(db).update(brand_id, payload))


@brands_router.delete("/{brand_id}", response_model=MessageResponse)
async def delete_brand(brand_id: int, _: AdminUser, db: DbSession) -> MessageResponse:
    BrandService(db).delete(brand_id)
    return MessageResponse(message="Brand deleted")
