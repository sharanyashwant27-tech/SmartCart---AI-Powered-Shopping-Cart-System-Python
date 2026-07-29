"""Product, category, and brand schemas."""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CategoryBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    description: Optional[str] = None
    parent_id: Optional[int] = None
    is_active: bool = True


class CategoryCreate(CategoryBase):
    slug: Optional[str] = None


class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=120)
    slug: Optional[str] = None
    description: Optional[str] = None
    parent_id: Optional[int] = None
    is_active: Optional[bool] = None


class CategoryResponse(CategoryBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    created_at: datetime


class BrandBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    description: Optional[str] = None
    website: Optional[str] = None
    is_active: bool = True


class BrandCreate(BrandBase):
    slug: Optional[str] = None


class BrandUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=120)
    slug: Optional[str] = None
    description: Optional[str] = None
    website: Optional[str] = None
    is_active: Optional[bool] = None


class BrandResponse(BrandBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    created_at: datetime


class ProductBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    sku: str = Field(..., min_length=2, max_length=64)
    description: Optional[str] = None
    price: Decimal = Field(..., gt=0)
    compare_at_price: Optional[Decimal] = Field(None, gt=0)
    stock: int = Field(0, ge=0, description="Available stock")
    stock_quantity: Optional[int] = Field(
        None, ge=0, description="Alias for stock (backward compatible)"
    )
    category_id: Optional[int] = None
    brand_id: Optional[int] = None
    image: Optional[str] = None
    image_url: Optional[str] = Field(None, description="Alias for image")
    rating: Decimal = Field(Decimal("0.00"), ge=0, le=5)
    is_active: bool = True
    is_featured: bool = False
    weight_kg: Optional[Decimal] = Field(None, ge=0)

    @field_validator("price", "compare_at_price", "rating", mode="before")
    @classmethod
    def coerce_decimal(cls, v):  # noqa: ANN001
        if v is None:
            return v
        return Decimal(str(v))


class ProductCreate(ProductBase):
    slug: Optional[str] = None


class ProductUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=200)
    slug: Optional[str] = None
    sku: Optional[str] = Field(None, min_length=2, max_length=64)
    description: Optional[str] = None
    price: Optional[Decimal] = Field(None, gt=0)
    compare_at_price: Optional[Decimal] = Field(None, gt=0)
    stock: Optional[int] = Field(None, ge=0)
    stock_quantity: Optional[int] = Field(None, ge=0)
    category_id: Optional[int] = None
    brand_id: Optional[int] = None
    image: Optional[str] = None
    image_url: Optional[str] = None
    rating: Optional[Decimal] = Field(None, ge=0, le=5)
    is_active: Optional[bool] = None
    is_featured: Optional[bool] = None
    weight_kg: Optional[Decimal] = Field(None, ge=0)


class ProductResponse(ProductBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    created_at: datetime
    updated_at: datetime
    category: Optional[CategoryResponse] = None
    brand: Optional[BrandResponse] = None


class ProductListResponse(BaseModel):
    items: list[ProductResponse]
    total: int
    page: int
    page_size: int
    pages: int
