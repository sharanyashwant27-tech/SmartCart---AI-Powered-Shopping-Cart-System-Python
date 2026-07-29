"""Product, category, and brand services."""

from math import ceil
from typing import Optional

from sqlalchemy.orm import Session

from app.utils.exceptions import ConflictError, NotFoundError
from app.models.category import Brand, Category
from app.models.product import Product
from app.repositories.product_repository import (
    BrandRepository,
    CategoryRepository,
    ProductRepository,
)
from app.schemas.product import (
    BrandCreate,
    BrandUpdate,
    CategoryCreate,
    CategoryUpdate,
    ProductCreate,
    ProductListItem,
    ProductListResponse,
    ProductResponse,
    ProductUpdate,
)
from app.utils.helpers import slugify


class CategoryService:
    def __init__(self, db: Session) -> None:
        self.repo = CategoryRepository(db)

    def create(self, payload: CategoryCreate) -> Category:
        if self.repo.get_by_name(payload.name):
            raise ConflictError("Category name already exists")
        slug = payload.slug or slugify(payload.name)
        if self.repo.get_by_slug(slug):
            raise ConflictError("Category slug already exists")
        entity = Category(
            name=payload.name,
            slug=slug,
            description=payload.description,
            parent_id=payload.parent_id,
            is_active=payload.is_active,
        )
        return self.repo.create(entity)

    def list(self, active_only: bool = False) -> list[Category]:
        filters = [Category.is_active.is_(True)] if active_only else None
        return self.repo.list(limit=500, filters=filters, order_by=Category.name.asc())

    def get(self, category_id: int) -> Category:
        entity = self.repo.get_by_id(category_id)
        if entity is None:
            raise NotFoundError("Category not found")
        return entity

    def update(self, category_id: int, payload: CategoryUpdate) -> Category:
        entity = self.get(category_id)
        data = payload.model_dump(exclude_unset=True)
        if "name" in data and data["name"] != entity.name:
            if self.repo.get_by_name(data["name"]):
                raise ConflictError("Category name already exists")
            data.setdefault("slug", slugify(data["name"]))
        return self.repo.update(entity, data)

    def delete(self, category_id: int) -> None:
        entity = self.get(category_id)
        self.repo.delete(entity)


class BrandService:
    def __init__(self, db: Session) -> None:
        self.repo = BrandRepository(db)

    def create(self, payload: BrandCreate) -> Brand:
        slug = payload.slug or slugify(payload.name)
        if self.repo.get_by_slug(slug):
            raise ConflictError("Brand slug already exists")
        entity = Brand(
            name=payload.name,
            slug=slug,
            description=payload.description,
            website=payload.website,
            is_active=payload.is_active,
        )
        return self.repo.create(entity)

    def list(self, active_only: bool = False) -> list[Brand]:
        filters = [Brand.is_active.is_(True)] if active_only else None
        return self.repo.list(limit=500, filters=filters, order_by=Brand.name.asc())

    def get(self, brand_id: int) -> Brand:
        entity = self.repo.get_by_id(brand_id)
        if entity is None:
            raise NotFoundError("Brand not found")
        return entity

    def update(self, brand_id: int, payload: BrandUpdate) -> Brand:
        entity = self.get(brand_id)
        data = payload.model_dump(exclude_unset=True)
        if "name" in data and "slug" not in data:
            data["slug"] = slugify(data["name"])
        return self.repo.update(entity, data)

    def delete(self, brand_id: int) -> None:
        entity = self.get(brand_id)
        self.repo.delete(entity)


class ProductService:
    def __init__(self, db: Session) -> None:
        self.repo = ProductRepository(db)

    def create(self, payload: ProductCreate) -> Product:
        if self.repo.get_by_sku(payload.sku):
            raise ConflictError("SKU already exists")
        slug = payload.slug or slugify(payload.name)
        if self.repo.get_by_slug(slug):
            slug = f"{slug}-{payload.sku.lower()}"
        stock = (
            payload.stock_quantity
            if payload.stock_quantity is not None
            else payload.stock
        )
        image = payload.image_url or payload.image
        entity = Product(
            name=payload.name,
            slug=slug,
            sku=payload.sku.upper(),
            description=payload.description,
            price=payload.price,
            compare_at_price=payload.compare_at_price,
            stock=stock or 0,
            rating=payload.rating,
            category_id=payload.category_id,
            brand_id=payload.brand_id,
            image=image,
            is_active=payload.is_active,
            is_featured=payload.is_featured,
            weight_kg=payload.weight_kg,
        )
        return self.repo.create(entity)

    def get(self, product_id: int) -> Product:
        entity = self.repo.get_by_id(product_id)
        if entity is None:
            raise NotFoundError("Product not found")
        return entity

    def get_by_slug(self, slug: str) -> Product:
        entity = self.repo.get_by_slug(slug)
        if entity is None:
            raise NotFoundError("Product not found")
        return entity

    def update(self, product_id: int, payload: ProductUpdate) -> Product:
        entity = self.get(product_id)
        data = payload.model_dump(exclude_unset=True)
        if "stock_quantity" in data and "stock" not in data:
            data["stock"] = data.pop("stock_quantity")
        elif "stock_quantity" in data:
            data.pop("stock_quantity")
        if "image_url" in data and "image" not in data:
            data["image"] = data.pop("image_url")
        elif "image_url" in data:
            data.pop("image_url")
        if "sku" in data:
            data["sku"] = data["sku"].upper()
            other = self.repo.get_by_sku(data["sku"])
            if other and other.id != entity.id:
                raise ConflictError("SKU already exists")
        if "name" in data and "slug" not in data:
            data["slug"] = slugify(data["name"])
        return self.repo.update(entity, data)

    def delete(self, product_id: int) -> None:
        entity = self.get(product_id)
        self.repo.delete(entity)

    def list_products(
        self,
        *,
        q: Optional[str] = None,
        category_id: Optional[int] = None,
        brand_id: Optional[int] = None,
        featured: Optional[bool] = None,
        active_only: bool = True,
        page: int = 1,
        page_size: int = 20,
    ) -> ProductListResponse:
        page = max(1, page)
        page_size = min(max(1, page_size), 100)
        skip = (page - 1) * page_size
        items, total = self.repo.search(
            q=q,
            category_id=category_id,
            brand_id=brand_id,
            featured=featured,
            active_only=active_only,
            skip=skip,
            limit=page_size,
        )
        return ProductListResponse(
            items=[ProductListItem.model_validate(i) for i in items],
            total=total,
            page=page,
            page_size=page_size,
            pages=ceil(total / page_size) if total else 0,
        )
