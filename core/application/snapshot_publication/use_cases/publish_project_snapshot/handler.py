from typing import Any

from core.domain.snapshot_publication.errors.persistence_failure import PersistenceFailure
from core.domain.snapshot_publication.errors.revision_conflict import RevisionConflict
from core.domain.snapshot_publication.errors.snapshot_invariant_violation import (
    SnapshotInvariantViolation,
)
from core.domain.snapshot_publication.errors.stale_revision import StaleRevision
from core.domain.snapshot_publication.services.snapshot_builder import SnapshotBuilder

from ...errors.missing_tenant_context import MissingTenantContext
from ...ports.snapshot_publication_store import SnapshotPublicationStore
from ...services.payload_hash_calculator import PayloadHashCalculator
from ...types.publication_context import PublicationContext
from ..publish_project_snapshot.outbound import PublishProjectSnapshotOutput


class PublishProjectSnapshotHandler:
    def __init__(
        self,
        store: SnapshotPublicationStore,
        builder: SnapshotBuilder | None = None,
        hash_calculator: PayloadHashCalculator | None = None,
    ):
        self._store = store
        self._builder = builder or SnapshotBuilder()
        self._hash_calculator = hash_calculator or PayloadHashCalculator()

    def execute(
        self, request: Any, context: PublicationContext | None
    ) -> PublishProjectSnapshotOutput:
        if context is None:
            raise MissingTenantContext("trusted tenant context is required")
        snapshot = self._builder.build(request)
        payload_hash = self._hash_calculator.calculate(request)
        try:
            record = self._store.publish_atomically(context.tenant_id, snapshot, payload_hash)
        except (
            PersistenceFailure,
            MissingTenantContext,
            RevisionConflict,
            StaleRevision,
            SnapshotInvariantViolation,
        ):
            raise
        except Exception as error:
            raise PersistenceFailure(str(error)) from None
        return PublishProjectSnapshotOutput.model_validate(
            {
                "status": record.status,
                "snapshot_id": record.snapshot_id,
                "requested_revision": record.requested_revision,
                "stored_revision": record.stored_revision,
                "active_snapshot_id": record.active_snapshot_id,
                "payload_hash": record.payload_hash,
                "entity_count": record.entity_count,
                "relation_count": record.relation_count,
                "evidence_count": record.evidence_count,
            }
        )


PublishProjectSnapshot = PublishProjectSnapshotHandler
