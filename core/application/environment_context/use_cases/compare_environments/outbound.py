from dataclasses import dataclass


@dataclass(frozen=True)
class CompareEnvironmentsOutput:
    source_environment: str
    target_environment: str
    added_entities: tuple[str, ...]
    removed_entities: tuple[str, ...]
    unchanged_entities: tuple[str, ...]
    total_added: int = 0
    total_removed: int = 0
    total_unchanged: int = 0
