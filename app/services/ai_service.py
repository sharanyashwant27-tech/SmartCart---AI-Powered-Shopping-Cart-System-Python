"""Optional OpenAI-powered shopping assistant and recommendations."""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.config import get_settings
from app.utils.exceptions import AppException
from app.repositories.product_repository import ProductRepository
from app.schemas.product import ProductResponse

logger = logging.getLogger(__name__)
settings = get_settings()


class AIService:
    """AI helpers. Falls back to heuristic recommendations when OpenAI is unset."""

    def __init__(self, db: Session) -> None:
        self.products = ProductRepository(db)

    @property
    def enabled(self) -> bool:
        return settings.openai_enabled

    def status(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "provider": "openai" if self.enabled else "heuristic",
            "model": settings.openai_model if self.enabled else None,
        }

    def recommend(
        self,
        *,
        query: Optional[str] = None,
        product_id: Optional[int] = None,
        limit: int = 4,
    ) -> dict[str, Any]:
        catalog, _ = self.products.search(active_only=True, skip=0, limit=50)
        if not catalog:
            return {
                "provider": self.status()["provider"],
                "message": "No products available",
                "recommendations": [],
            }

        seed = None
        if product_id:
            seed = self.products.get_by_id(product_id)

        if self.enabled:
            try:
                return self._openai_recommend(catalog, query=query, seed=seed, limit=limit)
            except Exception as exc:  # noqa: BLE001
                logger.warning("OpenAI recommendation failed, using heuristic: %s", exc)

        return self._heuristic_recommend(catalog, query=query, seed=seed, limit=limit)

    def chat(self, message: str) -> dict[str, Any]:
        if not message.strip():
            raise AppException("Message is required", code="validation_error")

        catalog, _ = self.products.search(active_only=True, skip=0, limit=30)
        catalog_blob = "\n".join(
            f"- {p.name} (${p.price}) [{p.sku}] stock={p.stock_quantity}"
            for p in catalog
        )

        if self.enabled:
            try:
                from openai import OpenAI

                client = OpenAI(api_key=settings.openai_api_key)
                completion = client.chat.completions.create(
                    model=settings.openai_model,
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "You are SmartCart's shopping assistant. Be concise and helpful. "
                                "Only recommend products from the provided catalog. "
                                f"Catalog:\n{catalog_blob}"
                            ),
                        },
                        {"role": "user", "content": message},
                    ],
                    temperature=0.4,
                    max_tokens=400,
                )
                reply = completion.choices[0].message.content or ""
                return {
                    "provider": "openai",
                    "model": settings.openai_model,
                    "reply": reply,
                }
            except Exception as exc:  # noqa: BLE001
                logger.warning("OpenAI chat failed: %s", exc)

        # Heuristic fallback
        q = message.lower()
        matches = [
            p
            for p in catalog
            if any(tok in (p.name or "").lower() or tok in (p.description or "").lower() for tok in q.split() if len(tok) > 2)
        ][:3]
        if matches:
            lines = ", ".join(f"{p.name} (${p.price})" for p in matches)
            reply = f"Based on your message, you might like: {lines}. Open the storefront to add them to your cart."
        else:
            featured = [p for p in catalog if p.is_featured][:3] or catalog[:3]
            lines = ", ".join(f"{p.name} (${p.price})" for p in featured)
            reply = (
                "AI is offline (set OPENAI_API_KEY to enable). "
                f"Popular picks right now: {lines}."
            )
        return {"provider": "heuristic", "model": None, "reply": reply}

    def _openai_recommend(
        self,
        catalog: list,
        *,
        query: Optional[str],
        seed: Any,
        limit: int,
    ) -> dict[str, Any]:
        from openai import OpenAI

        client = OpenAI(api_key=settings.openai_api_key)
        catalog_json = [
            {
                "id": p.id,
                "name": p.name,
                "sku": p.sku,
                "price": float(p.price),
                "category_id": p.category_id,
                "brand_id": p.brand_id,
                "description": (p.description or "")[:180],
            }
            for p in catalog
        ]
        prompt = {
            "query": query,
            "seed_product_id": seed.id if seed else None,
            "limit": limit,
            "catalog": catalog_json,
        }
        completion = client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Return JSON only: {\"ids\":[int],\"reason\":str}. "
                        "Pick up to `limit` product ids from catalog that best match the query/seed."
                    ),
                },
                {"role": "user", "content": json.dumps(prompt)},
            ],
            temperature=0.2,
            max_tokens=300,
            response_format={"type": "json_object"},
        )
        raw = completion.choices[0].message.content or "{}"
        parsed = json.loads(raw)
        ids = [int(i) for i in parsed.get("ids", [])][:limit]
        by_id = {p.id: p for p in catalog}
        recs = [
            ProductResponse.model_validate(by_id[i]).model_dump()
            for i in ids
            if i in by_id
        ]
        return {
            "provider": "openai",
            "model": settings.openai_model,
            "message": parsed.get("reason", "AI recommendations"),
            "recommendations": recs,
        }

    def _heuristic_recommend(
        self,
        catalog: list,
        *,
        query: Optional[str],
        seed: Any,
        limit: int,
    ) -> dict[str, Any]:
        scored: list[tuple[float, Any]] = []
        q_tokens = (query or "").lower().split() if query else []
        for p in catalog:
            if seed and p.id == seed.id:
                continue
            score = 0.0
            if seed and p.category_id and p.category_id == seed.category_id:
                score += 3
            if seed and p.brand_id and p.brand_id == seed.brand_id:
                score += 2
            if p.is_featured:
                score += 1.5
            text = f"{p.name} {p.description or ''}".lower()
            score += sum(1 for t in q_tokens if t and t in text)
            scored.append((score, p))
        scored.sort(key=lambda x: x[0], reverse=True)
        top = [p for s, p in scored if s > 0][:limit] or [p for _, p in scored][:limit]
        return {
            "provider": "heuristic",
            "model": None,
            "message": "Rule-based recommendations (set OPENAI_API_KEY for AI)",
            "recommendations": [ProductResponse.model_validate(p).model_dump() for p in top],
        }

    def similar_products(self, product_id: int, limit: int = 4) -> dict[str, Any]:
        product = self.products.get_by_id(product_id)
        if product is None:
            from app.utils.exceptions import NotFoundError

            raise NotFoundError("Product not found")
        return self.recommend(product_id=product_id, limit=limit)

    def predict_price(self, product_id: int) -> dict[str, Any]:
        product = self.products.get_by_id(product_id)
        if product is None:
            from app.utils.exceptions import NotFoundError

            raise NotFoundError("Product not found")

        peers, _ = self.products.search(
            category_id=product.category_id, active_only=True, skip=0, limit=40
        )
        peer_prices = [float(p.price) for p in peers if p.id != product.id]
        current = float(product.price)
        if peer_prices:
            avg = sum(peer_prices) / len(peer_prices)
            low = min(peer_prices)
            high = max(peer_prices)
        else:
            avg = current
            low = current * 0.9
            high = current * 1.1

        # Simple forecast: nudge toward category average with mild demand signal from stock
        stock_factor = 1.02 if product.stock_quantity < 10 else 0.98 if product.stock_quantity > 50 else 1.0
        predicted = round(((current * 0.6) + (avg * 0.4)) * stock_factor, 2)

        result = {
            "provider": "heuristic",
            "product_id": product_id,
            "current_price": current,
            "predicted_price": predicted,
            "category_avg": round(avg, 2),
            "category_low": round(low, 2),
            "category_high": round(high, 2),
            "confidence": 0.55 if peer_prices else 0.35,
            "insight": (
                "Price predicted from category peers and stock pressure."
                if not self.enabled
                else "Price predicted with AI-assisted commentary."
            ),
        }

        if self.enabled:
            try:
                from openai import OpenAI

                client = OpenAI(api_key=settings.openai_api_key)
                completion = client.chat.completions.create(
                    model=settings.openai_model,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a retail pricing analyst. Reply in 2 short sentences.",
                        },
                        {
                            "role": "user",
                            "content": (
                                f"Product {product.name} at ${current}. Category avg ${avg:.2f}, "
                                f"range ${low:.2f}-${high:.2f}, stock {product.stock_quantity}. "
                                f"Suggested price ${predicted}."
                            ),
                        },
                    ],
                    max_tokens=120,
                    temperature=0.3,
                )
                result["provider"] = "openai"
                result["insight"] = completion.choices[0].message.content or result["insight"]
            except Exception as exc:  # noqa: BLE001
                logger.warning("Price prediction AI failed: %s", exc)
        return result

    def summarize_reviews(self, product_id: int, reviews: list[dict]) -> dict[str, Any]:
        if not reviews:
            return {
                "provider": "heuristic",
                "product_id": product_id,
                "summary": "No reviews yet.",
                "pros": [],
                "cons": [],
                "average_rating": 0,
            }
        avg = sum(int(r.get("rating", 0)) for r in reviews) / len(reviews)
        texts = [f"{r.get('rating')}*: {(r.get('title') or '')} {(r.get('body') or '')}" for r in reviews]

        if self.enabled:
            try:
                from openai import OpenAI

                client = OpenAI(api_key=settings.openai_api_key)
                completion = client.chat.completions.create(
                    model=settings.openai_model,
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                'Return JSON: {"summary":str,"pros":[str],"cons":[str]}. '
                                "Be concise."
                            ),
                        },
                        {"role": "user", "content": "\n".join(texts[:30])},
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.2,
                    max_tokens=250,
                )
                parsed = json.loads(completion.choices[0].message.content or "{}")
                return {
                    "provider": "openai",
                    "product_id": product_id,
                    "summary": parsed.get("summary", ""),
                    "pros": parsed.get("pros", []),
                    "cons": parsed.get("cons", []),
                    "average_rating": round(avg, 2),
                }
            except Exception as exc:  # noqa: BLE001
                logger.warning("Review summary AI failed: %s", exc)

        positives = [r for r in reviews if int(r.get("rating", 0)) >= 4]
        negatives = [r for r in reviews if int(r.get("rating", 0)) <= 2]
        return {
            "provider": "heuristic",
            "product_id": product_id,
            "summary": (
                f"{len(reviews)} reviews with an average of {avg:.1f}/5. "
                f"{len(positives)} positive and {len(negatives)} critical."
            ),
            "pros": [((p.get("title") or p.get("body") or "Liked it")[:80]) for p in positives[:3]],
            "cons": [((n.get("title") or n.get("body") or "Needs improvement")[:80]) for n in negatives[:3]],
            "average_rating": round(avg, 2),
        }
