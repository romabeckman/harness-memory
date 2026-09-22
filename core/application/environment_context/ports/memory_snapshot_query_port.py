from typing import Protocol
from uuid import UUID


class MemorySnapshotQueryPort(Protocol):
    def get_snapshot_entity_fingerprints(
        self, snapshot_id: UUID, tenant_id: str | None = None
    ) -> dict[str, str]:
        ...
