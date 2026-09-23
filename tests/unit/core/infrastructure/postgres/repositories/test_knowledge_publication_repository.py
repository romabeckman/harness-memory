from datetime import datetime, timezone
from unittest.mock import Mock
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from core.application.knowledge_publication.use_cases.publish_knowledge.handler import PublishKnowledgeHandler
from core.application.knowledge_publication.use_cases.publish_knowledge.inbound import PublishKnowledgeInput
from core.domain.environment.value_objects.environment_name import EnvironmentName
from core.domain.knowledge_publication.aggregates.knowledge_publication import (
    KnowledgePublication as DomainKnowledgePublication,
)
from core.domain.knowledge_publication.types.publication_status import PublicationStatus
from core.domain.knowledge_publication.value_objects.deployment_id import DeploymentId
from core.domain.knowledge_publication.value_objects.publication_id import PublicationId
from core.domain.snapshot_publication.aggregates.project_knowledge_snapshot import (
    ProjectKnowledgeSnapshot,
)
from core.domain.snapshot_publication.errors.revision_conflict import RevisionConflict
from core.domain.snapshot_publication.value_objects.generated_at import GeneratedAt
from core.domain.snapshot_publication.value_objects.metadata_object import MetadataObject
from core.domain.snapshot_publication.value_objects.project_key import ProjectKey
from core.domain.snapshot_publication.value_objects.revision import Revision
from core.domain.snapshot_publication.value_objects.schema_version import SchemaVersion
from core.infrastructure.postgres.models.base import Base
from core.infrastructure.postgres.models.environment import Environment as ModelEnvironment
from core.infrastructure.postgres.models.project import Project as ModelProject
from core.infrastructure.postgres.models.snapshot import Snapshot as ModelSnapshot
from core.infrastructure.postgres.repositories.knowledge_publication_repository import (
    PostgresKnowledgePublicationRepository,
)
from core.infrastructure.postgres.repositories.environment_repository import PostgresEnvironmentRepository


def _seed_project_and_env(engine, tenant_id: str, proj_key: str, env_name: str) -> tuple:
    with Session(engine) as session:
        proj = ModelProject(
            id=uuid4(),
            tenant_id=tenant_id,
            key=proj_key,
            name=proj_key,
        )
        session.add(proj)
        session.commit()
        session.refresh(proj)

        env = ModelEnvironment(
            id=uuid4(),
            tenant_id=tenant_id,
            project_id=proj.id,
            name=env_name,
            type=env_name,
        )
        session.add(env)
        session.commit()
        session.refresh(env)
        return proj, env


