from hashlib import sha256
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from api.server.app import create_app
from core.infrastructure.postgres.models.api_access_token import ApiAccessToken
from core.infrastructure.postgres.models.api_service_account import ApiServiceAccount
from core.infrastructure.postgres.models.base import Base
from core.infrastructure.postgres.models.snapshot import Snapshot


from core.infrastructure.postgres.models.tenant import Tenant


def _client(scopes: tuple[str, ...]) -> tuple[TestClient, str, str, sessionmaker]:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    tenant_uuid = uuid4()
    tenant_id = str(tenant_uuid)
    plaintext = "hm_publication_secret"
    account_id = uuid4()
    with Session(engine) as session:
        session.add(
            Tenant(
                id=tenant_uuid,
                key=f"tenant-{tenant_uuid.hex[:8]}",
                name="Test Tenant",
                status="active",
            )
        )
        session.add(ApiServiceAccount(id=account_id, tenant_id=tenant_uuid, name="pipeline"))
        session.add(
            ApiAccessToken(
                id=uuid4(),
                service_account_id=account_id,
                name="pipeline",
                token_hash=sha256(plaintext.encode()).hexdigest(),
                expires_at=None,
                scopes=list(scopes),
            )
        )
        session.commit()
    return TestClient(create_app(factory, admin_token="admin-secret")), plaintext, tenant_id, factory


def test_management_routes_require_admin_bearer_token() -> None:
    client, _, _, _ = _client(("memory:read",))

    assert client.post("/v1/users", json={"name": "Ada", "email": "ada@example.com"}).status_code == 401
    assert (
        client.post(
            "/v1/users",
            json={"name": "Ada", "email": "ada@example.com"},
            headers={"Authorization": "Bearer wrong"},
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/v1/users",
            json={"name": "Ada", "email": "ada@example.com"},
            headers={"Authorization": "Bearer admin-secret"},
        ).status_code
        == 201
    )


def test_publication_derives_tenant_from_publish_token_and_provisions_environment() -> None:
    client, plaintext, tenant_id, factory = _client(("memory:publish",))

    response = client.post(
        "/v1/knowledge-publications",
        headers={
            "Authorization": f"Bearer {plaintext}",
            "X-Tenant-ID": "spoofed-tenant",
        },
        json={
            "project_key": "catalog",
            "environment": "staging",
            "deployment_id": "deploy-1",
            "version": "1.0.0",
            "entities": [{"key": "catalog-api", "type": "service", "name": "Catalog API"}],
            "relations": [],
            "evidence": [{"source": "git:abc123", "excerpt": "deployed"}],
        },
    )

    assert response.status_code == 201
    with factory() as session:
        assert session.scalar(select(Snapshot.tenant_id)) == tenant_id


def test_publication_rejects_missing_scope_and_invalid_fact_type() -> None:
    read_client, read_token, _, _ = _client(("memory:read",))
    payload = {
        "project_key": "catalog",
        "environment": "staging",
        "deployment_id": "deploy-1",
        "version": "1",
        "entities": [],
        "relations": [],
        "evidence": [],
    }

    assert (
        read_client.post(
            "/v1/knowledge-publications",
            headers={"Authorization": f"Bearer {read_token}"},
            json=payload,
        ).status_code
        == 403
    )

    publish_client, publish_token, _, _ = _client(("memory:publish",))
    payload["entities"] = [{"key": "catalog-api", "type": "typo"}]
    assert (
        publish_client.post(
            "/v1/knowledge-publications",
            headers={"Authorization": f"Bearer {publish_token}"},
            json=payload,
        ).status_code
        == 422
    )


def test_publication_allows_same_version_across_environments_and_rejects_changed_retry() -> None:
    client, token, _, _ = _client(("memory:publish",))
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "project_key": "catalog",
        "environment": "staging",
        "deployment_id": "deploy-1",
        "version": "1.0.0",
        "entities": [{"key": "catalog-api", "type": "service"}],
        "relations": [],
        "evidence": [{"source": "git:abc123", "excerpt": "deployed"}],
    }

    assert client.post("/v1/knowledge-publications", headers=headers, json=payload).status_code == 201
    production_payload = {**payload, "environment": "production", "deployment_id": "deploy-2"}
    assert (
        client.post("/v1/knowledge-publications", headers=headers, json=production_payload).status_code
        == 201
    )
    payload["entities"] = [{"key": "changed-api", "type": "service"}]

    assert client.post("/v1/knowledge-publications", headers=headers, json=payload).status_code == 409
