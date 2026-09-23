from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class PublishKnowledgeInput:
    project_key: str
    environment_name: str
    deployment_id: str
    version: str
    tenant_id: str = "default"
    entities: tuple[Any, ...] = field(default_factory=tuple)
    relations: tuple[Any, ...] = field(default_factory=tuple)
    evidence: tuple[Any, ...] = field(default_factory=tuple)
    metadata: dict[str, Any] = field(default_factory=dict)
