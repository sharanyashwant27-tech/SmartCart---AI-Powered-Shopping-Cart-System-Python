"""Shared enums used across models and schemas."""

import enum


class UserRole(str, enum.Enum):
    CUSTOMER = "customer"
    ADMIN = "admin"


class OrderStatus(str, enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"
    RETURN_REQUESTED = "return_requested"
    RETURNED = "returned"


class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    REFUNDED = "refunded"
    CANCELLED = "cancelled"


class CouponType(str, enum.Enum):
    PERCENTAGE = "percentage"
    FIXED = "fixed"


class PaymentMethod(str, enum.Enum):
    CARD = "card"
    UPI = "upi"
    NETBANKING = "netbanking"
    WALLET = "wallet"
    COD = "cod"


class CartItemStatus(str, enum.Enum):
    ACTIVE = "active"
    SAVED_FOR_LATER = "saved_for_later"


class AddressType(str, enum.Enum):
    SHIPPING = "shipping"
    BILLING = "billing"
    BOTH = "both"
