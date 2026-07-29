"""PDF invoice generation for orders."""

from __future__ import annotations

import io
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.models.order import Order


def build_invoice_pdf(order: Order) -> bytes:
    """Render a simple professional invoice PDF for an order."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.7 * inch,
        bottomMargin=0.7 * inch,
    )
    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        "InvoiceTitle",
        parent=styles["Heading1"],
        textColor=colors.HexColor("#0f766e"),
        spaceAfter=6,
    )
    muted = ParagraphStyle("Muted", parent=styles["Normal"], textColor=colors.HexColor("#5b6b76"))

    story = [
        Paragraph("SmartCart", title),
        Paragraph("Tax Invoice / Bill", muted),
        Spacer(1, 0.25 * inch),
        Paragraph(f"<b>Order:</b> {order.order_number}", styles["Normal"]),
        Paragraph(f"<b>Status:</b> {order.status.value}", styles["Normal"]),
        Paragraph(
            f"<b>Payment status:</b> {order.payment_status.value}",
            styles["Normal"],
        ),
        Paragraph(
            f"<b>Date:</b> {(order.order_date or order.created_at or datetime.utcnow()).strftime('%Y-%m-%d %H:%M UTC')}",
            styles["Normal"],
        ),
        Spacer(1, 0.15 * inch),
        Paragraph(f"<b>Ship to:</b> {order.shipping_address}", styles["Normal"]),
        Paragraph(f"<b>Bill to:</b> {order.billing_address or order.shipping_address}", styles["Normal"]),
    ]
    if order.payment:
        method = (order.payment.provider or "card").replace("_", " ").title()
        story.append(Paragraph(f"<b>Payment method:</b> {method}", styles["Normal"]))
        if order.payment.stripe_payment_intent_id:
            story.append(
                Paragraph(
                    f"<b>Payment ref:</b> {order.payment.stripe_payment_intent_id}",
                    muted,
                )
            )
    story.append(Spacer(1, 0.25 * inch))

    rows = [["Item", "SKU", "Qty", "Unit", "Line Total"]]
    for item in order.items:
        rows.append(
            [
                item.product_name,
                item.product_sku,
                str(item.quantity),
                f"${float(item.unit_price):.2f}",
                f"${float(item.line_total):.2f}",
            ]
        )

    table = Table(rows, colWidths=[2.6 * inch, 1.1 * inch, 0.6 * inch, 0.9 * inch, 1.0 * inch])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f766e")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d7e0db")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f3f6f4")]),
                ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(table)
    story.append(Spacer(1, 0.25 * inch))

    totals = [
        ["Subtotal", f"${float(order.subtotal):.2f}"],
        ["Discount", f"-${float(order.discount_amount):.2f}"],
        ["Shipping", f"${float(order.shipping_amount):.2f}"],
        ["Tax", f"${float(order.tax_amount):.2f}"],
        ["Total", f"${float(order.total_amount):.2f}"],
    ]
    totals_table = Table(totals, colWidths=[4.5 * inch, 1.5 * inch])
    totals_table.setStyle(
        TableStyle(
            [
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ("TEXTCOLOR", (0, -1), (-1, -1), colors.HexColor("#0f766e")),
                ("LINEABOVE", (0, -1), (-1, -1), 1, colors.HexColor("#0f766e")),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(totals_table)
    if order.coupon_code:
        story.append(Spacer(1, 0.1 * inch))
        story.append(Paragraph(f"Coupon applied: <b>{order.coupon_code}</b>", muted))
    if order.tracking_number:
        story.append(
            Paragraph(
                f"Tracking: <b>{order.tracking_number}</b> ({order.carrier or 'carrier TBD'})",
                muted,
            )
        )

    doc.build(story)
    return buffer.getvalue()
