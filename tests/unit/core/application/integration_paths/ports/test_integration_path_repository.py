from core.application.integration_paths.ports.integration_path_repository import (
    IntegrationPathRepository,
)


def test_integration_path_repository_exposes_find_paths_port():
    assert hasattr(IntegrationPathRepository, "find_paths")
