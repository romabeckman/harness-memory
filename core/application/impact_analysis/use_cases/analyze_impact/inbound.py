from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StrictStr, model_validator

from ...contracts.change_description import ChangeDescription
from ...types.impact_analysis_bounds import ImpactAnalysisBounds


class AnalyzeImpactInput(BaseModel):
    entity_id: UUID | None = None
    changed_entity_id: UUID | None = None
    target_entity_id: UUID | None = None
    change: ChangeDescription | None = None
    change_type: StrictStr = Field(default="contract", min_length=1, max_length=64)
    description: StrictStr = Field(default="", max_length=4096)
    changed_fields: tuple[StrictStr, ...] = ()
    bounds: ImpactAnalysisBounds = Field(default_factory=ImpactAnalysisBounds)

    model_config = ConfigDict(frozen=True, extra="forbid")

    @model_validator(mode="after")
    def normalize_change(self):
        candidates = tuple(
            value
            for value in (self.entity_id, self.changed_entity_id, self.target_entity_id)
            if value is not None
        )
        if self.change is not None:
            candidates += (self.change.entity_id,)
        if not candidates:
            raise ValueError("a change target entity is required")
        if any(candidate != candidates[0] for candidate in candidates[1:]):
            raise ValueError("change target entity is ambiguous")
        object.__setattr__(self, "entity_id", candidates[0])
        if self.change is not None:
            object.__setattr__(self, "change_type", self.change.change_type)
            object.__setattr__(self, "description", self.change.description)
            object.__setattr__(self, "changed_fields", self.change.changed_fields)
        return self


ImpactAnalysisInput = AnalyzeImpactInput
