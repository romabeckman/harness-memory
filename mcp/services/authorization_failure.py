class AuthorizationFailure(Exception):
    """Raised when authenticated context lacks a required MCP scope."""
