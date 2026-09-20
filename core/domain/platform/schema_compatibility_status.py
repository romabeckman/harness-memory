from pydantic import BaseModel, ConfigDict, field_validator


class SchemaCompatibilityStatus(BaseModel):
    current_revision: str | None
    head_revision: str
    model_config = ConfigDict(frozen=True)

    @field_validator("head_revision")
    @classmethod
    def validate_head_revision(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("head_revision must not be empty")
        return value

    def is_compatible(self) -> bool:
        return self.current_revision is not None and self.current_revision == self.head_revision
