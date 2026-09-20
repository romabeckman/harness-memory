from dataclasses import dataclass
from uuid import UUID


@dataclass(slots=True)
class User:
    id: UUID
    name: str
    email: str

    @property
    def tenant_id(self) -> UUID:
        return self.id
