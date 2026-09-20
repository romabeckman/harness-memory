from uuid import UUID

from fastapi import APIRouter, HTTPException, Response, status

from api.adapters.http.schemas.service_account_create import ServiceAccountCreate
from api.adapters.http.schemas.service_account_response import ServiceAccountResponse
from api.adapters.http.schemas.service_account_update import ServiceAccountUpdate
from api.application.services.service_account_service import ServiceAccountService


def create_service_account_router(service: ServiceAccountService) -> APIRouter:
    router = APIRouter(prefix="/service-accounts", tags=["service accounts"])

    @router.post("", response_model=ServiceAccountResponse, status_code=status.HTTP_201_CREATED)
    def create_service_account(payload: ServiceAccountCreate) -> ServiceAccountResponse:
        try:
            account = service.create(payload.name, payload.tenant_id)
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        return ServiceAccountResponse(id=account.id, tenant_id=account.tenant_id, name=account.name)

    @router.get("", response_model=list[ServiceAccountResponse])
    def list_service_accounts(tenant_id: UUID | None = None) -> list[ServiceAccountResponse]:
        return [
            ServiceAccountResponse(id=item.id, tenant_id=item.tenant_id, name=item.name)
            for item in service.list(tenant_id)
        ]

    @router.get("/{account_id}", response_model=ServiceAccountResponse)
    def get_service_account(account_id: UUID) -> ServiceAccountResponse:
        try:
            account = service.get(account_id)
        except LookupError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        return ServiceAccountResponse(id=account.id, tenant_id=account.tenant_id, name=account.name)

    @router.patch("/{account_id}", response_model=ServiceAccountResponse)
    def update_service_account(
        account_id: UUID, payload: ServiceAccountUpdate
    ) -> ServiceAccountResponse:
        try:
            account = service.update(account_id, name=payload.name)
        except LookupError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        return ServiceAccountResponse(id=account.id, tenant_id=account.tenant_id, name=account.name)

    @router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_service_account(account_id: UUID) -> Response:
        try:
            service.delete(account_id)
        except LookupError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    return router
