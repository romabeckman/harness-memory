import pytest
from pydantic import ValidationError

from harness_memory_mcp.config import RuntimeSettings


def test_runtime_settings_accept_valid_mcp_values_without_database():
    settings = RuntimeSettings(mcp_host="127.0.0.1", mcp_port=8000)

    assert settings.mcp_host == "127.0.0.1"
    assert settings.mcp_port == 8000
    assert settings.database_url is None


@pytest.mark.parametrize("port", [0, 65536])
def test_runtime_settings_reject_invalid_mcp_port(port):
    with pytest.raises(ValidationError):
        RuntimeSettings(mcp_host="127.0.0.1", mcp_port=port)


def test_runtime_settings_reject_blank_host():
    with pytest.raises(ValidationError):
        RuntimeSettings(mcp_host="   ", mcp_port=8000)


def test_database_auth_mode_requires_database_but_not_jwt_settings():
    settings = RuntimeSettings(
        mcp_auth_mode="database",
        database_url="postgresql+psycopg2://user:pass@postgres/memory",
        mcp_production=True,
    )

    settings.require_production_security()

    with pytest.raises(ValueError, match="DATABASE_URL"):
        RuntimeSettings(mcp_auth_mode="database", mcp_production=True).require_production_security()
