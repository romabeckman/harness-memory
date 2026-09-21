from uuid import UUID, uuid4

from core.application.knowledge_publication.use_cases.publish_knowledge.handler import (
    PublishKnowledgeHandler,
)
from core.application.knowledge_publication.use_cases.publish_knowledge.inbound import (
    PublishKnowledgeInput,
)
from core.domain.environment.aggregates.environment import Environment
from core.domain.environment.value_objects.environment_name import EnvironmentName
from core.domain.knowledge_publication.aggregates.knowledge_publication import (
    KnowledgePublication,
)
from core.domain.knowledge_publication.types.publication_status import PublicationStatus
from core.domain.knowledge_publication.value_objects.deployment_id import DeploymentId
from core.domain.knowledge_publication.value_objects.publication_id import PublicationId
from core.domain.snapshot_publication.aggregates.project_knowledge_snapshot import (
    ProjectKnowledgeSnapshot,
)
from core.domain.snapshot_publication.value_objects.project_key import ProjectKey


class FakeEnvironmentRepository:
    def __init__(self, environments: list[Environment] | None = None) -> None:
        self.environments: dict[tuple[str, str, str], Environment] = {
            (env.project_key.value, env.name.value, "default"): env for env in (environments or [])
        }
        self.promotions: list[tuple[UUID, UUID, str]] = []

    def resolve(self, project_key: str, name: str, tenant_id: str) -> Environment | None:
        key = (project_key, name, tenant_id)
        if key not in self.environments:
            env = Environment(
                id=uuid4(),
                project_key=ProjectKey(project_key),
                name=EnvironmentName(name),
            )
            self.environments[key] = env
        return self.environments[key]

    def promote_active_snapshot(self, env_id: UUID, snap_id: UUID, tenant_id: str) -> None:
        self.promotions.append((env_id, snap_id, tenant_id))
        for env in self.environments.values():
            if env.id == env_id:
                env.promote_snapshot(snap_id)


class FakeKnowledgePublicationRepository:
    def __init__(
        self,
        publications: list[KnowledgePublication] | None = None,
        env_repo: FakeEnvironmentRepository | None = None,
    ) -> None:
        self.publications: dict[tuple[str, str, str, str], KnowledgePublication] = {
            (pub.project_key.value, pub.environment_name.value, pub.deployment_id.value, "default"): pub
            for pub in (publications or [])
        }
        self.saved: list[KnowledgePublication] = []
        self.published_snapshots: list[ProjectKnowledgeSnapshot] = []
        self._env_repo = env_repo

    def find_by_deployment(
        self, project_key: str, env_name: str, deployment_id: str, tenant_id: str
    ) -> KnowledgePublication | None:
        return self.publications.get((project_key, env_name, deployment_id, tenant_id))

    def save(self, publication: KnowledgePublication, tenant_id: str) -> None:
        key = (
            publication.project_key.value,
            publication.environment_name.value,
            publication.deployment_id.value,
            tenant_id,
        )
        self.publications[key] = publication
        self.saved.append(publication)

    def publish_atomically_with_environment(
        self,
        tenant_id: str,
        publication: KnowledgePublication,
        snapshot: ProjectKnowledgeSnapshot,
        environment_id: UUID,
    ) -> UUID:
        snap_id = uuid4()
        publication.complete(snap_id)
        self.published_snapshots.append(snapshot)
        self.save(publication, tenant_id)
        if self._env_repo:
            self._env_repo.promote_active_snapshot(environment_id, snap_id, tenant_id)
        return snap_id


class TestPublishKnowledge:
    def test_returns_already_published_for_idempotent_retry(self) -> None:
        existing_snapshot_id = uuid4()
        pub = KnowledgePublication(
            id=PublicationId.generate(),
            project_key=ProjectKey("catalog"),
            environment_name=EnvironmentName("staging"),
            deployment_id=DeploymentId("deploy-100"),
            version="1.0.0",
            status=PublicationStatus.COMPLETED,
            snapshot_id=existing_snapshot_id,
        )
        env_repo = FakeEnvironmentRepository()
        pub_repo = FakeKnowledgePublicationRepository([pub], env_repo=env_repo)
        handler = PublishKnowledgeHandler(
            publication_repository=pub_repo,
            environment_repository=env_repo,
        )

        input_data = PublishKnowledgeInput(
            project_key="catalog",
            environment_name="staging",
            deployment_id="deploy-100",
            version="1.0.0",
            tenant_id="default",
        )
        output = handler.execute(input_data)

        assert output.status == PublicationStatus.ALREADY_PUBLISHED
        assert output.snapshot_id == existing_snapshot_id
        assert len(env_repo.promotions) == 0

    def test_publishes_new_knowledge_and_promotes_environment_with_facts(self) -> None:
        env_repo = FakeEnvironmentRepository()
        pub_repo = FakeKnowledgePublicationRepository(env_repo=env_repo)
        handler = PublishKnowledgeHandler(
            publication_repository=pub_repo,
            environment_repository=env_repo,
        )

        input_data = PublishKnowledgeInput(
            project_key="catalog",
            environment_name="staging",
            deployment_id="deploy-101",
            version="1.1.0",
            tenant_id="default",
            entities=(
                {"key": "catalog-api", "type": "service", "name": "Catalog API"},
                {"key": "db", "type": "service", "name": "Database"},
            ),
            relations=(
                {
                    "ref": "rel-1",
                    "source_entity_key": "catalog-api",
                    "type": "calls",
                    "target_entity_key": "db",
                    "provenance": "verified",
                },
            ),
        )
        output = handler.execute(input_data)

        assert output.status == PublicationStatus.COMPLETED
        assert isinstance(output.snapshot_id, UUID)
        assert len(pub_repo.saved) == 1
        assert len(env_repo.promotions) == 1
        assert len(pub_repo.published_snapshots) == 1
        created_snap = pub_repo.published_snapshots[0]
        assert len(created_snap.entities) == 2
        assert created_snap.entities[0].key.value == "catalog-api"
        assert len(created_snap.relations) == 1
        assert created_snap.relations[0].target_entity_key.value == "db"
