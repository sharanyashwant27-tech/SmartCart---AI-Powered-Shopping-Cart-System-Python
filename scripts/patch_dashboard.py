from pathlib import Path

path = Path("app/services/order_service.py")
text = path.read_text(encoding="utf-8")
start = text.index("    def dashboard(self) -> dict:")
prefix = text[:start]

new_dashboard = '''    def dashboard(self) -> dict:
        """Admin dashboard KPIs: revenue, orders, users, products, coupons, inventory."""
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        paid_like = [
            OrderStatus.PAID,
            OrderStatus.PROCESSING,
            OrderStatus.SHIPPED,
            OrderStatus.DELIVERED,
        ]

        def _revenue_between(start: datetime, end: datetime | None = None) -> Decimal:
            q = self.db.query(func.coalesce(func.sum(Order.total_amount), 0)).filter(
                Order.order_date >= start,
                Order.status.in_(paid_like),
            )
            if end is not None:
                q = q.filter(Order.order_date < end)
            return _money(q.scalar() or 0)

        today_revenue = _revenue_between(today_start)
        monthly_revenue = _revenue_between(month_start)
        total_revenue = _money(
            self.db.query(func.coalesce(func.sum(Order.total_amount), 0))
            .filter(Order.status.in_(paid_like))
            .scalar()
            or 0
        )

        total_orders = self.orders.count()
        pending_orders = self.orders.count([Order.status == OrderStatus.PENDING])
        cancelled_orders = self.orders.count(
            [Order.status.in_([OrderStatus.CANCELLED, OrderStatus.REFUNDED])]
        )
        total_users = self.users.count([User.role == UserRole.CUSTOMER])
        total_products = self.products.count()

        top_products = (
            self.db.query(
                OrderItem.product_name,
                func.sum(OrderItem.quantity).label("qty"),
                func.sum(OrderItem.line_total).label("revenue"),
            )
            .group_by(OrderItem.product_name)
            .order_by(func.sum(OrderItem.quantity).desc())
            .limit(10)
            .all()
        )

        inventory = self.inventory_report()
        low_stock = [i.model_dump() for i in inventory.items if i.is_low_stock][:20]

        from app.models.coupon import Coupon

        coupons = (
            self.db.query(Coupon).order_by(Coupon.created_at.desc()).limit(50).all()
        )
        coupon_rows = [
            {
                "id": c.id,
                "code": c.code,
                "discount": float(c.discount),
                "coupon_type": c.coupon_type.value,
                "expiry": c.expiry.isoformat() if c.expiry else None,
                "active": c.active,
                "used_count": c.used_count,
            }
            for c in coupons
        ]

        monthly = []
        for i in range(5, -1, -1):
            ms = (now.replace(day=1) - timedelta(days=30 * i)).replace(day=1)
            next_month = (ms + timedelta(days=32)).replace(day=1)
            count = (
                self.db.query(func.count(Order.id))
                .filter(Order.order_date >= ms, Order.order_date < next_month)
                .scalar()
            )
            revenue = (
                self.db.query(func.coalesce(func.sum(Order.total_amount), 0))
                .filter(
                    Order.order_date >= ms,
                    Order.order_date < next_month,
                    Order.status.in_(paid_like),
                )
                .scalar()
            )
            monthly.append(
                {
                    "month": ms.strftime("%Y-%m"),
                    "orders": int(count or 0),
                    "revenue": float(revenue or 0),
                }
            )

        sales = self.sales_report(days=30)
        overview = self.overview()
        top_rows = [
            {"name": r[0], "quantity": int(r[1]), "revenue": float(r[2])}
            for r in top_products
        ]

        return {
            "kpis": {
                "today_revenue": float(today_revenue),
                "monthly_revenue": float(monthly_revenue),
                "total_revenue": float(total_revenue),
                "total_orders": total_orders,
                "pending_orders": pending_orders,
                "cancelled_orders": cancelled_orders,
                "users": total_users,
                "products": total_products,
                "low_stock_count": inventory.low_stock_count,
                "out_of_stock_count": inventory.out_of_stock_count,
                "active_coupons": sum(1 for c in coupon_rows if c["active"]),
            },
            "top_products": top_rows,
            "low_stock": low_stock,
            "coupons": coupon_rows,
            "inventory": inventory.model_dump(),
            "monthly_orders": monthly,
            "overview": overview.model_dump(),
            "sales": sales.model_dump(),
            "best_sellers": top_rows[:5],
            "customer_growth": [],
            "revenue": float(total_revenue),
        }
'''

path.write_text(prefix + new_dashboard + "\n", encoding="utf-8")
print("ok")
