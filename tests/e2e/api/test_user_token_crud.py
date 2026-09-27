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
    Base.metadata.create_all(engine)
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
    Base.metadata.create_all(engine)
    client = TestClient(
        create_app(sessionmaker(bind=engine, expire_on_commit=False), admin_token=ADMIN_TOKEN),
        headers=ADMIN_HEADERS,
    )

    user_payload = {"name": "Ada", "email": "ada@example.com"}
    assert client.post("/users", json=user_payload).status_code == 404
    created_user = client.post("/v1/users", json=user_payload)
    assert created_user.status_code == 201
    user_id = created_user.json()["id"]
    assert client.get("/v1/tenants").json() == []
    assert client.get("/v1/projects").json() == []
    assert client.get(f"/v1/users/{user_id}").status_code == 200
    assert (
        client.patch(f"/v1/users/{user_id}", json={"name": "Ada Lovelace"}).json()["name"]
        == "Ada Lovelace"
    )

    tenant_id = client.post("/v1/tenants", json={"key": "platform", "name": "Platform"}).json()[
        "id"
    ]
    client.post("/v1/projects", json={"tenant_id": tenant_id, "key": "backend", "name": "Backend"})
    expires_at = (datetime.now(UTC) + timedelta(days=30)).isoformat()
    created_token = client.post(
        "/v1/tokens",
        json={
            "user_id": user_id,
            "name": "agent",
            "expires_at": expires_at,
            "project_keys": ["backend"],
        },
    )
    assert created_token.status_code == 201
    assert created_token.json()["token"].startswith("hm_")
    assert created_token.json()["project_keys"] == ["backend"]
    assert (
        client.get(
            "/v1/projects",
            headers={"Authorization": f"Bearer {created_token.json()['token']}"},
        ).status_code
        == 200
    )
    token_id = created_token.json()["id"]
    assert client.get(f"/v1/tokens/{token_id}").status_code == 200
    assert (
        client.patch(f"/v1/tokens/{token_id}", json={"name": "renamed"}).json()["name"] == "renamed"
    )
    assert client.delete(f"/v1/tokens/{token_id}").status_code == 204
    assert client.delete(f"/v1/users/{user_id}").status_code == 204


def test_http_accepts_one_year_user_token_and_rejects_longer_lifetime():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    client = TestClient(
        create_app(sessionmaker(bind=engine, expire_on_commit=False), admin_token=ADMIN_TOKEN),
        headers=ADMIN_HEADERS,
    )
    user_id = client.post("/v1/users", json={"name": "Ada", "email": "ada@example.com"}).json()[
        "id"
    ]

    accepted = client.post(
        "/v1/tokens",
        json={
            "user_id": user_id,
            "name": "agent",
            "project_keys": [],
            "expires_at": (datetime.now(UTC) + timedelta(days=365)).isoformat(),
        },
    )
    response = client.post(
        "/v1/tokens",
        json={
            "user_id": user_id,
            "name": "too-long",
            "project_keys": [],
            "expires_at": (datetime.now(UTC) + timedelta(days=366)).isoformat(),
        },
    )

    assert accepted.status_code == 201
    assert response.status_code == 422


def test_service_account_crud_issues_non_expiring_token():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    client = TestClient(
        create_app(sessionmaker(bind=engine, expire_on_commit=False), admin_token=ADMIN_TOKEN),
        headers=ADMIN_HEADERS,
    )
    tenant_resp = client.post("/v1/tenants", json={"key": "build-tenant", "name": "Build Tenant"})
    assert tenant_resp.status_code == 201
    tenant_id = tenant_resp.json()["id"]
    proj_resp = client.post(
        "/v1/projects",
        json={"tenant_id": tenant_id, "key": "automation-proj", "name": "Automation Project"},
    )
    assert proj_resp.status_code == 201

    created = client.post(
        "/v1/service-accounts",
        json={"name": "Build agent", "tenant_id": tenant_id},
    )

    assert created.status_code == 201
    account_id = created.json()["id"]
    assert created.json()["tenant_id"] == tenant_id
    assert len(client.get("/v1/tenants").json()) == 1
    assert [project["key"] for project in client.get("/v1/projects").json()] == ["automation-proj"]
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
        json={
            "service_account_id": account_id,
            "name": "automation",
            "project_keys": ["automation-proj"],
        },
    )

    assert created_token.status_code == 201
    assert created_token.json()["service_account_id"] == account_id
    assert created_token.json()["user_id"] is None
    assert created_token.json()["expires_at"] is None
    assert created_token.json()["project_keys"] == ["automation-proj"]
    token_id = created_token.json()["id"]
    assert client.get(f"/v1/tokens/{token_id}").json()["expires_at"] is None

    assert client.delete(f"/v1/service-accounts/{account_id}").status_code == 204
    assert client.get(f"/v1/tokens/{token_id}").status_code == 404


