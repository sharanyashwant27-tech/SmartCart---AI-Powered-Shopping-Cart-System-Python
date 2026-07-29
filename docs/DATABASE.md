# Database Design

SmartCart core schema (production model includes additional helper columns; synonyms keep older attribute names working).

## Users

| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | |
| name | VARCHAR(150) | Display name |
| email | VARCHAR(255) UNIQUE | |
| password | VARCHAR(255) | bcrypt hash |
| phone | VARCHAR(30) | nullable |
| role | ENUM | `customer` / `admin` |
| created_at | DATETIME | |

## Products

| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | |
| name | VARCHAR(200) | |
| description | TEXT | |
| category_id | FK → categories | category |
| brand_id | FK → brands | brand |
| price | NUMERIC(12,2) | |
| stock | INTEGER | |
| rating | NUMERIC(3,2) | avg from reviews |
| image | VARCHAR(500) | primary image URL |

## Cart (`cart_items`)

| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | |
| user_id | FK → users | |
| product_id | FK → products | |
| quantity | INTEGER | |
| price | NUMERIC(12,2) | unit price snapshot |
| subtotal | NUMERIC(12,2) | price × quantity |

## Orders

| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | |
| user_id | FK → users | |
| order_date | DATETIME | |
| status | ENUM | pending → delivered / cancelled / returned |
| payment_status | ENUM | pending / succeeded / failed / refunded |
| total_amount | NUMERIC(12,2) | |
| shipping_address | TEXT | |

## Order Items

| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | |
| order_id | FK → orders | |
| product_id | FK → products | |
| quantity | INTEGER | |
| price | NUMERIC(12,2) | unit price at purchase |

## Coupons

| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | |
| code | VARCHAR(40) UNIQUE | |
| discount | NUMERIC(12,2) | amount or percent value |
| expiry | DATETIME | nullable |
| active | BOOLEAN | |

Related tables also present: `categories`, `brands`, `payments`, `wishlist_items`, `reviews`, `product_images`, `addresses`.