class TestPostgresKnowledgePublicationRepository:
    def test_postgres_publication_uses_read_committed_for_revision_locking(self) -> None:
        engine = Mock()
        engine.dialect.name = "postgresql"
        write_engine = Mock()
        engine.execution_options.return_value = write_engine

        repository = PostgresKnowledgePublicationRepository(engine=engine)

        engine.execution_options.assert_called_once_with(isolation_level="READ COMMITTED")
        assert repository._session_factory.kw["bind"] is write_engine

    def test_distinct_deployments_of_same_version_keep_separate_snapshots(self) -> None:
        engine = create_engine("sqlite://")
        Base.metadata.create_all(engine)
        _seed_project_and_env(engine, "tenant-a", "catalog", "staging")
        repository = PostgresKnowledgePublicationRepository(engine=engine)
        handler = PublishKnowledgeHandler(repository, PostgresEnvironmentRepository(engine=engine))
        first_request = PublishKnowledgeInput(
            "catalog", "staging", "deploy-1", "1.2.3", tenant_id="tenant-a",
            metadata={"generation": 1},
        )
        second_request = PublishKnowledgeInput(
            "catalog", "staging", "deploy-2", "1.2.3", tenant_id="tenant-a",
            metadata={"generation": 2},
        )

        first = handler.execute(first_request)
        second = handler.execute(second_request)
        retry = handler.execute(second_request)

        assert first.snapshot_id != second.snapshot_id
        assert retry.snapshot_id == second.snapshot_id
        assert retry.status == PublicationStatus.ALREADY_PUBLISHED
        with pytest.raises(RevisionConflict, match="deployment identity"):
            handler.execute(PublishKnowledgeInput(
                "catalog", "staging", "deploy-2", "1.2.3", tenant_id="tenant-a",
                metadata={"generation": 3},
            ))
        with Session(engine) as session:
            snapshots = session.query(ModelSnapshot).all()
            assert len(snapshots) == 2
            assert len({snapshot.revision for snapshot in snapshots}) == 2

    def test_saves_and_finds_publication_by_deployment(self) -> None:
        engine = create_engine("sqlite://")
        Base.metadata.create_all(engine)
        _seed_project_and_env(engine, "tenant-a", "catalog", "staging")

        repo = PostgresKnowledgePublicationRepository(engine=engine)
        pub_id = PublicationId.generate()
        snap_id = uuid4()
        pub = DomainKnowledgePublication(
            id=pub_id,
            project_key=ProjectKey("catalog"),
            environment_name=EnvironmentName("staging"),
            deployment_id=DeploymentId("deploy-500"),
            version="2.0.0",
            status=PublicationStatus.COMPLETED,
            snapshot_id=snap_id,
        )

        repo.save(pub, tenant_id="tenant-a")

        found = repo.find_by_deployment("catalog", "staging", "deploy-500", tenant_id="tenant-a")
        assert found is not None
        assert found.id == pub_id
        assert found.version == "2.0.0"
        assert found.status == PublicationStatus.COMPLETED
        assert found.snapshot_id == snap_id

    def test_returns_none_when_deployment_not_found(self) -> None:
        engine = create_engine("sqlite://")
        Base.metadata.create_all(engine)
        _seed_project_and_env(engine, "tenant-a", "catalog", "staging")

        repo = PostgresKnowledgePublicationRepository(engine=engine)
        assert repo.find_by_deployment("catalog", "staging", "deploy-999", tenant_id="tenant-a") is None
        assert repo.find_by_deployment("catalog", "staging", "deploy-500", tenant_id="tenant-b") is None

    def test_publish_atomically_with_environment_persists_snapshot_and_promotes_environment(
        self,
    ) -> None:
        engine = create_engine("sqlite://")
        Base.metadata.create_all(engine)
        proj, env = _seed_project_and_env(engine, "tenant-a", "catalog", "staging")

        repo = PostgresKnowledgePublicationRepository(engine=engine)
        pub_id = PublicationId.generate()
        pub = DomainKnowledgePublication(
            id=pub_id,
            project_key=ProjectKey("catalog"),
            environment_name=EnvironmentName("staging"),
            deployment_id=DeploymentId("deploy-777"),
            version="1.0.0",
            status=PublicationStatus.PENDING,
        )
        snapshot = ProjectKnowledgeSnapshot(
            schema_version=SchemaVersion("1.0"),
            project_key=ProjectKey("catalog"),
            project_name="catalog",
            project_metadata=MetadataObject({"nodes": [{"id": "feature:orders"}], "edges": []}),
            revision=Revision(1),
            generated_at=GeneratedAt(datetime.now(timezone.utc)),
            entities=(),
            relations=(),
            evidence=(),
        )

        snap_id = repo.publish_atomically_with_environment(
            tenant_id="tenant-a",
            publication=pub,
            snapshot=snapshot,
            environment_id=env.id,
        )

        assert snap_id is not None
        found = repo.find_by_deployment("catalog", "staging", "deploy-777", tenant_id="tenant-a")
        assert found is not None
        assert found.status == PublicationStatus.COMPLETED
        assert found.snapshot_id == snap_id

        with Session(engine) as session:
            updated_env = session.get(ModelEnvironment, env.id)
            assert updated_env.current_snapshot_id == snap_id
            assert session.get(ModelSnapshot, snap_id).metadata_json == {
                "nodes": [{"id": "feature:orders"}], "edges": []
            }
