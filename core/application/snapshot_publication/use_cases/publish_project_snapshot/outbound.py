from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class PublishProjectSnapshotOutput(BaseModel):
    status: Literal["ACTIVATED", "ALREADY_PUBLISHED"]
    snapshot_id: UUID
    requested_revision: int
    stored_revision: int
    active_snapshot_id: UUID
    payload_hash: str
    entity_count: int
    relation_count: int
    evidence_count: int

    model_config = ConfigDict(frozen=True, extra="forbid")
