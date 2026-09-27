from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Response, status

from api.adapters.http.schemas.user_create import UserCreate
from api.adapters.http.schemas.user_response import UserResponse
from api.adapters.http.schemas.user_update import UserUpdate
from api.application.services.user_service import UserService


def create_user_router(service: UserService) -> APIRouter:
    router = APIRouter(prefix="/users", tags=["users"])

    @router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
    def create_user(payload: UserCreate) -> UserResponse:
        try:
            user = service.create(payload.name, str(payload.email))
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        return UserResponse(id=user.id, name=user.name, email=user.email)

    @router.get("", response_model=list[UserResponse])
    def list_users(
        name: str | None = None,
        email: str | None = None,
        q: str | None = None,
        limit: int = Query(100, ge=1, le=500),
        offset: int = Query(0, ge=0),
    ) -> list[UserResponse]:
        users = service.list(name=name, email=email, q=q, limit=limit, offset=offset)
        return [
            UserResponse(id=item.id, name=item.name, email=item.email)
            for item in users
        ]

    @router.get("/{user_id}", response_model=UserResponse)
    def get_user(user_id: UUID) -> UserResponse:
        try:
            user = service.get(user_id)
        except LookupError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        return UserResponse(id=user.id, name=user.name, email=user.email)

    @router.patch("/{user_id}", response_model=UserResponse)
    def update_user(user_id: UUID, payload: UserUpdate) -> UserResponse:
        try:
            user = service.update(
                user_id,
                name=payload.name,
                email=str(payload.email) if payload.email is not None else None,
            )
        except LookupError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        return UserResponse(id=user.id, name=user.name, email=user.email)

    @router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_user(user_id: UUID) -> Response:
        try:
            service.delete(user_id)
        except LookupError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    return router
