from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Response, status

from api.adapters.http.schemas.token_create import TokenCreate
from api.adapters.http.schemas.token_created_response import TokenCreatedResponse
from api.adapters.http.schemas.token_response import TokenResponse
from api.adapters.http.schemas.token_update import TokenUpdate
from api.application.services.token_service import TokenService


def create_token_router(service: TokenService) -> APIRouter:
    router = APIRouter(prefix="/tokens", tags=["tokens"])

    @router.post("", response_model=TokenCreatedResponse, status_code=status.HTTP_201_CREATED)
    def create_token(payload: TokenCreate) -> TokenCreatedResponse:
        try:
            issued = service.create(
                user_id=payload.user_id,
                service_account_id=payload.service_account_id,
                name=payload.name,
                expires_at=payload.expires_at,
                scopes=payload.scopes,
            )
        except LookupError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        token = issued.token
        return TokenCreatedResponse(
            id=token.id,
            user_id=token.user_id,
            service_account_id=token.service_account_id,
            name=token.name,
            expires_at=token.expires_at,
            token=issued.plaintext,
            scopes=set(token.scopes),
        )

    @router.get("", response_model=list[TokenResponse])
    def list_tokens(
        user_id: UUID | None = None,
        service_account_id: UUID | None = None,
        name: str | None = None,
        scope: str | None = None,
        q: str | None = None,
        limit: int = Query(100, ge=1, le=500),
        offset: int = Query(0, ge=0),
    ) -> list[TokenResponse]:
        tokens = service.list(user_id, service_account_id)
        if name:
            needle = name.casefold()
            tokens = [item for item in tokens if needle in item.name.casefold()]
        if scope:
            tokens = [item for item in tokens if scope in item.scopes]
        if q:
            needle = q.casefold()
            tokens = [item for item in tokens if needle in item.name.casefold()]
        return [
            TokenResponse(
                id=item.id,
                user_id=item.user_id,
                service_account_id=item.service_account_id,
                name=item.name,
                expires_at=item.expires_at,
                scopes=set(item.scopes),
            )
            for item in tokens[offset:offset + limit]
        ]

    @router.get("/{token_id}", response_model=TokenResponse)
    def get_token(token_id: UUID) -> TokenResponse:
        try:
            token = service.get(token_id)
        except LookupError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        return TokenResponse(
            id=token.id,
            user_id=token.user_id,
            service_account_id=token.service_account_id,
            name=token.name,
            expires_at=token.expires_at,
            scopes=set(token.scopes),
        )

    @router.patch("/{token_id}", response_model=TokenResponse)
    def update_token(token_id: UUID, payload: TokenUpdate) -> TokenResponse:
        try:
            token = service.update(
                token_id,
                name=payload.name,
                expires_at=payload.expires_at,
            )
        except LookupError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        return TokenResponse(
            id=token.id,
            user_id=token.user_id,
            service_account_id=token.service_account_id,
            name=token.name,
            expires_at=token.expires_at,
            scopes=set(token.scopes),
        )

    @router.delete("/{token_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_token(token_id: UUID) -> Response:
        try:
            service.delete(token_id)
        except LookupError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    return router
