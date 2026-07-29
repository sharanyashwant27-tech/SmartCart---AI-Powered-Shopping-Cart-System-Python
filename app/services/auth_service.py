"""Authentication and user management services."""

from jose import JWTError
from sqlalchemy.orm import Session

from app.utils.enums import UserRole
from app.utils.exceptions import ConflictError, NotFoundError, UnauthorizedError
from app.utils.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import (
    AdminUserUpdate,
    TokenResponse,
    UserRegister,
    UserResponse,
    UserUpdate,
)


class AuthService:
    def __init__(self, db: Session) -> None:
        self.users = UserRepository(db)

    def register(self, payload: UserRegister) -> TokenResponse:
        if self.users.email_exists(payload.email):
            raise ConflictError("Email already registered")
        user = User(
            email=payload.email.lower(),
            password=hash_password(payload.password),
            name=payload.full_name,
            phone=payload.phone,
            role=UserRole.CUSTOMER,
        )
        user = self.users.create(user)
        return self._tokens_for(user)

    def login(self, email: str, password: str) -> TokenResponse:
        user = self.users.get_by_email(email)
        if user is None or not verify_password(password, user.hashed_password):
            raise UnauthorizedError("Invalid email or password")
        if not user.is_active:
            raise UnauthorizedError("Account is inactive")
        return self._tokens_for(user)

    def refresh(self, refresh_token: str) -> TokenResponse:
        try:
            payload = decode_token(refresh_token)
            if payload.get("type") != "refresh":
                raise UnauthorizedError("Invalid refresh token")
            user_id = int(payload["sub"])
        except (JWTError, KeyError, ValueError) as exc:
            raise UnauthorizedError("Invalid refresh token") from exc
        user = self.users.get_by_id(user_id)
        if user is None or not user.is_active:
            raise UnauthorizedError("User not found or inactive")
        return self._tokens_for(user)

    def _tokens_for(self, user: User) -> TokenResponse:
        claims = {"role": user.role.value, "email": user.email}
        return TokenResponse(
            access_token=create_access_token(str(user.id), claims),
            refresh_token=create_refresh_token(str(user.id)),
            user=UserResponse.model_validate(user),
        )


class UserService:
    def __init__(self, db: Session) -> None:
        self.users = UserRepository(db)

    def get(self, user_id: int) -> User:
        user = self.users.get_by_id(user_id)
        if user is None:
            raise NotFoundError("User not found")
        return user

    def update_profile(self, user: User, payload: UserUpdate) -> User:
        data = payload.model_dump(exclude_unset=True)
        if "full_name" in data and "name" not in data:
            data["name"] = data.pop("full_name")
        elif "full_name" in data:
            data.pop("full_name")
        return self.users.update(user, data)

    def admin_update(self, user_id: int, payload: AdminUserUpdate) -> User:
        user = self.get(user_id)
        data = payload.model_dump(exclude_unset=True)
        if "full_name" in data and "name" not in data:
            data["name"] = data.pop("full_name")
        elif "full_name" in data:
            data.pop("full_name")
        return self.users.update(user, data)

    def list_customers(
        self, *, skip: int = 0, limit: int = 50, active_only: bool = False
    ) -> tuple[list[User], int]:
        filters = [User.role == UserRole.CUSTOMER]
        if active_only:
            filters.append(User.is_active.is_(True))
        items = self.users.list(skip=skip, limit=limit, filters=filters, order_by=User.created_at.desc())
        total = self.users.count(filters)
        return items, total

    def ensure_admin(self, email: str, password: str, full_name: str) -> User:
        existing = self.users.get_by_email(email)
        if existing:
            return existing
        admin = User(
            email=email.lower(),
            password=hash_password(password),
            name=full_name,
            role=UserRole.ADMIN,
            is_active=True,
        )
        return self.users.create(admin)
