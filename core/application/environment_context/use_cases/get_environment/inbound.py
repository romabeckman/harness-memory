from dataclasses import dataclass


@dataclass(frozen=True)
class GetEnvironmentInput:
    project_key: str
    environment_name: str
    tenant_id: str = "default"
