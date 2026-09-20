from enum import StrEnum


class MemoryScope(StrEnum):
    READ = "memory:read"
    PUBLISH = "memory:publish"
    IMPACT = "memory:impact"
