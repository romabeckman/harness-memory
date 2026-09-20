import os
import pytest
from pydantic import ValidationError
from mcp.config import RuntimeSettings


def test_validate_production_configuration_requires_database_url_and_production_flag(monkeypatch):
    monkeypatch.setenv("MCP_PRODUCTION", "true")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/harness_memory")
    monkeypatch.setenv("MCP_ISSUER", "https://issuer.example")
    monkeypatch.setenv("MCP_JWKS_URI", "https://issuer.example/.well-known/jwks.json")
    monkeypatch.setenv("MCP_AUDIENCE", "harness-memory")

    settings = RuntimeSettings()
    assert settings.mcp_production is True
    assert settings.mcp_host == "0.0.0.0"
    assert settings.mcp_port == 8000
    assert settings.database_url is not None
    assert "user:pass" in settings.database_url.get_secret_value()


def test_refuse_startup_when_production_flag_enabled_but_database_empty(monkeypatch):
    monkeypatch.setenv("MCP_PRODUCTION", "true")
    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setenv("MCP_ISSUER", "https://issuer.example")
    monkeypatch.setenv("MCP_JWKS_URI", "https://issuer.example/.well-known/jwks.json")
    monkeypatch.setenv("MCP_AUDIENCE", "harness-memory")

    with pytest.raises((ValidationError, ValueError)):
        RuntimeSettings()


def test_production_configuration_loads_with_database_without_auth_settings(monkeypatch):
    for name in ("MCP_ISSUER", "MCP_JWKS_URI", "MCP_AUDIENCE", "MCP_TENANT_CLAIM"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("MCP_PRODUCTION", "true")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/harness_memory")

    settings = RuntimeSettings()

    assert settings.mcp_host == "0.0.0.0"
    assert settings.mcp_port == 8000
    assert settings.database_url is not None
