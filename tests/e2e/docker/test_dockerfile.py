from pathlib import Path


def test_docker_container_runs_as_non_root_appuser():
    dockerfile_path = Path(__file__).resolve().parents[3] / "Dockerfile"
    assert dockerfile_path.exists()
    content = dockerfile_path.read_text(encoding="utf-8")
    assert "useradd -u 10001" in content
    assert "USER 10001" in content


def test_exclude_dev_and_test_artifacts_from_docker_image():
    dockerignore_path = Path(__file__).resolve().parents[3] / ".dockerignore"
    assert dockerignore_path.exists()
    content = dockerignore_path.read_text(encoding="utf-8")
    ignored_patterns = [
        line.strip()
        for line in content.splitlines()
        if line.strip() and not line.startswith("#")
    ]
    assert ".git" in ignored_patterns
    assert ".venv" in ignored_patterns or "venv" in ignored_patterns
    assert ".pytest_cache" in ignored_patterns
    assert ".coverage" in ignored_patterns
    assert "tests" in ignored_patterns


def test_builder_copies_package_sources_before_installing_project():
    dockerfile_path = Path(__file__).resolve().parents[3] / "Dockerfile"
    content = dockerfile_path.read_text(encoding="utf-8")

    assert "COPY core ./core" in content
    assert "COPY harness_memory_mcp ./harness_memory_mcp" in content
    assert "RUN pip install --no-cache-dir --prefix=/install ." in content


def test_compose_starts_mcp_from_the_application_package():
    compose_path = Path(__file__).resolve().parents[3] / "docker-compose.yml"
    content = compose_path.read_text(encoding="utf-8")

    assert 'command: ["python", "-m", "harness_memory_mcp.server.app"]' in content


def test_compose_mcp_service_declares_production_runtime_settings():
    compose_path = Path(__file__).resolve().parents[3] / "docker-compose.yml"
    content = compose_path.read_text(encoding="utf-8")

    assert "MCP_PRODUCTION: \"true\"" in content
    assert "MCP_AUTH_MODE: database" in content
    assert "DATABASE_URL:" in content
