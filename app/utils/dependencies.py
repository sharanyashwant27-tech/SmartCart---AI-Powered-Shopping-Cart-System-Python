"""FastAPI dependencies for auth, RBAC, and services."""

from typing import Annotated, Optional

from fastapi import Depends, Header
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.database import get_db
from app.utils.enums import UserRole
from app.utils.exceptions import ForbiddenError, UnauthorizedError
from app.utils.security import decode_token
from app.models.user import User
from app.repositories.user_repository import UserRepository

bearer_scheme = HTTPBearer(auto_error=False)
DbSession = Annotated[Session, Depends(get_db)]


def get_current_user(
    db: DbSession,
    credentials: Annotated[
        Optional[HTTPAuthorizationCredentials], Depends(bearer_scheme)
    ] = None,
) -> User:
    """Resolve the authenticated user from the Bearer JWT."""
    if credentials is None or not credentials.credentials:
        raise UnauthorizedError("Missing authentication token")
    try:
        payload = decode_token(credentials.credentials)
        if payload.get("type") != "access":
            raise UnauthorizedError("Invalid token type")
        user_id = payload.get("sub")
        if not user_id:
            raise UnauthorizedError("Invalid token subject")
    except JWTError as exc:
        raise UnauthorizedError("Could not validate credentials") from exc

    user = UserRepository(db).get_by_id(int(user_id))
    if user is None or not user.is_active:
        raise UnauthorizedError("User inactive or not found")
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
    """Return user if token present, otherwise None."""
    if credentials is None or not credentials.credentials:
        return None
    try:
        return get_current_user(db, credentials)
    except UnauthorizedError:
        return None


CurrentUser = Annotated[User, Depends(get_current_active_user)]
AdminUser = Annotated[User, Depends(require_admin)]
OptionalUser = Annotated[Optional[User], Depends(get_optional_user)]
