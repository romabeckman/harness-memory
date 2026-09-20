from pydantic import BaseModel, ConfigDict, StrictBool

from core.application.relationship_context.contracts.entity_context_item import EntityContextItem
from core.application.relationship_context.contracts.project_context_item import ProjectContextItem


class ProjectResourceOutput(BaseModel):
    project: ProjectContextItem
    entities: tuple[EntityContextItem, ...] = ()
    entities_truncated: StrictBool = False

    model_config = ConfigDict(frozen=True, extra="forbid")
