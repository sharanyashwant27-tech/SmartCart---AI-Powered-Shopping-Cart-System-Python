"""User management API routes."""

from typing import Optional

from fastapi import APIRouter, Query

from app.utils.dependencies import AdminUser, CurrentUser, DbSession
from app.schemas.user import AdminUserUpdate, MessageResponse, UserResponse, UserUpdate
from app.services.auth_service import UserService

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserResponse)
async def get_profile(user: CurrentUser) -> UserResponse:
    return UserResponse.model_validate(user)


@router.patch("/me", response_model=UserResponse)
async def update_profile(
    payload: UserUpdate, user: CurrentUser, db: DbSession
) -> UserResponse:
    updated = UserService(db).update_profile(user, payload)
    return UserResponse.model_validate(updated)


@router.get("", response_model=list[UserResponse])
async def list_customers(
    _: AdminUser,
    db: DbSession,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    active_only: bool = False,
) -> list[UserResponse]:
    items, _ = UserService(db).list_customers(
        skip=skip, limit=limit, active_only=active_only
    )
    return [UserResponse.model_validate(u) for u in items]


@router.get("/{user_id}", response_model=UserResponse)
async def get_customer(user_id: int, _: AdminUser, db: DbSession) -> UserResponse:
    return UserResponse.model_validate(UserService(db).get(user_id))


@router.patch("/{user_id}", response_model=UserResponse)
async def admin_update_customer(
    user_id: int, payload: AdminUserUpdate, _: AdminUser, db: DbSession
) -> UserResponse:
    return UserResponse.model_validate(UserService(db).admin_update(user_id, payload))
