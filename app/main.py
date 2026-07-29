"""FastAPI application factory and entrypoint."""

from contextlib import asynccontextmanager
from decimal import Decimal

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.config import get_settings
from app.database import SessionLocal, init_db
from app.utils.enums import CouponType
from app.utils.exceptions import register_exception_handlers
from app.utils.logging import get_logger, setup_logging
from app.utils.rate_limit import limiter
from app.api import api_router
from app.schemas.cart import CouponCreate
from app.schemas.product import BrandCreate, CategoryCreate, ProductCreate
from app.services.auth_service import UserService
from app.services.cart_service import CouponService
from app.services.product_service import BrandService, CategoryService, ProductService

settings = get_settings()
logger = get_logger(__name__)
BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = ROOT_DIR / "static"
UPLOADS_DIR = ROOT_DIR / "uploads"
APP_STATIC_DIR = BASE_DIR / "static"


def seed_data() -> None:
    """Seed admin user, categories, brands, sample products per category, and coupons."""
    db = SessionLocal()
    try:
        UserService(db).ensure_admin(
            settings.admin_email, settings.admin_password, settings.admin_full_name
        )

        # Categories
        existing_cats = {
            c.name.lower(): c for c in CategoryService(db).list(active_only=False)
        }
        for name, desc in [
            ("Electronics", "Gadgets and devices"),
            ("Mobile", "Smartphones and accessories"),
            ("Computers", "Laptops, PCs, and peripherals"),
            ("Fashion", "Apparel and accessories"),
            ("Home & Living", "Home essentials"),
            ("Beauty", "Personal care and beauty"),
            ("Sports", "Fitness and outdoor gear"),
        ]:
            if name.lower() not in existing_cats:
                cat = CategoryService(db).create(
                    CategoryCreate(name=name, description=desc)
                )
                existing_cats[name.lower()] = cat
                logger.info("Added category: %s", name)

        cats = {c.name.lower(): c for c in CategoryService(db).list(active_only=False)}

        # Brands
        existing_brands = {
            b.name.lower(): b for b in BrandService(db).list(active_only=False)
        }
        for name, desc in [
            ("NovaTech", "Smart devices"),
            ("UrbanWear", "Modern fashion"),
            ("HomeNest", "Home essentials"),
            ("GlowLab", "Beauty and personal care"),
            ("PulseFit", "Sports and fitness"),
        ]:
            if name.lower() not in existing_brands:
                brand = BrandService(db).create(
                    BrandCreate(name=name, description=desc)
                )
                existing_brands[name.lower()] = brand

        brands = {b.name.lower(): b for b in BrandService(db).list(active_only=False)}
        product_svc = ProductService(db)

        def cat(name: str):
            return cats[name.lower()].id

        def brand(name: str):
            b = brands.get(name.lower())
            return b.id if b else None

        samples = [
            # Electronics
            ProductCreate(
                name="Wireless Noise-Cancel Headphones",
                sku="NT-HP-001",
                description="Over-ear Bluetooth headphones with 30h battery life.",
                price=Decimal("129.99"),
                compare_at_price=Decimal("159.99"),
                stock_quantity=40,
                category_id=cat("Electronics"),
                brand_id=brand("NovaTech"),
                image_url="https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=600",
                is_featured=True,
            ),
            ProductCreate(
                name="Portable Bluetooth Speaker",
                sku="NT-SP-003",
                description="IPX7 waterproof speaker with rich bass.",
                price=Decimal("49.99"),
                stock_quantity=60,
                category_id=cat("Electronics"),
                brand_id=brand("NovaTech"),
                image_url="https://images.unsplash.com/photo-1608043152269-423dbba4e7e1?w=600",
                is_featured=True,
            ),
            ProductCreate(
                name="4K Action Camera",
                sku="NT-AC-014",
                description="Waterproof action cam with image stabilization.",
                price=Decimal("179.00"),
                stock_quantity=28,
                category_id=cat("Electronics"),
                brand_id=brand("NovaTech"),
                image_url="https://images.unsplash.com/photo-1526170375885-4d8ecf77b99f?w=600",
            ),
            # Mobile
            ProductCreate(
                name="Aura Phone 15",
                sku="MB-PH-101",
                description="6.7-inch OLED smartphone with dual camera and 5G.",
                price=Decimal("799.00"),
                compare_at_price=Decimal("899.00"),
                stock_quantity=35,
                category_id=cat("Mobile"),
                brand_id=brand("NovaTech"),
                image_url="https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?w=600",
                is_featured=True,
            ),
            ProductCreate(
                name="MagSafe Wireless Charger",
                sku="MB-CH-102",
                description="15W magnetic fast charger for compatible phones.",
                price=Decimal("39.99"),
                stock_quantity=70,
                category_id=cat("Mobile"),
                brand_id=brand("NovaTech"),
                image_url="https://images.unsplash.com/photo-1580910051074-3eb694886505?w=600",
            ),
            ProductCreate(
                name="ClearShield Phone Case",
                sku="MB-CS-103",
                description="Slim protective case with raised camera rim.",
                price=Decimal("24.50"),
                stock_quantity=120,
                category_id=cat("Mobile"),
                brand_id=brand("NovaTech"),
                image_url="https://images.unsplash.com/photo-1601784551446-20c9e07cdbdb?w=600",
            ),
            # Computers
            ProductCreate(
                name="NovaBook Pro 14",
                sku="PC-LB-201",
                description="14-inch laptop, 16GB RAM, 512GB SSD — work and create.",
                price=Decimal("1199.00"),
                stock_quantity=18,
                category_id=cat("Computers"),
                brand_id=brand("NovaTech"),
                image_url="https://images.unsplash.com/photo-1496181133206-80ce9b88a853?w=600",
                is_featured=True,
            ),
            ProductCreate(
                name="Mechanical RGB Keyboard",
                sku="PC-KB-202",
                description="Hot-swappable switches with per-key RGB lighting.",
                price=Decimal("89.00"),
                stock_quantity=45,
                category_id=cat("Computers"),
                brand_id=brand("NovaTech"),
                image_url="https://images.unsplash.com/photo-1511467687858-23d96c32e4ae?w=600",
            ),
            ProductCreate(
                name="UltraWide 34\" Monitor",
                sku="PC-MN-203",
                description="34-inch curved ultrawide display for multitasking.",
                price=Decimal("449.00"),
                stock_quantity=22,
                category_id=cat("Computers"),
                brand_id=brand("NovaTech"),
                image_url="https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?w=600",
            ),
            # Fashion
            ProductCreate(
                name="Classic Denim Jacket",
                sku="UW-DJ-010",
                description="Durable mid-wash denim jacket.",
                price=Decimal("69.00"),
                stock_quantity=30,
                category_id=cat("Fashion"),
                brand_id=brand("UrbanWear"),
                image_url="https://images.unsplash.com/photo-1551028719-00167b16eac5?w=600",
                is_featured=True,
            ),
            ProductCreate(
                name="Minimalist Leather Backpack",
                sku="UW-BP-011",
                description="Laptop-friendly everyday backpack.",
                price=Decimal("119.00"),
                stock_quantity=25,
                category_id=cat("Fashion"),
                brand_id=brand("UrbanWear"),
                image_url="https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=600",
            ),
            ProductCreate(
                name="Everyday Cotton Tee",
                sku="UW-TS-012",
                description="Soft mid-weight cotton tee in classic fit.",
                price=Decimal("28.00"),
                stock_quantity=90,
                category_id=cat("Fashion"),
                brand_id=brand("UrbanWear"),
                image_url="https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=600",
            ),
            # Home & Living
            ProductCreate(
                name="Ceramic Pour-Over Mug Set",
                sku="HL-MG-020",
                description="Set of 2 artisan ceramic mugs.",
                price=Decimal("34.99"),
                stock_quantity=80,
                category_id=cat("Home & Living"),
                brand_id=brand("HomeNest"),
                image_url="https://images.unsplash.com/photo-1514228742587-6b1558fcca3d?w=600",
            ),
            ProductCreate(
                name="Linen Throw Pillow Pair",
                sku="HL-PL-021",
                description="Soft linen pillows for sofa or bed styling.",
                price=Decimal("42.00"),
                stock_quantity=55,
                category_id=cat("Home & Living"),
                brand_id=brand("HomeNest"),
                image_url="https://images.unsplash.com/photo-1584100936595-c0654b55a2e2?w=600",
            ),
            ProductCreate(
                name="Aroma Diffuser Lamp",
                sku="HL-DF-022",
                description="Ultrasonic essential oil diffuser with warm light.",
                price=Decimal("36.50"),
                stock_quantity=48,
                category_id=cat("Home & Living"),
                brand_id=brand("HomeNest"),
                image_url="https://images.unsplash.com/photo-1608571423902-eed4a5ad8108?w=600",
                is_featured=True,
            ),
            # Beauty
            ProductCreate(
                name="Vitamin C Bright Serum",
                sku="GL-SR-301",
                description="Daily brightening serum for even skin tone.",
                price=Decimal("32.00"),
                stock_quantity=65,
                category_id=cat("Beauty"),
                brand_id=brand("GlowLab"),
                image_url="https://images.unsplash.com/photo-1620916568170-2577e8126b61?w=600",
            ),
            ProductCreate(
                name="Hydrating Face Mist",
                sku="GL-MS-302",
                description="Refreshing facial mist with aloe and rose water.",
                price=Decimal("18.99"),
                stock_quantity=100,
                category_id=cat("Beauty"),
                brand_id=brand("GlowLab"),
                image_url="https://images.unsplash.com/photo-1571875257727-256c39da42af?w=600",
                is_featured=True,
            ),
            ProductCreate(
                name="Soft Bristle Hair Brush",
                sku="GL-BR-303",
                description="Detangling brush gentle on wet or dry hair.",
                price=Decimal("14.50"),
                stock_quantity=85,
                category_id=cat("Beauty"),
                brand_id=brand("GlowLab"),
                image_url="https://images.unsplash.com/photo-1522338242992-e1a54906a8da?w=600",
            ),
            # Sports
            ProductCreate(
                name="Smart Fitness Watch",
                sku="NT-SW-002",
                description="Track workouts, heart rate, and sleep.",
                price=Decimal("89.50"),
                stock_quantity=55,
                category_id=cat("Sports"),
                brand_id=brand("PulseFit"),
                image_url="https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=600",
                is_featured=True,
            ),
            ProductCreate(
                name="Yoga Mat Pro",
                sku="PF-YM-400",
                description="Non-slip 6mm yoga mat with carrying strap.",
                price=Decimal("35.00"),
                stock_quantity=60,
                category_id=cat("Sports"),
                brand_id=brand("PulseFit"),
                image_url="https://images.unsplash.com/photo-1601925260368-ae2f83cf8b7f?w=600",
            ),
            ProductCreate(
                name="Performance Running Shoes",
                sku="PF-RN-401",
                description="Lightweight cushioned runners for road training.",
                price=Decimal("110.00"),
                stock_quantity=40,
                category_id=cat("Sports"),
                brand_id=brand("PulseFit"),
                image_url="https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=600",
                is_featured=True,
            ),
            ProductCreate(
                name="Resistance Band Set",
                sku="PF-RB-402",
                description="5-level resistance bands for home strength training.",
                price=Decimal("22.00"),
                stock_quantity=75,
                category_id=cat("Sports"),
                brand_id=brand("PulseFit"),
                image_url="https://images.unsplash.com/photo-1598289431512-b97b0917affc?w=600",
            ),
        ]

        added = 0
        for payload in samples:
            if product_svc.repo.get_by_sku(payload.sku):
                continue
            product_svc.create(payload)
            added += 1
        if added:
            logger.info("Seeded %s sample products across categories", added)

        # Coupons
        from app.models.coupon import Coupon

        for code, create_kwargs in [
            (
                "WELCOME10",
                dict(
                    code="WELCOME10",
                    description="10% off your first order",
                    coupon_type=CouponType.PERCENTAGE,
                    value=Decimal("10"),
                    min_order_amount=Decimal("25"),
                    max_discount=Decimal("50"),
                ),
            ),
            (
                "SAVE5",
                dict(
                    code="SAVE5",
                    description="$5 off orders over $40",
                    coupon_type=CouponType.FIXED,
                    value=Decimal("5"),
                    min_order_amount=Decimal("40"),
                ),
            ),
        ]:
            exists = db.query(Coupon).filter(Coupon.code == code).first()
            if not exists:
                CouponService(db).create(CouponCreate(**create_kwargs))
                logger.info("Seeded coupon %s", code)
    finally:
        db.close()


