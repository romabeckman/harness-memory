from pathlib import Path

from .validator import ArchitectureValidator
from .violation import ArchitectureViolation


class ValidateArchitecture:
    def execute(self, project_root: str | Path = ".") -> list[ArchitectureViolation]:
        return ArchitectureValidator().validate(Path(project_root).resolve())

    def validate(self, project_root: str | Path = ".") -> list[ArchitectureViolation]:
        return self.execute(project_root)
