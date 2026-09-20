from dataclasses import dataclass

from ..value_objects.metadata_object import MetadataObject
from ..value_objects.relation_reference import RelationReference


@dataclass(frozen=True, slots=True, init=False)
class EvidenceFact:
    source: str
    excerpt: str | None
    relation_reference: RelationReference | None
    metadata: MetadataObject

    def __init__(
        self,
        source: str,
        excerpt: str | None = None,
        relation_reference: RelationReference | None = None,
        metadata: MetadataObject | None = None,
        *,
        relation_ref: RelationReference | None = None,
    ) -> None:
        object.__setattr__(self, "source", source)
        object.__setattr__(self, "excerpt", excerpt)
        object.__setattr__(self, "relation_reference", relation_reference or relation_ref)
        object.__setattr__(self, "metadata", metadata or MetadataObject({}))
        self.__post_init__()

    def __post_init__(self) -> None:
        if not isinstance(self.source, str) or not 1 <= len(self.source.strip()) <= 1024:
            raise ValueError("evidence source must contain 1 to 1024 characters")
        object.__setattr__(self, "source", self.source.strip())
        if self.excerpt is not None and len(self.excerpt) > 4096:
            raise ValueError("evidence excerpt must contain at most 4096 characters")

    @property
    def relation_ref(self) -> RelationReference | None:
        return self.relation_reference
