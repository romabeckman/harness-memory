from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.server.app import create_app
from core.infrastructure.postgres.models.api_access_token import ApiAccessToken
from core.infrastructure.postgres.models.api_service_account import ApiServiceAccount
from core.infrastructure.postgres.models.api_user import ApiUser
from core.infrastructure.postgres.models.base import Base

ADMIN_TOKEN = "test-admin-secret"
ADMIN_HEADERS = {"Authorization": f"Bearer {ADMIN_TOKEN}"}


def test_swagger_and_healthcheck_are_exposed():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(
        engine,
        tables=[ApiUser.__table__, ApiServiceAccount.__table__, ApiAccessToken.__table__],
    )
    client = TestClient(
        create_app(sessionmaker(bind=engine, expire_on_commit=False), admin_token=ADMIN_TOKEN),
        headers=ADMIN_HEADERS,
    )

    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/docs").status_code == 200
    openapi = client.get("/openapi.json").json()
    assert openapi["info"]["title"] == "Harness Memory API"
    assert "/v1/users" in openapi["paths"]
    assert "/v1/tokens" in openapi["paths"]
    assert "/v1/service-accounts" in openapi["paths"]
    assert "/users" not in openapi["paths"]
    assert "/tokens" not in openapi["paths"]


def test_user_and_token_crud_http_contract():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(
        engine,
        tables=[ApiUser.__table__, ApiServiceAccount.__table__, ApiAccessToken.__table__],
    )
    client = TestClient(
        create_app(sessionmaker(bind=engine, expire_on_commit=False), admin_token=ADMIN_TOKEN),
        headers=ADMIN_HEADERS,
    )

    user_payload = {"name": "Ada", "email": "ada@example.com"}
    assert client.post("/users", json=user_payload).status_code == 404
    created_user = client.post("/v1/users", json=user_payload)
    assert created_user.status_code == 201
    user_id = created_user.json()["id"]
    assert client.get(f"/v1/users/{user_id}").status_code == 200
    assert (
        client.patch(f"/v1/users/{user_id}", json={"name": "Ada Lovelace"}).json()["name"]
        == "Ada Lovelace"
    )

    expires_at = (datetime.now(UTC) + timedelta(days=30)).isoformat()
    created_token = client.post(
        "/v1/tokens",
        json={"user_id": user_id, "name": "agent", "expires_at": expires_at},
    )
    assert created_token.status_code == 201
    assert created_token.json()["token"].startswith("hm_")
    token_id = created_token.json()["id"]
    assert client.get(f"/v1/tokens/{token_id}").status_code == 200
    assert (
        client.patch(f"/v1/tokens/{token_id}", json={"name": "renamed"}).json()["name"] == "renamed"
    )
    assert client.delete(f"/v1/tokens/{token_id}").status_code == 204
    assert client.delete(f"/v1/users/{user_id}").status_code == 204


def test_http_rejects_token_lifetime_over_ninety_days():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(
        engine,
        tables=[ApiUser.__table__, ApiServiceAccount.__table__, ApiAccessToken.__table__],
    )
    client = TestClient(
        create_app(sessionmaker(bind=engine, expire_on_commit=False), admin_token=ADMIN_TOKEN),
        headers=ADMIN_HEADERS,
    )
    user_id = client.post("/v1/users", json={"name": "Ada", "email": "ada@example.com"}).json()[
        "id"
    ]

    response = client.post(
        "/v1/tokens",
        json={
            "user_id": user_id,
            "name": "agent",
            "expires_at": (datetime.now(UTC) + timedelta(days=91)).isoformat(),
        },
    )

    assert response.status_code == 422


def test_service_account_crud_issues_non_expiring_token():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(
        engine,
        tables=[ApiUser.__table__, ApiServiceAccount.__table__, ApiAccessToken.__table__],
    )
    client = TestClient(
        create_app(sessionmaker(bind=engine, expire_on_commit=False), admin_token=ADMIN_TOKEN),
        headers=ADMIN_HEADERS,
    )
    tenant_id = "a89e819c-27cb-4c90-82ec-baa868cd529d"
    created = client.post(
        "/v1/service-accounts",
        json={"name": "Build agent", "tenant_id": tenant_id},
    )

    assert created.status_code == 201
    account_id = created.json()["id"]
    assert created.json()["tenant_id"] == tenant_id
    assert client.get(f"/v1/service-accounts/{account_id}").status_code == 200
    assert client.get(f"/v1/service-accounts?tenant_id={tenant_id}").json()[0]["id"] == account_id
    assert (
        client.patch(f"/v1/service-accounts/{account_id}", json={"name": "Release agent"}).json()[
            "name"
        ]
        == "Release agent"
    )
    assert (
        client.patch(
            f"/v1/service-accounts/{account_id}",
            json={"tenant_id": "b89e819c-27cb-4c90-82ec-baa868cd529d"},
        ).status_code
        == 422
    )

    created_token = client.post(
        "/v1/tokens",
        json={"service_account_id": account_id, "name": "automation"},
    )

    assert created_token.status_code == 201
    assert created_token.json()["service_account_id"] == account_id
    assert created_token.json()["user_id"] is None
    assert created_token.json()["expires_at"] is None
    token_id = created_token.json()["id"]
    assert client.get(f"/v1/tokens/{token_id}").json()["expires_at"] is None

    assert client.delete(f"/v1/service-accounts/{account_id}").status_code == 204
    assert client.get(f"/v1/tokens/{token_id}").status_code == 404


def test_token_requires_one_owner_and_user_token_expiration():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(
        engine,
        tables=[ApiUser.__table__, ApiServiceAccount.__table__, ApiAccessToken.__table__],
    )
    client = TestClient(
        create_app(sessionmaker(bind=engine, expire_on_commit=False), admin_token=ADMIN_TOKEN),
        headers=ADMIN_HEADERS,
    )
    user_id = client.post("/v1/users", json={"name": "Ada", "email": "ada@example.com"}).json()[
        "id"
    ]

    missing_owner = client.post("/v1/tokens", json={"name": "invalid"})
    missing_user_expiration = client.post(
        "/v1/tokens", json={"user_id": user_id, "name": "invalid"}
    )
    account_id = client.post(
        "/v1/service-accounts",
        json={"name": "Build agent", "tenant_id": "a89e819c-27cb-4c90-82ec-baa868cd529d"},
    ).json()["id"]
    multiple_owners = client.post(
        "/v1/tokens",
        json={
            "user_id": user_id,
            "service_account_id": account_id,
            "name": "invalid",
        },
    )
    missing_service_account = client.post(
        "/v1/tokens",
        json={"service_account_id": "b89e819c-27cb-4c90-82ec-baa868cd529d", "name": "invalid"},
    )

    assert missing_owner.status_code == 422
    assert missing_user_expiration.status_code == 422
    assert multiple_owners.status_code == 422
    assert missing_service_account.status_code == 404
