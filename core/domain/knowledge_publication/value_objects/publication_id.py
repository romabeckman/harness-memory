from dataclasses import dataclass
from uuid import UUID, uuid4


@dataclass(frozen=True)
class PublicationId:
    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise TypeError("publication_id must be a UUID")

    @classmethod
    def generate(cls) -> "PublicationId":
        return cls(uuid4())
