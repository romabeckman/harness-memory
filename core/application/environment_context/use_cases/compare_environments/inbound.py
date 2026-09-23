from dataclasses import dataclass


@dataclass(frozen=True)
class CompareEnvironmentsInput:
    project_key: str
    source_environment: str
    target_environment: str
    tenant_id: str | None = "default"
    limit: int = 500
    offset: int = 0
