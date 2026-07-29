"""Optional AI assistant and product recommendation endpoints."""

from typing import Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from app.utils.dependencies import DbSession, OptionalUser
from app.services.ai_service import AIService
from app.services.review_service import ReviewService

router = APIRouter(prefix="/ai", tags=["AI"])


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)


@router.get("/status")
async def ai_status(db: DbSession) -> dict:
    """Return whether OpenAI is configured."""
    return AIService(db).status()


@router.get("/recommendations")
async def recommendations(
    db: DbSession,
    _: OptionalUser = None,
    query: Optional[str] = Query(None, description="Free-text shopping intent"),
    product_id: Optional[int] = Query(None, description="Similar-to product id"),
    limit: int = Query(4, ge=1, le=10),
) -> dict:
    """Product recommendations via OpenAI (or heuristic fallback)."""
    return AIService(db).recommend(query=query, product_id=product_id, limit=limit)


@router.get("/similar/{product_id}")
async def similar_products(
    product_id: int,
    db: DbSession,
    limit: int = Query(4, ge=1, le=10),
) -> dict:
    """Similar products for a given product."""
    return AIService(db).similar_products(product_id, limit=limit)


@router.get("/price-prediction/{product_id}")
async def price_prediction(product_id: int, db: DbSession) -> dict:
    """Predict a suggested price from peers / optional OpenAI insight."""
    return AIService(db).predict_price(product_id)


@router.get("/reviews/{product_id}/summarize")
async def summarize_reviews(product_id: int, db: DbSession) -> dict:
    """Summarize product reviews (OpenAI optional)."""
    reviews = ReviewService(db).list_for_product(product_id)
    payload = [r.model_dump() for r in reviews]
    return AIService(db).summarize_reviews(product_id, payload)


@router.post("/chat")
async def chat(payload: ChatRequest, db: DbSession, _: OptionalUser = None) -> dict:
    """Shopping assistant chat (OpenAI optional)."""
    return AIService(db).chat(payload.message)
