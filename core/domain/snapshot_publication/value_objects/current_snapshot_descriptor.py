from dataclasses import dataclass
from uuid import UUID

from .payload_hash import PayloadHash
from .revision import Revision


@dataclass(frozen=True, slots=True)
class CurrentSnapshotDescriptor:
    snapshot_id: UUID
    revision: Revision
    payload_hash: PayloadHash
