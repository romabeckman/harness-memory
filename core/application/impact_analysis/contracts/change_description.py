from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StrictStr


class ChangeDescription(BaseModel):
    entity_id: UUID = Field(
        description=(
            "Required target UUID from search_entities.entity_id; must match any "
            "separate target UUID supplied to analyze_impact."
        )
    )
    change_type: StrictStr = Field(
        default="contract",
        min_length=1,
        max_length=64,
        description=(
            "Category such as contract or implementation; defaults to contract "
            "and overrides the separate change_type argument."
        ),
    )
    description: StrictStr = Field(
        default="",
        max_length=4096,
        description=(
            "Short summary of the proposed change; overrides the separate description argument."
        ),
    )
    changed_fields: tuple[StrictStr, ...] = Field(
        default=(),
        description=(
            "Affected entity field names; overrides the separate changed_fields argument."
        ),
    )

    model_config = ConfigDict(frozen=True, extra="forbid")
