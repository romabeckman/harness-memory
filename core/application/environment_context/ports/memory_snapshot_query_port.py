from typing import Protocol
from uuid import UUID


class MemorySnapshotQueryPort(Protocol):
    def get_snapshot_entity_keys(self, snapshot_id: UUID, tenant_id: str | None = None) -> set[str]:
        ...
