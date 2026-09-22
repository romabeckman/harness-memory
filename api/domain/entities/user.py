from dataclasses import dataclass
from uuid import UUID


@dataclass(slots=True)
class User:
    id: UUID
    name: str
    email: str
    tenant_id: UUID | None = None

    def __post_init__(self) -> None:
        if self.tenant_id is None:
            object.__setattr__(self, "tenant_id", self.id)
