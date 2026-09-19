from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class RuntimeSettings(BaseSettings):
    mcp_host: str = "127.0.0.1"
    mcp_port: int = 8000
    database_url: SecretStr | None = None

    model_config = SettingsConfigDict(
        env_prefix="",
        case_sensitive=False,
        extra="ignore",
        hide_input_in_errors=True,
    )

    @field_validator("mcp_host")
    @classmethod
    def validate_host(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("MCP_HOST must not be empty")
        return value.strip()

    @field_validator("mcp_port")
    @classmethod
    def validate_port(cls, value: int) -> int:
        if not 1 <= value <= 65535:
            raise ValueError("MCP_PORT must be between 1 and 65535")
        return value
