from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StrictStr


class ChangeDescription(BaseModel):
    entity_id: UUID = Field(description="Identifier of the entity being changed.")
    change_type: StrictStr = Field(
        default="contract",
        min_length=1,
        max_length=64,
        description="Category of change, such as a contract or implementation change.",
    )
    description: StrictStr = Field(
        default="",
        max_length=4096,
        description="Short human-readable summary of the proposed change.",
    )
    changed_fields: tuple[StrictStr, ...] = Field(
        default=(),
        description="Names of the entity fields affected by the change.",
    )

    model_config = ConfigDict(frozen=True, extra="forbid")
