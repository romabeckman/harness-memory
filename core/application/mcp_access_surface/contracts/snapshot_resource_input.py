from uuid import UUID

from pydantic import BaseModel, ConfigDict


class SnapshotResourceInput(BaseModel):
    snapshot_id: UUID

    model_config = ConfigDict(frozen=True, extra="forbid")
