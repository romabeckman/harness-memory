from dataclasses import dataclass

from ..types.entity_type import EntityType
from ..value_objects.entity_key import EntityKey
from ..value_objects.metadata_object import MetadataObject


@dataclass(frozen=True, slots=True)
class EntityFact:
    key: EntityKey
    type: EntityType
    name: str | None
    metadata: MetadataObject

    @property
    def entity_type(self) -> EntityType:
        return self.type

    def __post_init__(self) -> None:
        if self.name is not None:
            name = self.name.strip()
            if not 1 <= len(name) <= 255:
                raise ValueError("entity name must contain 1 to 255 characters")
            object.__setattr__(self, "name", name)
