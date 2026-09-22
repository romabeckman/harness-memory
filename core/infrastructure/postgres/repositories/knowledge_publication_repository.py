from collections.abc import Callable
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

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
from core.domain.snapshot_publication.value_objects.project_key import ProjectKey
from core.infrastructure.postgres.models.environment import Environment as ModelEnvironment
from core.infrastructure.postgres.models.knowledge_publication import (
    KnowledgePublication as ModelKnowledgePublication,
)
from core.infrastructure.postgres.models.project import Project as ModelProject
from core.infrastructure.postgres.repositories.snapshot_persistence_mapper import SnapshotPersistenceMapper
from core.application.snapshot_publication.services.snapshot_payload import snapshot_payload
from core.infrastructure.postgres.models.snapshot import Snapshot as ModelSnapshot
from core.application.snapshot_publication.services.payload_hash_calculator import PayloadHashCalculator


class PostgresKnowledgePublicationRepository:
    def __init__(
        self,
        session_factory: Callable[[], Session] | None = None,
        *,
        engine=None,
        mapper: SnapshotPersistenceMapper | None = None,
    ) -> None:
        if session_factory is None and engine is not None:
            session_factory = sessionmaker(bind=engine, expire_on_commit=False)
        if session_factory is None:
            raise ValueError("session_factory or engine is required")
        self._session_factory = session_factory
        self._mapper = mapper or SnapshotPersistenceMapper()
        self._hash_calculator = PayloadHashCalculator()

    def find_by_deployment(
        self, project_key: str, env_name: str, deployment_id: str, tenant_id: str
    ) -> DomainKnowledgePublication | None:
        with self._session_factory() as session:
            stmt = (
                select(ModelKnowledgePublication)
                .join(
                    ModelProject,
                    (ModelProject.id == ModelKnowledgePublication.project_id)
                    & (ModelProject.tenant_id == ModelKnowledgePublication.tenant_id),
                )
                .join(
                    ModelEnvironment,
                    (ModelEnvironment.id == ModelKnowledgePublication.environment_id)
                    & (ModelEnvironment.tenant_id == ModelKnowledgePublication.tenant_id),
                )
                .where(
                    ModelKnowledgePublication.tenant_id == tenant_id,
                    ModelProject.key == project_key,
                    ModelEnvironment.name == env_name,
                    ModelKnowledgePublication.deployment_id == deployment_id,
                )
            )
            result = session.execute(
                stmt.with_only_columns(ModelKnowledgePublication, ModelSnapshot.payload_hash)
                .outerjoin(
                    ModelSnapshot,
                    (ModelSnapshot.id == ModelKnowledgePublication.snapshot_id)
                    & (ModelSnapshot.tenant_id == ModelKnowledgePublication.tenant_id),
                )
            ).first()
            if result is None:
                return None
            row, payload_hash = result

            return DomainKnowledgePublication(
                id=PublicationId(row.id),
                project_key=ProjectKey(project_key),
                environment_name=EnvironmentName(env_name),
                deployment_id=DeploymentId(row.deployment_id),
                version=row.version,
                status=PublicationStatus(row.status),
                snapshot_id=row.snapshot_id,
                payload_hash=payload_hash,
            )

    def save(self, publication: DomainKnowledgePublication, tenant_id: str) -> None:
        with self._session_factory() as session:
            proj = session.scalars(
                select(ModelProject).where(
                    ModelProject.tenant_id == tenant_id,
                    ModelProject.key == publication.project_key.value,
                )
            ).first()
            if proj is None:
                raise ValueError(f"project {publication.project_key.value} not found")

            env = session.scalars(
                select(ModelEnvironment).where(
                    ModelEnvironment.tenant_id == tenant_id,
                    ModelEnvironment.project_id == proj.id,
                    ModelEnvironment.name == publication.environment_name.value,
                )
            ).first()
            if env is None:
                raise ValueError(f"environment {publication.environment_name.value} not found")

            model = ModelKnowledgePublication(
                id=publication.id.value,
                tenant_id=tenant_id,
                project_id=proj.id,
                environment_id=env.id,
                deployment_id=publication.deployment_id.value,
                version=publication.version,
                status=publication.status.value,
                snapshot_id=publication.snapshot_id,
            )
            session.add(model)
            session.commit()

    def publish_atomically_with_environment(
        self,
        tenant_id: str,
        publication: DomainKnowledgePublication,
        snapshot: ProjectKnowledgeSnapshot,
        environment_id: UUID,
    ) -> UUID:
        with self._session_factory() as session:
            with session.begin():
                proj = session.scalars(
                    select(ModelProject).where(
                        ModelProject.tenant_id == tenant_id,
                        ModelProject.key == publication.project_key.value,
                    )
                ).first()
                if proj is None:
                    proj = ModelProject(
                        id=uuid4(),
                        tenant_id=tenant_id,
                        key=publication.project_key.value,
                        name=publication.project_key.value,
                    )
                    session.add(proj)
                    session.flush()

                env = session.scalars(
                    select(ModelEnvironment).where(
                        ModelEnvironment.tenant_id == tenant_id,
                        ModelEnvironment.id == environment_id,
                    )
                ).first()
                if env is None:
                    raise ValueError(f"environment {environment_id} not found")

                payload_hash = publication.payload_hash
                if payload_hash is None:
                    content = snapshot_payload(snapshot)
                    content.pop("generated_at", None)
                    payload_hash = self._hash_calculator.calculate(content).value
                rows = self._mapper.map(
                    snapshot=snapshot,
                    tenant_id=tenant_id,
                    payload_hash=payload_hash,
                    project_id=proj.id,
                )
                rows.snapshot.environment_id = env.id
                rows.snapshot.publication_id = publication.id.value

                session.add(rows.snapshot)
                session.flush()
                session.add_all(rows.entities)
                session.flush()
                session.add_all(rows.relations)
                session.flush()
                session.add_all(rows.evidence)
                session.flush()

                model = ModelKnowledgePublication(
                    id=publication.id.value,
                    tenant_id=tenant_id,
                    project_id=proj.id,
                    environment_id=env.id,
                    deployment_id=publication.deployment_id.value,
                    version=publication.version,
                    status=PublicationStatus.COMPLETED.value,
                    snapshot_id=rows.snapshot.id,
                )
                session.add(model)
                session.flush()

                env.current_snapshot_id = rows.snapshot.id
                if env.type == "production" or proj.active_snapshot_id is None:
                    proj.active_snapshot_id = rows.snapshot.id
                session.flush()

                return rows.snapshot.id
