from dataclasses import dataclass
from uuid import UUID

from core.domain.snapshot_publication.types.entity_type import EntityType


@dataclass(frozen=True, slots=True)
class EntitySearchCriteria:
    key: str | None = None
    name: str | None = None
    type: EntityType | None = None
    project: str | None = None
    query: str | None = None
    include_history: bool = False
    include_past_snapshots: bool = False
    tenant_id: str | None = None
    project_id: UUID | None = None
    snapshot_id: UUID | None = None
    environment: str | None = None
    allow_unfiltered: bool = False

    def __post_init__(self) -> None:
        values = {
            "key": self.key,
            "name": self.name,
            "project": self.project,
            "query": self.query,
            "tenant_id": self.tenant_id,
            "environment": self.environment,
        }
        normalized: dict[str, str | None] = {}
        for field, value in values.items():
            if value is not None and not isinstance(value, str):
                raise ValueError(f"{field} filter must be text")
            trimmed = value.strip() if value is not None else None
            if trimmed == "":
                raise ValueError(f"{field} filter must not be empty")
            if trimmed is not None and len(trimmed) > 255:
                raise ValueError(f"{field} filter is too long")
            normalized[field] = (
                trimmed.lower() if field in {"name", "query"} and trimmed else trimmed
            )

        entity_type = self.type
        if entity_type is not None:
            try:
                entity_type = EntityType(entity_type)
            except (TypeError, ValueError) as error:
                raise ValueError("unsupported EntityType") from error

        if (
            not self.allow_unfiltered
            and not any(value is not None for value in normalized.values())
            and entity_type is None
            and self.project_id is None
            and self.snapshot_id is None
        ):
            raise ValueError("at least one discovery filter is required")

        object.__setattr__(self, "key", normalized["key"])
        object.__setattr__(self, "name", normalized["name"])
        object.__setattr__(self, "project", normalized["project"])
        object.__setattr__(self, "query", normalized["query"])
        object.__setattr__(self, "type", entity_type)
        object.__setattr__(self, "tenant_id", normalized["tenant_id"])
        object.__setattr__(self, "environment", normalized["environment"])
        for field in ("project_id", "snapshot_id"):
            value = getattr(self, field)
            if value is not None and not isinstance(value, UUID):
                try:
                    object.__setattr__(self, field, UUID(str(value)))
                except (TypeError, ValueError) as error:
                    raise ValueError(f"invalid {field}") from error
        if not isinstance(self.include_history, bool):
            raise ValueError("include_history must be a boolean")
        if not isinstance(self.include_past_snapshots, bool):
            raise ValueError("include_past_snapshots must be a boolean")

    @property
    def name_like(self) -> str | None:
        if self.name is None:
            return None
        return self.name.replace("!", "!!").replace("%", "!%").replace("_", "!_")

    @property
    def query_like(self) -> str | None:
        if self.query is None:
            return None
        return self.query.replace("!", "!!").replace("%", "!%").replace("_", "!_")
