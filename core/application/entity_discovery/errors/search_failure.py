class EntitySearchFailure(RuntimeError):
    """Stable search failure that does not expose persistence details."""

    def __init__(self, _detail: str | None = None):
        super().__init__("entity search failed")
