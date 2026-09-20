from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class DockerRuntimeConfig(BaseSettings):
    """Production Docker container runtime configuration."""

    mcp_host: str = "0.0.0.0"
    mcp_port: int = 8000
    database_url: SecretStr
    mcp_production: bool = True

    model_config = SettingsConfigDict(
        env_prefix="",
        case_sensitive=False,
        extra="ignore",
        hide_input_in_errors=True,
    )

    @field_validator("mcp_host")
    @classmethod
    def validate_host(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("MCP_HOST must not be empty")
        return value

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: SecretStr) -> SecretStr:
        if not value.get_secret_value().strip():
            raise ValueError("DATABASE_URL must not be empty")
        return value

    @field_validator("mcp_port")
    @classmethod
    def validate_port(cls, value: int) -> int:
        if not 1 <= value <= 65535:
            raise ValueError("MCP_PORT must be between 1 and 65535")
        return value
