from pydantic import BaseModel, ConfigDict, StrictBool

from core.application.relationship_context.contracts.dependency_view import DependencyView
from core.application.relationship_context.contracts.entity_context_item import EntityContextItem
from core.application.relationship_context.contracts.project_context_item import ProjectContextItem
from core.application.relationship_context.contracts.relation_view import RelationView


class GetContextOutput(BaseModel):
    entity: EntityContextItem
    project: ProjectContextItem
    owners: tuple[EntityContextItem, ...] = ()
    relations: tuple[RelationView, ...] = ()
    dependencies: tuple[DependencyView, ...] = ()
    relations_truncated: StrictBool = False
    dependencies_truncated: StrictBool = False

    model_config = ConfigDict(frozen=True, extra="forbid")
