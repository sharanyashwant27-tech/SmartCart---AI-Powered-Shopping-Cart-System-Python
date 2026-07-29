"""Address book routes (users domain)."""

from fastapi import APIRouter

from app.utils.dependencies import CurrentUser, DbSession
from app.schemas.extra import AddressCreate, AddressResponse, AddressUpdate
from app.schemas.user import MessageResponse
from app.services.address_service import AddressService

addresses_router = APIRouter(prefix="/addresses", tags=["Address Book"])


@addresses_router.get("", response_model=list[AddressResponse])
async def list_addresses(user: CurrentUser, db: DbSession) -> list[AddressResponse]:
    return AddressService(db).list(user.id)


@addresses_router.post("", response_model=AddressResponse, status_code=201)
async def create_address(
    payload: AddressCreate, user: CurrentUser, db: DbSession
) -> AddressResponse:
    return AddressService(db).create(user.id, payload)


@addresses_router.patch("/{address_id}", response_model=AddressResponse)
async def update_address(
    address_id: int, payload: AddressUpdate, user: CurrentUser, db: DbSession
) -> AddressResponse:
    return AddressService(db).update(user.id, address_id, payload)


@addresses_router.delete("/{address_id}", response_model=MessageResponse)
async def delete_address(
    address_id: int, user: CurrentUser, db: DbSession
) -> MessageResponse:
    AddressService(db).delete(user.id, address_id)
    return MessageResponse(message="Address deleted")
