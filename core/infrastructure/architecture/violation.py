from dataclasses import dataclass


@dataclass(frozen=True)
class ArchitectureViolation:
    file: str
    import_name: str
    message: str