@asynccontextmanager
async def lifespan(_: FastAPI):
    setup_logging("DEBUG" if settings.debug else "INFO")
    logger.info("Starting %s on port %s", settings.app_name, settings.api_port)
    init_db()
    seed_data()
    yield
    logger.info("Shutting down %s", settings.app_name)


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        description=(
            "Production-ready AI-powered Shopping Cart System with JWT auth, "
            "cart, checkout, Stripe sandbox payments, admin analytics, and more."
        ),
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_exception_handlers(app)
    app.include_router(api_router)

    STATIC_DIR.mkdir(parents=True, exist_ok=True)
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

    def _storefront_html() -> str:
        """Build a self-contained storefront page (CSS/JS inlined)."""
        html = (TEMPLATES_DIR / "index.html").read_text(encoding="utf-8")
        css_path = STATIC_DIR / "app.css"
        js_path = STATIC_DIR / "app.js"
        if css_path.exists():
            css = css_path.read_text(encoding="utf-8")
            html = html.replace(
                '<link rel="stylesheet" href="/static/app.css" />',
                f"<style>\n{css}\n</style>",
            )
        if js_path.exists():
            js = js_path.read_text(encoding="utf-8")
            html = html.replace(
                '<script src="/static/app.js"></script>',
                f"<script>\n{js}\n</script>",
            )
        return html.replace("{{PORT}}", str(settings.api_port))

    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    async def root():
        """Serve the SmartCart storefront on the API host (port 8904)."""
        return HTMLResponse(content=_storefront_html())

    @app.get("/app", response_class=HTMLResponse, include_in_schema=False)
    async def storefront_app():
        """Alias for the storefront UI."""
        return HTMLResponse(content=_storefront_html())

    @app.get("/health", tags=["Health"])
    async def health():
        return {
            "status": "ok",
            "app": settings.app_name,
            "env": settings.app_env,
            "port": settings.api_port,
        }

    # Mounts after routes so "/" is never shadowed
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
    app.mount("/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")
    if APP_STATIC_DIR.exists():
        app.mount("/app-static", StaticFiles(directory=str(APP_STATIC_DIR)), name="app_static")

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.api_port,
        reload=bool(settings.debug),
    )
