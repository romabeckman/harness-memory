from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.adapters.http.knowledge_publication_routes import (
    create_knowledge_publication_router,
)
from core.application.knowledge_publication.use_cases.publish_knowledge.outbound import (
    PublishKnowledgeOutput,
)
from core.domain.knowledge_publication.types.publication_status import PublicationStatus
from core.domain.tenant_security.value_objects.authenticated_principal import AuthenticatedPrincipal


def authenticated_principal() -> AuthenticatedPrincipal:
    return AuthenticatedPrincipal("pipeline", "tenant-a", frozenset({"memory:publish"}))


class FakePublishKnowledgeHandler:
    def __init__(self, output: PublishKnowledgeOutput) -> None:
        self.output = output
        self.received_input = None

    def execute(self, input_data):
        self.received_input = input_data
        return self.output


class TestKnowledgePublicationRoutes:
    def test_publishes_new_knowledge_returns_201_activated(self) -> None:
        pub_id = uuid4()
        snap_id = uuid4()
        handler = FakePublishKnowledgeHandler(
            PublishKnowledgeOutput(
                publication_id=pub_id,
                snapshot_id=snap_id,
                status=PublicationStatus.COMPLETED,
            )
        )
        app = FastAPI()
        app.include_router(
            create_knowledge_publication_router(handler, authenticated_principal), prefix="/v1"
        )
        client = TestClient(app)

        response = client.post(
            "/v1/knowledge-publications",
            json={
                "project_key": "catalog",
                "environment": "staging",
                "deployment_id": "deploy-1",
                "version": "1.0.0",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "ACTIVATED"
        assert data["publication_id"] == str(pub_id)
        assert data["snapshot_id"] == str(snap_id)
        assert handler.received_input.tenant_id == "tenant-a"

    def test_idempotent_retry_returns_200_already_published(self) -> None:
        pub_id = uuid4()
        snap_id = uuid4()
        handler = FakePublishKnowledgeHandler(
            PublishKnowledgeOutput(
                publication_id=pub_id,
                snapshot_id=snap_id,
                status=PublicationStatus.ALREADY_PUBLISHED,
            )
        )
        app = FastAPI()
        app.include_router(
            create_knowledge_publication_router(handler, authenticated_principal), prefix="/v1"
        )
        client = TestClient(app)

        response = client.post(
            "/v1/knowledge-publications",
            json={
                "project_key": "catalog",
                "environment": "staging",
                "deployment_id": "deploy-1",
                "version": "1.0.0",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ALREADY_PUBLISHED"
        assert data["publication_id"] == str(pub_id)
        assert data["snapshot_id"] == str(snap_id)

    def test_ordinary_publisher_ignores_body_tenant_override(self) -> None:
        pub_id = uuid4()
        snap_id = uuid4()
        handler = FakePublishKnowledgeHandler(
            PublishKnowledgeOutput(
                publication_id=pub_id,
                snapshot_id=snap_id,
                status=PublicationStatus.COMPLETED,
            )
        )
        app = FastAPI()
        app.include_router(
            create_knowledge_publication_router(handler, authenticated_principal), prefix="/v1"
        )
        client = TestClient(app)

        response = client.post(
            "/v1/knowledge-publications",
            json={
                "project_key": "catalog",
                "environment": "staging",
                "deployment_id": "deploy-1",
                "version": "1.0.0",
                "metadata": {"nodes": [{"id": "feature:orders"}], "edges": []},
                "tenant_id": str(uuid4()),
            },
        )
        assert response.status_code == 201
        assert handler.received_input.tenant_id == "tenant-a"
        assert handler.received_input.metadata == {"nodes": [{"id": "feature:orders"}], "edges": []}
