from typing import Literal

from pydantic import AnyHttpUrl, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class SecuritySettings(BaseSettings):
    """Production bearer verification settings."""

    issuer: AnyHttpUrl
    jwks_uri: AnyHttpUrl
    audience: str
    tenant_claim: str = "tenant_id"

    model_config = SettingsConfigDict(
        env_prefix="MCP_",
        case_sensitive=False,
        extra="forbid",
        hide_input_in_errors=True,
    )

    @field_validator("audience", "tenant_claim")
    @classmethod
    def required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("security setting must not be empty")
        return value

    @field_validator("issuer", "jwks_uri")
    @classmethod
    def require_https_urls(cls, value: AnyHttpUrl) -> AnyHttpUrl:
        if value.scheme != "https":
            raise ValueError("production security URLs must use HTTPS")
        return value


class RuntimeSettings(BaseSettings):
    mcp_host: str = "127.0.0.1"
    mcp_port: int = 8000
    database_url: SecretStr | None = None
    api_admin_token: SecretStr | None = None
    harness_memory_api_key: SecretStr | None = None
    mcp_issuer: AnyHttpUrl | None = None
    mcp_jwks_uri: AnyHttpUrl | None = None
    mcp_audience: str | None = None
    mcp_tenant_claim: str = "tenant_id"
    mcp_production: bool = False
    mcp_require_auth: bool = False
    mcp_auth_mode: Literal["jwt", "database"] = "jwt"

    @property
    def security(self) -> SecuritySettings | None:
        if not (self.mcp_issuer and self.mcp_jwks_uri and self.mcp_audience):
            return None
        return SecuritySettings(
            issuer=self.mcp_issuer,
            jwks_uri=self.mcp_jwks_uri,
            audience=self.mcp_audience,
            tenant_claim=self.mcp_tenant_claim,
        )

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

    @field_validator("mcp_audience")
    @classmethod
    def validate_audience(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("MCP_AUDIENCE must not be empty")
        return value.strip() if value else value

    @field_validator("mcp_issuer", "mcp_jwks_uri")
    @classmethod
    def require_https_security_urls(cls, value: AnyHttpUrl | None) -> AnyHttpUrl | None:
        if value is not None and value.scheme != "https":
            raise ValueError("production security URLs must use HTTPS")
        return value

    @field_validator("mcp_tenant_claim")
    @classmethod
    def validate_tenant_claim(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("MCP_TENANT_CLAIM must not be empty")
        return value

    @field_validator("database_url", mode="before")
    @classmethod
    def validate_database_url(cls, value: str | SecretStr | None) -> str | SecretStr | None:
        if value is not None:
            raw = value.get_secret_value() if isinstance(value, SecretStr) else str(value)
            if not raw.strip():
                raise ValueError("DATABASE_URL must not be empty")
        return value

    @model_validator(mode="after")
    def validate_production_auth(self):
        import os

        if self.mcp_production and self.mcp_host == "127.0.0.1" and "MCP_HOST" not in os.environ:
            self.mcp_host = "0.0.0.0"

        if self.mcp_require_auth and self.mcp_auth_mode == "database":
            if self.database_url is None:
                raise ValueError("incomplete production authentication settings: DATABASE_URL")
        elif self.mcp_require_auth:
            missing = [
                name
                for name, value in (
                    ("MCP_ISSUER", self.mcp_issuer),
                    ("MCP_JWKS_URI", self.mcp_jwks_uri),
                    ("MCP_AUDIENCE", self.mcp_audience),
                    ("MCP_TENANT_CLAIM", self.mcp_tenant_claim),
                )
                if not value
            ]
            if missing:
                raise ValueError(
                    "incomplete production authentication settings: " + ", ".join(missing)
                )
        return self

    def require_production_security(self) -> None:
        if self.mcp_auth_mode == "database":
            if self.database_url is None:
                raise ValueError("DATABASE_URL is required for database authentication")
            return
        if (
            not self.mcp_issuer
            or not self.mcp_jwks_uri
            or not self.mcp_audience
            or not self.mcp_tenant_claim
        ):
            raise ValueError("incomplete production authentication settings")
