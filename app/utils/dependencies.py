"""FastAPI dependencies for auth, RBAC, and services."""

from typing import Annotated, Optional

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import ExpiredSignatureError, JWTError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.utils.enums import UserRole
from app.utils.exceptions import ForbiddenError, UnauthorizedError
from app.utils.security import decode_token

bearer_scheme = HTTPBearer(auto_error=False)
DbSession = Annotated[Session, Depends(get_db)]


def get_current_user(
    db: DbSession,
    credentials: Annotated[
        Optional[HTTPAuthorizationCredentials], Depends(bearer_scheme)
    ] = None,
) -> User:
    """Resolve the authenticated user (guest/customer or admin) from the Bearer JWT."""
    if credentials is None or not credentials.credentials:
        raise UnauthorizedError(
            "Please sign in as a guest or admin to continue",
            extra={"code": "missing_token"},
        )
    token = credentials.credentials.strip()
    if not token or token.lower() in {"null", "undefined", "bearer"}:
        raise UnauthorizedError(
            "Please sign in as a guest or admin to continue",
            extra={"code": "missing_token"},
        )
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise UnauthorizedError(
                "Invalid access token — please sign in again",
                extra={"code": "invalid_token_type"},
            )
        user_id = payload.get("sub")
        if user_id is None or user_id == "":
            raise UnauthorizedError(
                "Invalid token subject — please sign in again",
                extra={"code": "invalid_subject"},
            )
        user = UserRepository(db).get_by_id(int(user_id))
    except ExpiredSignatureError as exc:
        raise UnauthorizedError(
            "Session expired — please sign in again",
            extra={"code": "token_expired"},
        ) from exc
    except UnauthorizedError:
        raise
    except (JWTError, ValueError, TypeError) as exc:
        raise UnauthorizedError(
            "Could not validate credentials — please sign in as guest or admin",
            extra={"code": "invalid_token"},
        ) from exc

    if user is None:
        raise UnauthorizedError(
            "Account not found — please sign in again",
            extra={"code": "user_not_found"},
        )
    if not user.is_active:
        raise UnauthorizedError(
            "Account is inactive",
            extra={"code": "user_inactive"},
        )
    # Guest (customer) and admin are both valid cart/checkout actors
    if user.role not in {UserRole.CUSTOMER, UserRole.ADMIN}:
        raise UnauthorizedError(
            "Unsupported account role",
            extra={"code": "invalid_role"},
        )
    return user


def get_current_active_user(
    user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Ensure the authenticated user is active."""
    if not user.is_active:
        raise UnauthorizedError("Inactive user")
    return user


def require_admin(
    user: Annotated[User, Depends(get_current_active_user)],
) -> User:
    """Require admin role (RBAC)."""
    if user.role != UserRole.ADMIN:
        raise ForbiddenError("Admin privileges required")
    return user


def get_optional_user(
    db: DbSession,
    credentials: Annotated[
        Optional[HTTPAuthorizationCredentials], Depends(bearer_scheme)
    ] = None,
) -> Optional[User]:
    """Return user if token present and valid, otherwise None."""
    if credentials is None or not credentials.credentials:
        return None
    try:
        return get_current_user(db, credentials)
    except UnauthorizedError:
        return None


CurrentUser = Annotated[User, Depends(get_current_active_user)]
AdminUser = Annotated[User, Depends(require_admin)]
OptionalUser = Annotated[Optional[User], Depends(get_optional_user)]
