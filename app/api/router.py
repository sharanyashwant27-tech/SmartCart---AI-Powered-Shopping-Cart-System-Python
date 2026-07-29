"""API router aggregation — wires all domain routers under /api/v1."""

from fastapi import APIRouter

from app.admin.router import router as admin_router
from app.ai.router import router as ai_router
from app.analytics.router import router as analytics_router
from app.auth.router import router as auth_router
from app.cart.router import coupons_router, router as cart_router
from app.checkout.router import router as checkout_router
from app.loyalty.router import router as loyalty_router
from app.orders.router import router as orders_router
from app.payment.router import router as payment_router
from app.products.catalog_router import brands_router, categories_router
from app.products.reviews import images_router, reviews_router
from app.products.router import router as products_router
from app.users.addresses import addresses_router
from app.users.router import router as users_router
from app.wishlist.router import router as wishlist_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(addresses_router)
api_router.include_router(loyalty_router)
api_router.include_router(categories_router)
api_router.include_router(brands_router)
api_router.include_router(products_router)
api_router.include_router(reviews_router)
api_router.include_router(images_router)
api_router.include_router(cart_router)
api_router.include_router(wishlist_router)
api_router.include_router(coupons_router)
api_router.include_router(checkout_router)
api_router.include_router(orders_router)
api_router.include_router(payment_router)
api_router.include_router(admin_router)
api_router.include_router(analytics_router)
api_router.include_router(ai_router)
