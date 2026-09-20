from pathlib import Path


def test_ci_workflow_defines_required_quality_gates():
    workflow = Path(__file__).resolve().parents[3] / ".github" / "workflows" / "ci.yml"

    assert workflow.exists()
    content = workflow.read_text(encoding="utf-8")
    for job in ("lint", "test-migrations", "test-unit", "test-integration", "test-e2e", "coverage"):
        assert f"{job}:" in content
    assert "pytest --cov=core --cov=mcp --cov-fail-under=80" in content
    assert "postgres:17" in content


def test_runtime_dependency_declares_opentelemetry_api():
    pyproject = Path(__file__).resolve().parents[3] / "pyproject.toml"

    content = pyproject.read_text(encoding="utf-8")

    assert "opentelemetry-api" in content
