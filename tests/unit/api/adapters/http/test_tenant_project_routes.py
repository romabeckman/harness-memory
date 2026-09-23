from hashlib import sha256
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from api.server.app import create_app
from core.infrastructure.postgres.models.api_access_token import ApiAccessToken
from core.infrastructure.postgres.models.api_service_account import ApiServiceAccount
from core.infrastructure.postgres.models.base import Base
from core.infrastructure.postgres.models.tenant import Tenant


def _client(
    *, include_reader: bool = True, read_api_key: str | None = None
) -> tuple[TestClient, str, str | None]:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    tenant_id = uuid4()
    token = "database-read-token"
    with Session(engine) as session:
        session.add(Tenant(id=tenant_id, key="tenant-a", name="Tenant A", status="active"))
        if include_reader:
            account_id = uuid4()
            session.add(ApiServiceAccount(id=account_id, tenant_id=tenant_id, name="reader"))
            session.add(ApiAccessToken(
                id=uuid4(),
                service_account_id=account_id,
                name="read-only",
                token_hash=sha256(token.encode()).hexdigest(),
                scopes=["memory:read"],
            ))
        session.commit()
    return (
        TestClient(
            create_app(factory, admin_token="admin-secret", read_api_key=read_api_key)
        ),
        str(tenant_id),
        token if include_reader else None,
    )


def test_admin_can_create_read_update_and_delete_tenants_and_projects() -> None:
    client, tenant_id, _ = _client(include_reader=False)
    admin = {"Authorization": "Bearer admin-secret"}

    tenant_response = client.post(
        "/v1/tenants", headers=admin,
        json={"key": "tenant-b", "name": "Tenant B", "metadata": {"region": "west"}},
    )
    assert tenant_response.status_code == 201
    created_tenant = tenant_response.json()
    assert client.get(f"/v1/tenants/{created_tenant['id']}", headers=admin).status_code == 200
    updated_tenant = client.patch(
        f"/v1/tenants/{created_tenant['id']}", headers=admin,
        json={"name": "Tenant B Updated", "status": "disabled"},
    )
    assert updated_tenant.status_code == 200
    assert updated_tenant.json()["name"] == "Tenant B Updated"
    assert client.delete(f"/v1/tenants/{created_tenant['id']}", headers=admin).status_code == 204
    assert client.get(f"/v1/tenants/{created_tenant['id']}", headers=admin).status_code == 404

    project_response = client.post(
        "/v1/projects", headers=admin,
        json={"tenant_id": tenant_id, "key": "catalog", "name": "Catalog",
              "metadata": {"owner": "platform"}},
    )
    assert project_response.status_code == 201
    assert project_response.json()["key"] == "catalog"
    found_project = client.get("/v1/projects/catalog", params={"tenant_id": tenant_id},
                               headers=admin)
    assert found_project.status_code == 200
    assert found_project.json()["metadata"] == {"owner": "platform"}
    updated_project = client.patch(
        "/v1/projects/catalog", params={"tenant_id": tenant_id}, headers=admin,
        json={"name": "Catalog API", "metadata": {"owner": "infra"}},
    )
    assert updated_project.status_code == 200
    assert updated_project.json()["name"] == "Catalog API"
    assert client.delete("/v1/projects/catalog", params={"tenant_id": tenant_id},
                         headers=admin).status_code == 204
    assert client.get("/v1/projects/catalog", params={"tenant_id": tenant_id},
                      headers=admin).status_code == 404


def test_database_read_token_gets_tenant_reads_only() -> None:
    client, tenant_id, token = _client()
    assert token is not None
    reader = {"Authorization": f"Bearer {token}"}

    tenants = client.get("/v1/tenants", headers=reader)
    assert tenants.status_code == 200
    assert [tenant["id"] for tenant in tenants.json()] == [tenant_id]
    assert client.get("/v1/tenants/current", headers=reader).status_code == 200
    assert client.get("/v1/projects", headers=reader).status_code == 200
    assert client.get("/v1/snapshots/" + str(uuid4()), headers=reader).status_code == 404
    assert client.post(
        "/v1/tenants", headers=reader, json={"key": "blocked", "name": "Blocked"}
    ).status_code == 403
    assert client.patch(
        "/v1/tenants/" + tenant_id, headers=reader, json={"name": "Blocked"}
    ).status_code == 403
    assert client.delete("/v1/tenants/" + tenant_id, headers=reader).status_code == 403
    assert client.post(
        "/v1/projects", headers=reader,
        json={"tenant_id": tenant_id, "key": "blocked"},
    ).status_code == 403
    assert client.patch(
        "/v1/projects/blocked", params={"tenant_id": tenant_id}, headers=reader,
        json={"name": "Blocked"},
    ).status_code == 403
    assert client.delete(
        "/v1/projects/blocked", params={"tenant_id": tenant_id}, headers=reader
    ).status_code == 403
    assert client.post("/v1/knowledge-publications", headers=reader, json={}).status_code == 403


def test_harness_memory_api_key_has_global_read_scope_only(monkeypatch) -> None:
    monkeypatch.setenv("HARNESS_MEMORY_API_KEY", "global-read-secret")
    client, tenant_id, _ = _client()
    reader = {"Authorization": "Bearer global-read-secret"}

    tenants = client.get("/v1/tenants", headers=reader)
    assert tenants.status_code == 200
    assert [item["id"] for item in tenants.json()] == [tenant_id]
    assert client.get("/v1/tenants/current", headers=reader).status_code == 400
    assert client.get("/v1/projects", headers=reader).status_code == 200
    assert client.post(
        "/v1/tenants", headers=reader, json={"key": "blocked", "name": "Blocked"}
    ).status_code == 403
    assert client.get("/v1/users", headers=reader).status_code == 403
    assert client.post("/v1/knowledge-publications", headers=reader, json={}).status_code == 403


def test_tenant_delete_requires_projects_to_be_removed_first() -> None:
    client, tenant_id, _ = _client(include_reader=False)
    admin = {"Authorization": "Bearer admin-secret"}
    project = client.post(
        "/v1/projects", headers=admin,
        json={"tenant_id": tenant_id, "key": "catalog", "name": "Catalog"},
    )
    assert project.status_code == 201
    assert client.delete(f"/v1/tenants/{tenant_id}", headers=admin).status_code == 409
    assert client.delete("/v1/projects/catalog", params={"tenant_id": tenant_id},
                         headers=admin).status_code == 204
    assert client.delete(f"/v1/tenants/{tenant_id}", headers=admin).status_code == 204


def test_snapshots_remain_read_only_even_for_admin() -> None:
    client, _, _ = _client()
    admin = {"Authorization": "Bearer admin-secret"}
    snapshot_id = str(uuid4())

    assert client.post(f"/v1/snapshots/{snapshot_id}", headers=admin, json={}).status_code == 405
    assert client.patch(f"/v1/snapshots/{snapshot_id}", headers=admin, json={}).status_code == 405
    assert client.delete(f"/v1/snapshots/{snapshot_id}", headers=admin).status_code == 405
    assert client.put(f"/v1/snapshots/{snapshot_id}", headers=admin, json={}).status_code == 405
