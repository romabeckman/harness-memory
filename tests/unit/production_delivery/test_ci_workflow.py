from pathlib import Path


def test_ci_workflow_defines_required_quality_gates():
    workflow = Path(__file__).resolve().parents[3] / ".github" / "workflows" / "ci.yml"

    assert workflow.exists()
    content = workflow.read_text(encoding="utf-8")
    for job in (
        "lint",
        "test-migrations",
        "test-unit",
        "test-integration",
        "test-e2e",
        "coverage",
    ):
        assert f"{job}:" in content
    for coverage_target in ("--cov=api", "--cov=core", "--cov=harness_memory_mcp"):
        assert coverage_target in content
    assert "pytest tests/unit tests/e2e --cov=api" in content
    assert "pytest tests/integration --ignore=tests/integration/migrations" in content
    assert (
        "pytest tests/integration/migrations tests/integration/core/infrastructure/postgres/test_startup_schema_compatibility.py"
        in content
    )
    assert "--cov-append" in content
    assert (
        "coverage report --include='api/*,core/*,harness_memory_mcp/*' --fail-under=80" in content
    )
    assert "postgres:17" in content


def test_runtime_dependency_declares_opentelemetry_api():
    pyproject = Path(__file__).resolve().parents[3] / "pyproject.toml"

    content = pyproject.read_text(encoding="utf-8")

    assert "opentelemetry-api" in content
