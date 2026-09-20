from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.server.app import create_app
from core.infrastructure.postgres.models.api_access_token import ApiAccessToken
from core.infrastructure.postgres.models.api_user import ApiUser
from core.infrastructure.postgres.models.base import Base


def test_swagger_and_healthcheck_are_exposed():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine, tables=[ApiUser.__table__, ApiAccessToken.__table__])
    client = TestClient(create_app(sessionmaker(bind=engine, expire_on_commit=False)))

    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/docs").status_code == 200
    assert client.get("/openapi.json").json()["info"]["title"] == "Harness Memory API"


def test_user_and_token_crud_http_contract():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine, tables=[ApiUser.__table__, ApiAccessToken.__table__])
    client = TestClient(create_app(sessionmaker(bind=engine, expire_on_commit=False)))

    created_user = client.post(
        "/users", json={"name": "Ada", "email": "ada@example.com"}
    )
    assert created_user.status_code == 201
    user_id = created_user.json()["id"]
    assert client.get(f"/users/{user_id}").status_code == 200
    assert client.patch(f"/users/{user_id}", json={"name": "Ada Lovelace"}).json()[
        "name"
    ] == "Ada Lovelace"

    expires_at = (datetime.now(UTC) + timedelta(days=30)).isoformat()
    created_token = client.post(
        "/tokens",
        json={"user_id": user_id, "name": "agent", "expires_at": expires_at},
    )
    assert created_token.status_code == 201
    assert created_token.json()["token"].startswith("hm_")
    token_id = created_token.json()["id"]
    assert client.get(f"/tokens/{token_id}").status_code == 200
    assert client.patch(f"/tokens/{token_id}", json={"name": "renamed"}).json()[
        "name"
    ] == "renamed"
    assert client.delete(f"/tokens/{token_id}").status_code == 204
    assert client.delete(f"/users/{user_id}").status_code == 204


def test_http_rejects_token_lifetime_over_ninety_days():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine, tables=[ApiUser.__table__, ApiAccessToken.__table__])
    client = TestClient(create_app(sessionmaker(bind=engine, expire_on_commit=False)))
    user_id = client.post(
        "/users", json={"name": "Ada", "email": "ada@example.com"}
    ).json()["id"]

    response = client.post(
        "/tokens",
        json={
            "user_id": user_id,
            "name": "agent",
            "expires_at": (datetime.now(UTC) + timedelta(days=91)).isoformat(),
        },
    )

    assert response.status_code == 422
