from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TenantScope:
    tenant_id: str

    def __post_init__(self) -> None:
        value = self.tenant_id.strip() if isinstance(self.tenant_id, str) else ""
        if not value:
            raise ValueError("tenant context is required")
        object.__setattr__(self, "tenant_id", value)
