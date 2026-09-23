from dataclasses import dataclass

from core.domain.snapshot_publication.types.entity_type import EntityType


@dataclass(frozen=True, slots=True)
class EntitySearchCriteria:
    key: str | None = None
    name: str | None = None
    type: EntityType | None = None
    project: str | None = None

    def __post_init__(self) -> None:
        values = {"key": self.key, "name": self.name, "project": self.project}
        normalized: dict[str, str | None] = {}
        for field, value in values.items():
            if value is not None and not isinstance(value, str):
                raise ValueError(f"{field} filter must be text")
            trimmed = value.strip() if value is not None else None
            if trimmed == "":
                raise ValueError(f"{field} filter must not be empty")
            if trimmed is not None and len(trimmed) > 255:
                raise ValueError(f"{field} filter is too long")
            normalized[field] = trimmed.lower() if field == "name" and trimmed else trimmed

        entity_type = self.type
        if entity_type is not None:
            try:
                entity_type = EntityType(entity_type)
            except (TypeError, ValueError) as error:
                raise ValueError("unsupported EntityType") from error

        if not any(value is not None for value in normalized.values()) and entity_type is None:
            raise ValueError("at least one discovery filter is required")

        object.__setattr__(self, "key", normalized["key"])
        object.__setattr__(self, "name", normalized["name"])
        object.__setattr__(self, "project", normalized["project"])
        object.__setattr__(self, "type", entity_type)

    @property
    def name_like(self) -> str | None:
        if self.name is None:
            return None
        return self.name.replace("!", "!!").replace("%", "!%").replace("_", "!_")

    @property
    def project_like(self) -> str | None:
        if self.project is None:
            return None
        return self.project.lower().replace("!", "!!").replace("%", "!%").replace("_", "!_")
