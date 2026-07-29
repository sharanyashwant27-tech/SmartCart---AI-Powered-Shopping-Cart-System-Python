# SmartCart — AI-Powered Shopping Cart System

Production-ready shopping cart built with **Python** and **FastAPI**. The web storefront and API both run on **port 8904**.

**Repository:** [sharanyashwant27-tech/SmartCart---AI-Powered-Shopping-Cart-System-Python](https://github.com/sharanyashwant27-tech/SmartCart---AI-Powered-Shopping-Cart-System-Python)

| Surface | URL |
|---------|-----|
| Web storefront | http://localhost:8904 |
| API / Swagger | http://localhost:8904/docs |
| Health | http://localhost:8904/health |
| Optional Streamlit UI | http://localhost:8501 |

## Tech stack

| Category | Technology |
| -------- | ---------- |
| Language | Python 3.12+ |
| Backend | FastAPI |
| Storefront | FastAPI-served HTML/CSS/JS SPA |
| Optional UI | Streamlit |
| Database | SQLite (dev/Docker default), PostgreSQL (production) |
| ORM | SQLAlchemy |
| Authentication | JWT |
| Payments | Card, UPI, QR Code, Net Banking, Wallet, COD (+ Stripe sandbox) |
| AI | OpenAI API (optional) |
| Testing | Pytest |
| Containers | Docker + Docker Compose |
| Deployment | Docker, Render, Railway |

## Features

| Module | Capabilities |
|--------|----------------|
| Auth | Register / login (guest + admin), JWT with session refresh |
| Shop | Categories, search, product details, images |
| Cart | Add / remove, **+/- quantity**, editable qty, coupons, live totals |
| Checkout | Shipping + billing, remove items before pay, payment method selection |
| Payments | Card, UPI, **QR Code**, Internet Banking, Wallet, Cash on Delivery (+ Stripe sandbox) |
| Bills | PDF invoice with verification QR; auto-download after payment |
| Loyalty | Points for guests (earn on paid orders, redeem at checkout) |
| i18n | English / Hindi storefront language toggle |
| Admin | Dashboard KPIs, manage products & categories, orders |
| Analytics | Revenue, orders, inventory, coupons |
| Performance | Cached static assets, Gzip, lean product/cart APIs, SPA cache |
| Security | JWT, RBAC, CORS, rate limiting |

## Demo credentials

| Role | Email | Password |
|------|-------|----------|
| Admin | `admin@smartcart.com` | `Admin@12345` |

Coupons: `WELCOME10` (10% off), `SAVE5` ($5 off)  
Loyalty: +50 points on signup · 1 pt / $1 paid · 100 pts = $1 off

---

## Docker (recommended)

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (or Docker Engine + Compose v2)

### Build & run (storefront + API on :8904)

```bash
git clone https://github.com/sharanyashwant27-tech/SmartCart---AI-Powered-Shopping-Cart-System-Python.git
cd SmartCart---AI-Powered-Shopping-Cart-System-Python

docker compose up --build
```

Open **http://localhost:8904**

| Service | Image / container | Port |
|---------|-------------------|------|
| API + storefront | `smartcart-api:latest` / `smartcart-api` | **8904** |

Stop:

```bash
docker compose down
```

### Useful Docker commands

```bash
# Rebuild image only (includes README.md)
docker build -t smartcart-api:latest .

# Run API container without Compose
docker run --rm -p 8904:8904 --name smartcart-api smartcart-api:latest

# View logs
docker compose logs -f api

# Health check
curl http://localhost:8904/health

# Confirm README.md is inside the image / container
docker run --rm smartcart-api:latest head -n 8 /app/README.md
# or, with Compose running:
docker compose exec api head -n 8 /app/README.md
```

### Optional profiles

**Streamlit UI** (port 8501):

```bash
docker compose --profile streamlit up --build
```

**PostgreSQL** backend:

```bash
docker compose --profile postgres up --build
```

API then uses `postgresql+psycopg2://smartcart:smartcart@db:5432/smartcart`.

### Docker image contents

The `Dockerfile` builds a Python 3.12 slim image that:

- Installs dependencies from `requirements.txt`
- Copies the full application (`.dockerignore` excludes docs noise but **keeps `README.md`**)
- Explicitly copies and verifies **`/app/README.md`** at build time (`test -f /app/README.md`)
- Ships the FastAPI app and static storefront assets (`/static`)
- Exposes **8904** (API/UI) and **8501** (optional Streamlit)
- Includes a healthcheck on `/health`
- Defaults to: `uvicorn app.main:app --host 0.0.0.0 --port 8904`

Persistent volumes (Compose): `smartcart_data` (SQLite), `smartcart_uploads`, `smartcart_logs`.

---

## Local quick start (without Docker)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1   # Windows
# source .venv/bin/activate    # macOS/Linux

pip install -r requirements.txt
copy .env.example .env         # or: cp .env.example .env

uvicorn app.main:app --host 0.0.0.0 --port 8904 --reload
```

Optional Streamlit:

```powershell
$env:SMARTCART_API_URL="http://127.0.0.1:8904/api/v1"
streamlit run frontend/Home.py --server.port 8501
```

## Architecture

```
app/                 # FastAPI domains (auth, cart, checkout, orders, loyalty, admin, …)
frontend/            # Optional Streamlit UI
static/              # Storefront CSS/JS/i18n served at /
tests/
Dockerfile
docker-compose.yml
docs/
README.md            # Also baked into the Docker image at /app/README.md
```

## API documentation

Interactive OpenAPI docs: http://localhost:8904/docs

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/auth/register` | Create guest account |
| POST | `/api/v1/auth/login` | Obtain JWT |
| GET | `/api/v1/products` | List / search products |
| POST | `/api/v1/cart/items` | Add to cart |
| PATCH | `/api/v1/cart/items/{id}` | Update cart item quantity |
| DELETE | `/api/v1/cart/items/{id}` | Remove cart item |
| POST | `/api/v1/checkout` | Create order (`payment_method`: card/upi/qr/netbanking/wallet/cod) |
| POST | `/api/v1/payments/orders/{id}/confirm` | Confirm payment |
| GET | `/api/v1/orders/{id}/invoice` | Download PDF bill |
| GET | `/api/v1/loyalty/me` | Loyalty balance (guests) |
| GET | `/api/v1/admin/orders/{id}/invoice` | Admin bill download |
| GET | `/api/v1/analytics/dashboard` | Admin dashboard KPIs |

Protected routes require: `Authorization: Bearer <access_token>`.

## Environment variables

Copy `.env.example` → `.env`. Important keys:

| Variable | Purpose |
|----------|---------|
| `API_PORT` | Default `8904` |
| `SECRET_KEY` | JWT signing key |
| `DATABASE_URL` | SQLite or Postgres URL |
| `CORS_ORIGINS` | Allowed browser origins |
| `STRIPE_*` | Optional live Stripe test keys |
| `OPENAI_API_KEY` | Optional AI features |
| `ADMIN_EMAIL` / `ADMIN_PASSWORD` | Seeded admin |

## Testing

```bash
pytest -v
```

## Deployment

| Platform | Config |
|----------|--------|
| Docker | `Dockerfile`, `docker-compose.yml` |
| Render | `render.yaml` |
| Railway | `railway.json`, `Procfile` |

## License

MIT — production-style reference implementation.
