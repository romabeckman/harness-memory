from dataclasses import dataclass

from ..value_objects.metadata_object import MetadataObject
from ..value_objects.project_key import ProjectKey


@dataclass(frozen=True, slots=True)
class ProjectDescriptor:
    key: ProjectKey
    name: str | None
    metadata: MetadataObject

    @property
    def project_key(self) -> ProjectKey:
        return self.key

    def __post_init__(self) -> None:
        if self.name is not None:
            name = self.name.strip()
            if not 1 <= len(name) <= 255:
                raise ValueError("project name must contain 1 to 255 characters")
            object.__setattr__(self, "name", name)
