from typing import Callable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session, sessionmaker

from core.application.snapshot_publication.types.publication_record import PublicationRecord
from core.domain.snapshot_publication.aggregates.project_knowledge_snapshot import (
    ProjectKnowledgeSnapshot,
)
from core.domain.snapshot_publication.errors.persistence_failure import PersistenceFailure
from core.domain.snapshot_publication.errors.revision_conflict import RevisionConflict
from core.domain.snapshot_publication.errors.stale_revision import StaleRevision
from core.domain.snapshot_publication.services.snapshot_revision_policy import (
    SnapshotRevisionPolicy,
)
from core.domain.snapshot_publication.types.revision_decision import RevisionDecision
from core.domain.snapshot_publication.value_objects.current_snapshot_descriptor import (
    CurrentSnapshotDescriptor,
)
from core.domain.snapshot_publication.value_objects.payload_hash import PayloadHash
from core.domain.snapshot_publication.value_objects.revision import Revision

from ..models.project import Project
from ..models.snapshot import Snapshot
from .snapshot_persistence_mapper import SnapshotPersistenceMapper


class PostgresSnapshotPublicationRepository:
    def __init__(
        self,
        session_factory: Callable[[], Session] | sessionmaker | None = None,
        engine=None,
        mapper: SnapshotPersistenceMapper | None = None,
        revision_policy: SnapshotRevisionPolicy | None = None,
        session: Session | None = None,
    ):
        if session_factory is not None and not callable(session_factory):
            session = session_factory
            session_factory = None
        if session is not None and session_factory is None:

            def session_factory():
                return session
        if session_factory is None and engine is not None:
            write_engine = engine.execution_options(isolation_level="READ COMMITTED")
            session_factory = sessionmaker(bind=write_engine, expire_on_commit=False)
        if session_factory is None:
            raise ValueError("session_factory or engine is required")
        self._session_factory = session_factory
        self._mapper = mapper or SnapshotPersistenceMapper()
        self._policy = revision_policy or SnapshotRevisionPolicy()

    def publish_atomically(
        self, tenant_id: str, snapshot: ProjectKnowledgeSnapshot, payload_hash: PayloadHash
    ) -> PublicationRecord:
        if isinstance(payload_hash, str):
            payload_hash = PayloadHash(payload_hash)
        for attempt in range(2):
            try:
                return self._publish_once(tenant_id, snapshot, payload_hash)
            except IntegrityError as error:
                if not self._is_retryable_integrity_error(error):
                    raise PersistenceFailure(str(error)) from None
                if attempt == 1:
                    raise PersistenceFailure() from None
            except OperationalError as error:
                if not self._is_retryable_operational_error(error):
                    raise PersistenceFailure(str(error)) from None
                if attempt == 1:
                    raise PersistenceFailure() from None
        raise PersistenceFailure()

    def _publish_once(
        self, tenant_id: str, snapshot: ProjectKnowledgeSnapshot, payload_hash: PayloadHash
    ) -> PublicationRecord:
        try:
            with self._session_factory() as session:
                with session.begin():
                    project = session.execute(
                        select(Project)
                        .where(
                            Project.tenant_id == tenant_id,
                            Project.key == snapshot.project.key.value,
                        )
                        .with_for_update()
                    ).scalar_one_or_none()
                    if project is None:
                        project = Project(
                            tenant_id=tenant_id,
                            key=snapshot.project.key.value,
                            name=snapshot.project.name,
                            metadata_json=snapshot.project.metadata.to_dict(),
                        )
                        session.add(project)
                        session.flush()

                    existing = session.execute(
                        select(Snapshot)
                        .where(
                            Snapshot.tenant_id == tenant_id,
                            Snapshot.project_id == project.id,
                            Snapshot.revision == snapshot.revision.value,
                        )
                        .with_for_update()
                    ).scalar_one_or_none()
                    if existing is not None:
                        if existing.payload_hash != payload_hash.value:
                            raise RevisionConflict("revision already contains different content")
                        return self._record(
                            "ALREADY_PUBLISHED", existing, project.active_snapshot_id
                        )

                    active = None
                    if project.active_snapshot_id is not None:
                        active = session.execute(
                            select(Snapshot)
                            .where(
                                Snapshot.id == project.active_snapshot_id,
                                Snapshot.tenant_id == tenant_id,
                            )
                            .with_for_update()
                        ).scalar_one_or_none()
                    current = (
                        CurrentSnapshotDescriptor(
                            active.id, Revision(active.revision), PayloadHash(active.payload_hash)
                        )
                        if active is not None
                        else None
                    )
                    candidate = CurrentSnapshotDescriptor(
                        UUID(int=0), snapshot.revision, payload_hash
                    )
                    decision = self._policy.decide(current, candidate)
                    if decision is not RevisionDecision.ACTIVATE:
                        return self._record("ALREADY_PUBLISHED", active, project.active_snapshot_id)

                    project.name = snapshot.project.name
                    project.metadata_json = snapshot.project.metadata.to_dict()
                    rows = self._mapper.map(snapshot, tenant_id, payload_hash, project.id)
                    session.add(rows.snapshot)
                    session.flush()
                    session.add_all(rows.entities)
                    session.flush()
                    session.add_all(rows.relations)
                    session.flush()
                    session.add_all(rows.evidence)
                    session.flush()
                    project.active_snapshot_id = rows.snapshot.id
                    session.flush()
                    return self._record("ACTIVATED", rows.snapshot, rows.snapshot.id)
        except (RevisionConflict, StaleRevision, PersistenceFailure, IntegrityError):
            raise
        except OperationalError as error:
            if self._is_retryable_operational_error(error):
                raise
            raise PersistenceFailure(str(error)) from None
        except Exception as error:
            raise PersistenceFailure(str(error)) from None

    @staticmethod
    def _is_retryable_operational_error(error: OperationalError) -> bool:
        original = getattr(error, "orig", None)
        sqlstate = getattr(original, "pgcode", None) or getattr(original, "sqlstate", None)
        if sqlstate in {"40001", "40P01"}:
            return True
        detail = str(original or error).lower()
        return "database is locked" in detail or "deadlock detected" in detail

    @staticmethod
    def _is_retryable_integrity_error(error: IntegrityError) -> bool:
        original = getattr(error, "orig", None)
        sqlstate = getattr(original, "pgcode", None) or getattr(original, "sqlstate", None)
        if sqlstate == "23505":
            return True
        detail = str(original or error).lower()
        return "unique constraint" in detail or "duplicate key" in detail

    @staticmethod
    def _is_serialization_failure(error: OperationalError) -> bool:
        """Backward-compatible classifier for PostgreSQL serialization failures."""
        original = getattr(error, "orig", None)
        sqlstate = getattr(original, "pgcode", None) or getattr(original, "sqlstate", None)
        return sqlstate == "40001"

    @staticmethod
    def _record(
        status: str, snapshot: Snapshot | None, active_snapshot_id: UUID | None
    ) -> PublicationRecord:
        if snapshot is None or active_snapshot_id is None:
            raise PersistenceFailure()
        payload = snapshot.payload or {}
        return PublicationRecord(
            status=status,
            snapshot_id=snapshot.id,
            requested_revision=snapshot.revision,
            stored_revision=snapshot.revision,
            active_snapshot_id=active_snapshot_id,
            payload_hash=snapshot.payload_hash,
            entity_count=len(payload.get("entities", [])),
            relation_count=len(payload.get("relations", [])),
            evidence_count=len(payload.get("evidence", [])),
        )
