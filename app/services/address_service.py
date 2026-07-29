"""Address book and forgot-password services."""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.utils.exceptions import NotFoundError, ValidationAppError
from app.utils.logging import get_logger
from app.utils.security import hash_password
from app.models.address import Address, PasswordResetToken
from app.repositories.base import BaseRepository
from app.repositories.user_repository import UserRepository
from app.schemas.extra import AddressCreate, AddressResponse, AddressUpdate, ResetPasswordRequest
from app.schemas.user import MessageResponse

logger = get_logger(__name__)


class AddressRepository(BaseRepository[Address]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, Address)

    def list_for_user(self, user_id: int) -> list[Address]:
        return (
            self.db.query(Address)
            .filter(Address.user_id == user_id)
            .order_by(Address.is_default.desc(), Address.id.desc())
            .all()
        )


class AddressService:
    def __init__(self, db: Session) -> None:
        self.repo = AddressRepository(db)
        self.db = db

    def _to_response(self, addr: Address) -> AddressResponse:
        payload = {
            "id": addr.id,
            "user_id": addr.user_id,
            "label": addr.label,
            "full_name": addr.full_name,
            "phone": addr.phone,
            "line1": addr.line1,
            "line2": addr.line2,
            "city": addr.city,
            "state": addr.state,
            "postal_code": addr.postal_code,
            "country": addr.country,
            "address_type": addr.address_type,
            "is_default": addr.is_default,
            "created_at": addr.created_at,
            "formatted": addr.formatted(),
        }
        return AddressResponse.model_validate(payload)

    def list(self, user_id: int) -> list[AddressResponse]:
        return [self._to_response(a) for a in self.repo.list_for_user(user_id)]

    def create(self, user_id: int, payload: AddressCreate) -> AddressResponse:
        if payload.is_default:
            self._clear_defaults(user_id)
        entity = Address(user_id=user_id, **payload.model_dump())
        return self._to_response(self.repo.create(entity))

    def update(self, user_id: int, address_id: int, payload: AddressUpdate) -> AddressResponse:
        addr = self.repo.get_by_id(address_id)
        if addr is None or addr.user_id != user_id:
            raise NotFoundError("Address not found")
        data = payload.model_dump(exclude_unset=True)
        if data.get("is_default"):
            self._clear_defaults(user_id)
        return self._to_response(self.repo.update(addr, data))

    def delete(self, user_id: int, address_id: int) -> None:
        addr = self.repo.get_by_id(address_id)
        if addr is None or addr.user_id != user_id:
            raise NotFoundError("Address not found")
        self.repo.delete(addr)

    def _clear_defaults(self, user_id: int) -> None:
        for addr in self.repo.list_for_user(user_id):
            if addr.is_default:
                addr.is_default = False
        self.db.commit()


class PasswordResetService:
    """Forgot-password flow. In development the reset token is returned in the API response."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.users = UserRepository(db)

    def request_reset(self, email: str) -> dict:
        user = self.users.get_by_email(email)
        # Always return success to avoid email enumeration
        if user is None:
            return {
                "success": True,
                "message": "If that email exists, a reset link was generated.",
                "reset_token": None,
            }
        token = secrets.token_urlsafe(32)
        entity = PasswordResetToken(
            user_id=user.id,
            token=token,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        self.db.add(entity)
        self.db.commit()
        logger.info("Password reset token created for user_id=%s", user.id)
        return {
            "success": True,
            "message": "If that email exists, a reset link was generated.",
            "reset_token": token,  # exposed for sandbox/dev (no email provider wired)
        }

    def reset_password(self, payload: ResetPasswordRequest) -> MessageResponse:
        row = (
            self.db.query(PasswordResetToken)
            .filter(PasswordResetToken.token == payload.token)
            .first()
        )
        if row is None or row.used:
            raise ValidationAppError("Invalid or used reset token")
        expires = row.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if expires < datetime.now(timezone.utc):
            raise ValidationAppError("Reset token has expired")
        user = self.users.get_by_id(row.user_id)
        if user is None:
            raise NotFoundError("User not found")
        user.hashed_password = hash_password(payload.new_password)
        row.used = True
        self.db.commit()
        return MessageResponse(message="Password updated successfully")
