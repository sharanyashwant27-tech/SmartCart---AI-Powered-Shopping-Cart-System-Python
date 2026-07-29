"""QR code generation for SmartCart payments."""

from __future__ import annotations

import base64
import io
from decimal import Decimal
from typing import Optional
from urllib.parse import quote

import qrcode
from qrcode.constants import ERROR_CORRECT_M


def build_upi_payload(
    *,
    amount: Decimal | float | str,
    order_number: str,
    vpa: str = "smartcart@upi",
    payee_name: str = "SmartCart",
    currency: str = "INR",
) -> str:
    """Build a UPI deep-link that payment apps can scan from a QR code."""
    am = f"{float(amount):.2f}"
    tn = quote(f"SmartCart {order_number}")
    pn = quote(payee_name)
    pa = quote(vpa)
    return (
        f"upi://pay?pa={pa}&pn={pn}&am={am}&cu={currency.upper()}&tn={tn}"
    )


def qr_png_base64(payload: str, box_size: int = 8, border: int = 2) -> str:
    """Return a PNG QR code as a base64 string (no data: prefix)."""
    qr = qrcode.QRCode(
        version=None,
        error_correction=ERROR_CORRECT_M,
        box_size=box_size,
        border=border,
    )
    qr.add_data(payload)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#0f766e", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


def payment_qr(
    *,
    amount: Decimal | float | str,
    order_number: str,
    vpa: str = "smartcart@upi",
    payee_name: str = "SmartCart",
    currency: str = "INR",
    extra_note: Optional[str] = None,
) -> dict:
    """
    Create QR payload + image for checkout.

    Returns:
      { payload, image_base64, mime, vpa, amount }
    """
    payload = build_upi_payload(
        amount=amount,
        order_number=order_number,
        vpa=vpa,
        payee_name=payee_name,
        currency=currency,
    )
    if extra_note:
        # Keep payload UPI-valid; note is for UI only
        pass
    return {
        "payload": payload,
        "image_base64": qr_png_base64(payload),
        "mime": "image/png",
        "vpa": vpa,
        "amount": f"{float(amount):.2f}",
        "order_number": order_number,
    }
