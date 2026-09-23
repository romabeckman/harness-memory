from hashlib import sha256
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from api.server.app import create_app
from core.infrastructure.postgres.models.base import Base
from core.infrastructure.postgres.models.entity import Entity
from core.infrastructure.postgres.models.environment import Environment
from core.infrastructure.postgres.models.evidence import Evidence
from core.infrastructure.postgres.models.knowledge_publication import KnowledgePublication
from core.infrastructure.postgres.models.project import Project
from core.infrastructure.postgres.models.relation import Relation
from core.infrastructure.postgres.models.snapshot import Snapshot
from core.infrastructure.postgres.models.tenant import Tenant


def test_read_key_searches_all_knowledge_tables_with_filters() -> None:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    tenant_id = uuid4()
    project_id = uuid4()
    environment_id = uuid4()
    snapshot_id = uuid4()
    entity_id = uuid4()
    target_entity_id = uuid4()
    relation_id = uuid4()
    other_tenant_id = uuid4()
    other_project_id = uuid4()
    other_environment_id = uuid4()
    with Session(engine) as session:
        session.add_all(
            [
                Tenant(id=tenant_id, key="acme", name="Acme", status="active"),
                Tenant(id=other_tenant_id, key="other", name="Other", status="active"),
                Project(id=project_id, tenant_id=tenant_id, key="catalog", name="Catalog"),
                Project(
                    id=other_project_id,
                    tenant_id=other_tenant_id,
                    key="billing",
                    name="Billing",
                ),
            ]
        )
        session.add(
            Environment(
                id=other_environment_id,
                tenant_id=other_tenant_id,
                project_id=other_project_id,
                name="production",
                type="production",
                metadata_json={},
            )
        )
        session.add(
            Snapshot(
                id=snapshot_id,
                tenant_id=tenant_id,
                project_id=project_id,
                environment_id=environment_id,
                revision=9,
                schema_version="1.0",
                payload_hash=sha256(b"catalog").hexdigest(),
                payload={},
                metadata_json={},
            )
        )
        session.add(
            Environment(
                id=environment_id,
                tenant_id=tenant_id,
                project_id=project_id,
                name="production",
                type="production",
                current_snapshot_id=snapshot_id,
                metadata_json={},
            )
        )
        session.add(
            KnowledgePublication(
                id=uuid4(),
                tenant_id=tenant_id,
                project_id=project_id,
                environment_id=environment_id,
                deployment_id="deploy-9",
                version="v9.0",
                status="SUCCEEDED",
                snapshot_id=snapshot_id,
                metadata_json={},
            )
        )
        session.add_all(
            [
                Entity(
                    id=entity_id,
                    tenant_id=tenant_id,
                    project_id=project_id,
                    snapshot_id=snapshot_id,
                    entity_key="catalog-api",
                    entity_type="service",
                    name="Catalog API",
                    metadata_json={},
                ),
                Entity(
                    id=target_entity_id,
                    tenant_id=tenant_id,
                    project_id=project_id,
                    snapshot_id=snapshot_id,
                    entity_key="catalog-db",
                    entity_type="database",
                    name="Catalog Database",
                    metadata_json={},
                ),
            ]
        )
        session.add(
            Relation(
                id=relation_id,
                tenant_id=tenant_id,
                snapshot_id=snapshot_id,
                source_entity_id=entity_id,
                target_entity_id=target_entity_id,
                relation_type="uses",
                provenance_kind="declared",
                metadata_json={},
            )
        )
        session.add(
            Evidence(
                id=uuid4(),
                tenant_id=tenant_id,
                snapshot_id=snapshot_id,
                relation_id=relation_id,
                source="docs/architecture.md",
                excerpt="Catalog API uses Catalog Database",
                metadata_json={},
            )
        )
        session.commit()

    client = TestClient(
        create_app(factory, admin_token="admin-secret", read_api_key="global-read-secret")
    )
    headers = {"Authorization": "Bearer global-read-secret"}

    environments = client.get(
        "/v1/environments", params={"project_key": "catalog", "name": "production"},
        headers=headers,
    )
    publications = client.get(
        "/v1/knowledge-publications",
        params={"project_key": "catalog", "status": "SUCCEEDED", "version": "v9.0"},
        headers=headers,
    )
    snapshots = client.get(
        "/v1/snapshots", params={"project_key": "catalog", "revision": 9}, headers=headers
    )
    entities = client.get(
        "/v1/entities",
        params={"project_key": "catalog", "entity_type": "service", "q": "Catalog API"},
        headers=headers,
    )
    relations = client.get(
        "/v1/relations",
        params={"project_key": "catalog", "relation_type": "uses",
                "provenance_kind": "declared"},
        headers=headers,
    )
    evidence = client.get(
        "/v1/evidence",
        params={"snapshot_id": str(snapshot_id), "q": "Catalog Database"}, headers=headers,
    )

    assert environments.status_code == 200
    assert environments.json()[0]["name"] == "production"
    assert publications.status_code == 200
    assert publications.json()[0]["deployment_id"] == "deploy-9"
    assert snapshots.status_code == 200
    assert snapshots.json()[0]["revision"] == 9
    assert entities.status_code == 200
    assert [item["entity_key"] for item in entities.json()] == ["catalog-api"]
    assert relations.status_code == 200
    assert relations.json()[0]["relation_type"] == "uses"
    assert evidence.status_code == 200
    assert evidence.json()[0]["source"] == "docs/architecture.md"

    tenants = client.get("/v1/tenants", headers=headers)
    assert {item["id"] for item in tenants.json()} == {
        str(tenant_id), str(other_tenant_id)
    }
    first_page = client.get(
        "/v1/environments", params={"type": "production", "limit": 1}, headers=headers
    )
    second_page = client.get(
        "/v1/environments",
        params={"type": "production", "limit": 1, "offset": 1},
        headers=headers,
    )
    assert len(first_page.json()) == len(second_page.json()) == 1
    assert first_page.json()[0]["id"] != second_page.json()[0]["id"]


def test_data_search_supports_pagination_and_rejects_write_methods() -> None:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    client = TestClient(
        create_app(factory, admin_token="admin-secret", read_api_key="global-read-secret")
    )

    response = client.get(
        "/v1/entities", params={"limit": 0},
        headers={"Authorization": "Bearer global-read-secret"},
    )

    assert response.status_code == 422
