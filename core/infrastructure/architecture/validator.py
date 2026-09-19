import ast
from pathlib import Path

from .violation import ArchitectureViolation


class ArchitectureValidator:
    _PROHIBITED = {
        "core.domain": (
            "core.application",
            "core.infrastructure",
            "mcp",
            "fastmcp",
            "sqlalchemy",
            "psycopg",
        ),
        "core.application": (
            "core.infrastructure",
            "mcp",
            "fastmcp",
            "sqlalchemy",
            "psycopg",
        ),
    }

    def validate(self, project_root: Path) -> list[ArchitectureViolation]:
        violations = []
        for source in project_root.rglob("*.py"):
            if any(part in {".venv", "venv", "__pycache__"} for part in source.parts):
                continue
            layer = self._layer_for(source, project_root)
            if layer is None:
                continue
            try:
                tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
            except (OSError, SyntaxError) as error:
                violations.append(
                    ArchitectureViolation(
                        str(source), "<parse>", f"cannot inspect imports: {error}"
                    )
                )
                continue
            for imported in self._imports(tree):
                if self._is_prohibited(layer, imported):
                    violations.append(
                        ArchitectureViolation(
                            str(source), imported, f"{layer} must not import {imported}"
                        )
                    )
        return violations

    @staticmethod
    def _layer_for(source: Path, root: Path) -> str | None:
        relative = source.relative_to(root).as_posix()
        for layer in ("core/domain", "core/application"):
            if relative.startswith(f"{layer}/"):
                return layer.replace("/", ".")
        return None

    @staticmethod
    def _imports(tree: ast.AST) -> list[str]:
        names = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                names.append(node.module)
        return names

    def _is_prohibited(self, layer: str, imported: str) -> bool:
        return any(
            imported == prefix or imported.startswith(f"{prefix}.")
            for prefix in self._PROHIBITED[layer]
        )