def test_token_requires_one_owner_and_user_token_expiration():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    client = TestClient(
        create_app(sessionmaker(bind=engine, expire_on_commit=False), admin_token=ADMIN_TOKEN),
        headers=ADMIN_HEADERS,
    )
    tenant_resp = client.post("/v1/tenants", json={"key": "t-owner", "name": "Owner Tenant"})
    tenant_id = tenant_resp.json()["id"]
    user_id = client.post("/v1/users", json={"name": "Ada", "email": "ada@example.com"}).json()[
        "id"
    ]

    missing_owner = client.post("/v1/tokens", json={"name": "invalid", "project_keys": ["backend"]})
    missing_user_expiration = client.post(
        "/v1/tokens", json={"user_id": user_id, "name": "invalid", "project_keys": ["backend"]}
    )
    account_id = client.post(
        "/v1/service-accounts",
        json={"name": "Build agent", "tenant_id": tenant_id},
    ).json()["id"]
    multiple_owners = client.post(
        "/v1/tokens",
        json={
            "user_id": user_id,
            "service_account_id": account_id,
            "name": "invalid",
            "project_keys": ["backend"],
        },
    )
    missing_service_account = client.post(
        "/v1/tokens",
        json={
            "service_account_id": "b89e819c-27cb-4c90-82ec-baa868cd529d",
            "name": "invalid",
            "project_keys": ["backend"],
        },
    )

    missing_projects = client.post(
        "/v1/tokens",
        json={
            "user_id": user_id,
            "name": "invalid",
            "expires_at": (datetime.now(UTC) + timedelta(days=1)).isoformat(),
            "project_keys": [],
        },
    )

    assert missing_owner.status_code == 422
    assert missing_user_expiration.status_code == 422
    assert multiple_owners.status_code == 422
    assert missing_service_account.status_code == 404
    assert missing_projects.status_code == 201
    assert missing_projects.json()["project_keys"] == ["*"]


def test_deleting_user_cascades_all_owned_tokens_over_rest():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    client = TestClient(
        create_app(sessionmaker(bind=engine, expire_on_commit=False), admin_token=ADMIN_TOKEN),
        headers=ADMIN_HEADERS,
    )
    user_response = client.post("/v1/users", json={"name": "Ada", "email": "ada@example.com"})
    assert user_response.status_code == 201
    user_id = user_response.json()["id"]
    assert set(user_response.json()) == {"id", "name", "email"}
    assert client.get(f"/v1/tenants/{user_id}").status_code == 404

    token_ids = []
    for token_name in ("reader", "publisher"):
        token_response = client.post(
            "/v1/tokens",
            json={
                "user_id": user_id,
                "name": token_name,
                "scopes": ["memory:read"],
                "project_keys": [],
                "expires_at": (datetime.now(UTC) + timedelta(days=30)).isoformat(),
            },
        )
        assert token_response.status_code == 201
        token_ids.append(token_response.json()["id"])

    assert client.delete(f"/v1/users/{user_id}").status_code == 204
    assert client.get(f"/v1/users/{user_id}").status_code == 404
    assert all(client.get(f"/v1/tokens/{token_id}").status_code == 404 for token_id in token_ids)
