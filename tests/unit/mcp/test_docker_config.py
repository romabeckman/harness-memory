import pytest
from pydantic import ValidationError

from mcp.docker_config import DockerRuntimeConfig


def test_docker_runtime_config_defaults_to_production_host_and_port():
    config = DockerRuntimeConfig(database_url="postgresql+psycopg2://user:pass@db/app")

    assert config.mcp_host == "0.0.0.0"
    assert config.mcp_port == 8000
    assert config.mcp_production is True


def test_docker_runtime_config_rejects_invalid_host_and_port():
    with pytest.raises(ValidationError):
        DockerRuntimeConfig(
            database_url="postgresql+psycopg2://user:pass@db/app",
            mcp_host="",
        )
    with pytest.raises(ValidationError):
        DockerRuntimeConfig(
            database_url="postgresql+psycopg2://user:pass@db/app",
            mcp_port=0,
        )
    with pytest.raises(ValidationError):
        DockerRuntimeConfig(database_url=" ")
