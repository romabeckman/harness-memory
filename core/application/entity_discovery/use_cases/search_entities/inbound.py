from typing import Annotated
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictInt,
    StrictStr,
    field_validator,
)

from core.domain.snapshot_publication.types.entity_type import EntityType


class SearchEntitiesInput(BaseModel):
    key: Annotated[
        StrictStr | None,
        Field(
            max_length=255,
            description="Exact, case-sensitive entity key. Blank text is invalid.",
        ),
    ] = None
    name: Annotated[
        StrictStr | None,
        Field(
            max_length=255,
            description=(
                "Case-insensitive literal prefix of an entity name or key. "
                "Blank text is invalid."
            ),
        ),
    ] = None
    type: EntityType | None = Field(
        default=None,
        description="Restrict results to one supported entity type; see schema enum values.",
    )
    project: Annotated[
        StrictStr | None,
        Field(
            max_length=255,
            description=(
                "Exact, case-sensitive project key from search_projects; narrows "
                "content searches. Blank text is invalid."
            ),
        ),
    ] = None
    query: Annotated[
        StrictStr | None,
        Field(
            max_length=255,
            description=(
                "Find this literal phrase in entity keys, names, or metadata content, "
                "ignoring case. SQL wildcards are literal; blank text is invalid."
            ),
        ),
    ] = None
    include_history: bool = Field(
        default=False,
        description=(
            "Include removed documents and historical document revisions in the "
            "selected snapshot; does not search every prior snapshot. Defaults to false."
        ),
    )
    include_past_snapshots: bool = Field(
        default=False,
        description=(
            "Search current and older snapshots across accessible projects. "
            "Each result identifies its snapshot and publication. Defaults to false."
        ),
    )
    tenant_id: StrictStr | None = Field(
        default=None,
        max_length=255,
        description=(
            "Tenant ID from search_projects; narrows authenticated read scope "
            "and never grants access."
        ),
    )
    project_id: UUID | None = Field(
        default=None,
        description=(
            "Project UUID from search_projects; selects one project occurrence "
            "when keys repeat."
        ),
    )
    snapshot_id: UUID | None = Field(
        default=None,
        description=(
            "Immutable snapshot UUID from search_projects or search_entities; "
            "selects that snapshot, including historical ones."
        ),
    )
    environment: StrictStr | None = Field(
        default=None,
        max_length=64,
        description=(
            "Environment name from search_projects; selects its current snapshot "
            "unless snapshot_id or include_past_snapshots is supplied. Historical "
            "search limits results to snapshots published in this environment."
        ),
    )
    limit: StrictInt = Field(
        default=25,
        ge=1,
        le=100,
        description="Maximum number of results in this page, from 1 to 100.",
    )
    cursor: Annotated[
        StrictStr | None,
        Field(
            max_length=1024,
            description=(
                "Opaque next_cursor from the previous page. Keep filters and "
                "authenticated scope unchanged; restart when the selected current "
                "snapshot or historical snapshot set changes."
            ),
        ),
    ] = None

    model_config = ConfigDict(frozen=True, extra="forbid")

    @field_validator("key", "name", "project", "query", "tenant_id", "environment")
    @classmethod
    def trim_text_filter(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("search filter must not be empty")
        return value
