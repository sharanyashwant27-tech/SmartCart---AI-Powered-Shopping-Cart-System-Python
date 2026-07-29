"""Authentication API routes."""

from fastapi import APIRouter, Request

from app.utils.dependencies import CurrentUser, DbSession
from app.utils.logging import get_logger
from app.schemas.user import (
    MessageResponse,
    RefreshTokenRequest,
    TokenResponse,
    UserLogin,
    UserRegister,
    UserResponse,
)
from app.schemas.extra import ForgotPasswordRequest, ResetPasswordRequest
from app.utils.rate_limit import limiter
from app.services.auth_service import AuthService
from app.services.address_service import PasswordResetService

router = APIRouter(prefix="/auth", tags=["Authentication"])
logger = get_logger(__name__)


@router.post("/register", response_model=TokenResponse, status_code=201)
@limiter.limit("10/minute")
async def register(request: Request, payload: UserRegister, db: DbSession) -> TokenResponse:
    """Register a new customer account."""
    logger.info("User registration attempt: %s", payload.email)
    return AuthService(db).register(payload)


@router.post("/login", response_model=TokenResponse)
@limiter.limit("20/minute")
async def login(request: Request, payload: UserLogin, db: DbSession) -> TokenResponse:
    """Login with email and password."""
    return AuthService(db).login(payload.email, payload.password)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(payload: RefreshTokenRequest, db: DbSession) -> TokenResponse:
    """Exchange a refresh token for a new token pair."""
    return AuthService(db).refresh(payload.refresh_token)


@router.get("/me", response_model=UserResponse)
async def me(user: CurrentUser) -> UserResponse:
    """Return the current authenticated user."""
    return UserResponse.model_validate(user)


@router.post("/logout", response_model=MessageResponse)
async def logout(user: CurrentUser) -> MessageResponse:
    """Client-side logout acknowledgment (JWT is stateless)."""
    return MessageResponse(message=f"Logged out {user.email}")


@router.post("/forgot-password")
async def forgot_password(payload: ForgotPasswordRequest, db: DbSession) -> dict:
    """Request a password reset token (returned in sandbox/dev responses)."""
    return PasswordResetService(db).request_reset(payload.email)


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(payload: ResetPasswordRequest, db: DbSession) -> MessageResponse:
    return PasswordResetService(db).reset_password(payload)
