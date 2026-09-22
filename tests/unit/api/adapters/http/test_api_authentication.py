from datetime import UTC, datetime, timedelta
from hashlib import sha256
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from api.server.app import create_app
from core.infrastructure.postgres.models.api_access_token import ApiAccessToken
from core.infrastructure.postgres.models.api_service_account import ApiServiceAccount
from core.infrastructure.postgres.models.api_user import ApiUser
from core.infrastructure.postgres.models.base import Base
from core.infrastructure.postgres.models.project import Project
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
    return (
        TestClient(create_app(factory, admin_token="admin-secret")),
        plaintext,
        tenant_id,
        factory,
    )


def test_management_routes_require_admin_bearer_token() -> None:
    client, _, _, _ = _client(("memory:read",))

    assert (
        client.post("/v1/users", json={"name": "Ada", "email": "ada@example.com"}).status_code
        == 401
    )
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
        headers={"Authorization": f"Bearer {plaintext}"},
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


def test_user_token_can_publish_for_its_tenant() -> None:
    client, _, tenant_id, factory = _client(("memory:publish",))
    user_id = uuid4()
    token = "hm_user_publish"
    with factory() as session:
        session.add(ApiUser(id=user_id, tenant_id=tenant_id, name="Ada", email="ada@example.com"))
        session.add(ApiAccessToken(id=uuid4(), user_id=user_id, name="publisher",
            token_hash=sha256(token.encode()).hexdigest(), scopes=["memory:publish"],
            expires_at=datetime.now(UTC) + timedelta(days=1)))
        session.commit()
    response = client.post("/v1/knowledge-publications",
        headers={"Authorization": f"Bearer {token}"},
        json={"project_key": "catalog", "environment": "staging", "deployment_id": "user-1",
              "version": "1", "entities": [], "relations": [], "evidence": []})
    assert response.status_code == 201
    with factory() as session:
        assert session.scalar(select(Snapshot.tenant_id)) == tenant_id


def test_admin_publication_requires_tenant_destination_in_body() -> None:
    client, _, tenant_id, factory = _client(("memory:read",))
    payload = {"project_key": "catalog", "environment": "staging", "deployment_id": "admin-1",
               "version": "1", "entities": [], "relations": [], "evidence": []}
    admin = {"Authorization": "Bearer admin-secret"}
    assert client.post("/v1/knowledge-publications", headers=admin, json=payload).status_code == 400
    assert client.post("/v1/knowledge-publications", headers=admin,
        json={**payload, "tenant_id": "invalid"}).status_code == 422
    assert client.post("/v1/knowledge-publications", headers=admin,
        json={**payload, "tenant_id": str(uuid4())}).status_code == 404
    response = client.post("/v1/knowledge-publications", headers=admin,
        json={**payload, "tenant_id": tenant_id})
    assert response.status_code == 201
    with factory() as session:
        assert session.scalar(select(Snapshot.tenant_id)) == tenant_id


def test_read_scope_can_fetch_publication_baseline_but_cannot_publish() -> None:
    client, read_token, tenant_id, _ = _client(("memory:read",))
    params = {"project_key": "catalog", "environment": "staging"}
    response = client.get("/v1/knowledge-publications/latest", params=params,
        headers={"Authorization": f"Bearer {read_token}"})
    assert response.status_code == 404
    admin = {"Authorization": "Bearer admin-secret"}
    assert client.get("/v1/knowledge-publications/latest", params=params,
        headers=admin).status_code == 404


def test_publish_scope_still_reads_baseline_for_incremental_publication() -> None:
    client, token, _, _ = _client(("memory:publish",))
    response = client.get("/v1/knowledge-publications/latest",
        params={"project_key": "catalog", "environment": "staging"},
        headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 404


def test_data_reads_are_tenant_scoped_and_admin_selects_tenant() -> None:
    client, token, tenant_id, _ = _client(("memory:read",))
    headers = {"Authorization": f"Bearer {token}"}
    assert client.get("/v1/tenants/current", headers=headers).json()["id"] == tenant_id
    assert client.get("/v1/projects", headers=headers).json() == []
    assert client.get("/v1/projects/missing", headers=headers).status_code == 404
    assert client.get("/v1/snapshots/" + str(uuid4()), headers=headers).status_code == 404
    admin = {"Authorization": "Bearer admin-secret"}
    assert client.get("/v1/tenants/current", headers=admin).status_code == 400
    assert [item["id"] for item in client.get("/v1/tenants", headers=admin).json()] == [tenant_id]
    assert client.get("/v1/projects", headers=admin).json() == []


def test_ordinary_reads_are_tenant_scoped_and_admin_reads_are_global() -> None:
    client, publisher, tenant_id, factory = _client(("memory:read", "memory:publish"))
    headers = {"Authorization": f"Bearer {publisher}"}
    payload = {"project_key": "catalog", "environment": "staging", "deployment_id": "read-1",
               "version": "1", "entities": [], "relations": [], "evidence": []}
    published = client.post("/v1/knowledge-publications", headers=headers, json=payload)
    assert published.status_code == 201
    snapshot_id = published.json()["snapshot_id"]
    assert client.get("/v1/projects", headers=headers).json()[0]["key"] == "catalog"
    assert client.get("/v1/projects/catalog", headers=headers).json()["key"] == "catalog"
    assert (
        client.get("/v1/projects/catalog/snapshots", headers=headers).json()[0]["id"]
        == snapshot_id
    )
    assert client.get(f"/v1/snapshots/{snapshot_id}", headers=headers).json()["payload"]

    foreign_id = uuid4()
    foreign_project_id = uuid4()
    foreign_snapshot_id = uuid4()
    with factory() as session:
        session.add(Tenant(id=foreign_id, key="foreign", name="Foreign", status="active"))
        session.add(
            Project(
                id=foreign_project_id,
                tenant_id=foreign_id,
                key="foreign",
                name="Foreign",
            )
        )
        session.add(
            Snapshot(
                id=foreign_snapshot_id,
                tenant_id=foreign_id,
                project_id=foreign_project_id,
                revision=1,
                schema_version="1.0",
                payload_hash="f" * 64,
                payload={"tenant": "foreign"},
                metadata_json={},
            )
        )
        session.commit()
    admin_headers = {"Authorization": "Bearer admin-secret"}
    admin_projects = client.get("/v1/projects", headers=admin_headers).json()
    assert {item["key"] for item in admin_projects} == {"catalog", "foreign"}
    assert {item["tenant_id"] for item in admin_projects} == {tenant_id, str(foreign_id)}
    assert client.get(f"/v1/snapshots/{snapshot_id}", headers=admin_headers).status_code == 200
    assert client.get(f"/v1/snapshots/{foreign_snapshot_id}", headers=headers).status_code == 404
    admin_snapshot = client.get(
        f"/v1/snapshots/{foreign_snapshot_id}", headers=admin_headers
    ).json()
    assert admin_snapshot["tenant_id"] == str(foreign_id)


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

    assert (
        client.post("/v1/knowledge-publications", headers=headers, json=payload).status_code
        == 201
    )
    production_payload = {**payload, "environment": "production", "deployment_id": "deploy-2"}
    assert (
        client.post(
            "/v1/knowledge-publications", headers=headers, json=production_payload
        ).status_code
        == 201
    )
    payload["entities"] = [{"key": "changed-api", "type": "service"}]

    assert (
        client.post("/v1/knowledge-publications", headers=headers, json=payload).status_code
        == 409
    )
