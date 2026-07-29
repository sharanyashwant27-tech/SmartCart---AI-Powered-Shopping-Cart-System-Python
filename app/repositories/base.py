"""Base repository with generic CRUD helpers."""

from __future__ import annotations

from typing import Any, Generic, Optional, Type, TypeVar

from sqlalchemy.orm import Session

from app.database import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """Generic repository implementing common persistence operations."""

    def __init__(self, db: Session, model: Type[ModelT]) -> None:
        self.db = db
        self.model = model

    def get_by_id(self, entity_id: int) -> Optional[ModelT]:
        return self.db.get(self.model, entity_id)

    def list(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[list[Any]] = None,
        order_by: Optional[Any] = None,
    ) -> list[ModelT]:
        query = self.db.query(self.model)
        if filters:
            for f in filters:
                query = query.filter(f)
        if order_by is not None:
            query = query.order_by(order_by)
        return query.offset(skip).limit(limit).all()

    def count(self, filters: Optional[list[Any]] = None) -> int:
        query = self.db.query(self.model)
        if filters:
            for f in filters:
                query = query.filter(f)
        return query.count()

    def create(self, entity: ModelT) -> ModelT:
        self.db.add(entity)
        self.db.commit()
        self.db.refresh(entity)
        return entity

    def update(self, entity: ModelT, data: dict[str, Any]) -> ModelT:
        for key, value in data.items():
            if value is not None and hasattr(entity, key):
                setattr(entity, key, value)
        self.db.commit()
        self.db.refresh(entity)
        return entity

    def delete(self, entity: ModelT) -> None:
        self.db.delete(entity)
        self.db.commit()

    def save(self, entity: ModelT) -> ModelT:
        self.db.add(entity)
        self.db.commit()
        self.db.refresh(entity)
        return entity
