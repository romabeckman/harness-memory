from pathlib import Path

from core.infrastructure.architecture.rules import ValidateArchitecture


def test_validate_architecture_accepts_inward_dependency_edges(tmp_path):
    root = tmp_path / "project"
    (root / "mcp").mkdir(parents=True)
    (root / "core" / "application").mkdir(parents=True)
    (root / "core" / "domain").mkdir(parents=True)
    (root / "core" / "infrastructure").mkdir(parents=True)
    (root / "mcp" / "adapter.py").write_text(
        "from core.application.foundation import action\n", encoding="utf-8"
    )
    (root / "core" / "application" / "foundation.py").write_text(
        "from core.domain.foundation import value\n", encoding="utf-8"
    )
    (root / "core" / "infrastructure" / "adapter.py").write_text(
        "from core.application.foundation import action\n", encoding="utf-8"
    )

    assert ValidateArchitecture().execute(root) == []


def test_validate_architecture_reports_domain_infrastructure_import(tmp_path):
    root = tmp_path / "project"
    source = root / "core" / "domain" / "bad.py"
    source.parent.mkdir(parents=True)
    source.write_text("from core.infrastructure.postgres.models import Project\n", encoding="utf-8")

    violations = ValidateArchitecture().execute(root)

    assert len(violations) == 1
    assert "core/domain/bad.py" in violations[0].file.replace("\\", "/")
    assert "core.infrastructure" in violations[0].import_name


def test_validate_architecture_reports_application_fastmcp_and_model_imports(tmp_path):
    root = tmp_path / "project"
    source = root / "core" / "application" / "bad.py"
    source.parent.mkdir(parents=True)
    source.write_text(
        "from fastmcp import FastMCP\nfrom core.infrastructure.postgres.models import Project\n",
        encoding="utf-8",
    )

    violations = ValidateArchitecture().execute(root)

    assert len(violations) == 2


def test_validate_architecture_accepts_repository_source_tree():
    project_root = Path(__file__).resolve().parents[3]

    assert ValidateArchitecture().execute(project_root) == []
