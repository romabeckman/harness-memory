class AuthorizationFailure(Exception):
    """Raised when authenticated context lacks a required MCP scope."""

    def __init__(
        self,
        message: str = "required MCP scope is missing",
        required_scope: str | None = None,
    ):
        super().__init__(message)
        self.required_scope = required_scope
