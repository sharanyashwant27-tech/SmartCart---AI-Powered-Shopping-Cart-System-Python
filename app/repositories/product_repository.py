"""Product, category, and brand repositories."""

from typing import Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.models.category import Brand, Category
from app.models.product import Product
from app.repositories.base import BaseRepository


class CategoryRepository(BaseRepository[Category]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, Category)

    def get_by_slug(self, slug: str) -> Optional[Category]:
        return self.db.query(Category).filter(Category.slug == slug).first()

    def get_by_name(self, name: str) -> Optional[Category]:
        return self.db.query(Category).filter(Category.name == name).first()


class BrandRepository(BaseRepository[Brand]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, Brand)

    def get_by_slug(self, slug: str) -> Optional[Brand]:
        return self.db.query(Brand).filter(Brand.slug == slug).first()


class ProductRepository(BaseRepository[Product]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, Product)

    def get_by_id(self, entity_id: int) -> Optional[Product]:
        return (
            self.db.query(Product)
            .options(joinedload(Product.category), joinedload(Product.brand))
            .filter(Product.id == entity_id)
            .first()
        )

    def get_by_slug(self, slug: str) -> Optional[Product]:
        return (
            self.db.query(Product)
            .options(joinedload(Product.category), joinedload(Product.brand))
            .filter(Product.slug == slug)
            .first()
        )

    def get_by_sku(self, sku: str) -> Optional[Product]:
        return self.db.query(Product).filter(Product.sku == sku).first()

    def search(
        self,
        *,
        q: Optional[str] = None,
        category_id: Optional[int] = None,
        brand_id: Optional[int] = None,
        featured: Optional[bool] = None,
        active_only: bool = True,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[Product], int]:
        filters = []
        if active_only:
            filters.append(Product.is_active.is_(True))
        if q:
            like = f"%{q}%"
            filters.append(
                or_(
                    Product.name.ilike(like),
                    Product.description.ilike(like),
                    Product.sku.ilike(like),
                )
            )
        if category_id is not None:
            filters.append(Product.category_id == category_id)
        if brand_id is not None:
            filters.append(Product.brand_id == brand_id)
        if featured is not None:
            filters.append(Product.is_featured.is_(featured))

        # Count without joinedloads (much cheaper on SQLite/Postgres)
        count_q = self.db.query(Product)
        for f in filters:
            count_q = count_q.filter(f)
        total = count_q.count()

        query = self.db.query(Product).options(joinedload(Product.category))
        for f in filters:
            query = query.filter(f)
        items = query.order_by(Product.created_at.desc()).offset(skip).limit(limit).all()
        return items, total

    def adjust_stock(self, product: Product, delta: int) -> Product:
        product.stock_quantity = max(0, product.stock_quantity + delta)
        self.db.commit()
        self.db.refresh(product)
        return product
