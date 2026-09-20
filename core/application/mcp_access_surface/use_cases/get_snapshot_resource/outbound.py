from pydantic import BaseModel, ConfigDict

from core.application.mcp_access_surface.contracts.snapshot_context_item import SnapshotContextItem
from core.application.mcp_access_surface.contracts.snapshot_fact_page import SnapshotFactPage


class SnapshotResourceOutput(BaseModel):
    snapshot: SnapshotContextItem
    facts: SnapshotFactPage

    model_config = ConfigDict(frozen=True, extra="forbid")
