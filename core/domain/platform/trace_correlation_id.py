from pydantic import BaseModel, ConfigDict, field_validator


class TraceCorrelationId(BaseModel):
    value: str | None
    model_config = ConfigDict(frozen=True)

    @field_validator("value")
    @classmethod
    def validate_hex32(cls, val: str | None) -> str | None:
        if val is None:
            return None
        clean = val.strip().lower()
        if len(clean) != 32 or any(c not in "0123456789abcdef" for c in clean):
            raise ValueError("TraceCorrelationId must be a 32-character hexadecimal string")
        if clean == "0" * 32:
            raise ValueError("TraceCorrelationId cannot be all zeros")
        return clean
