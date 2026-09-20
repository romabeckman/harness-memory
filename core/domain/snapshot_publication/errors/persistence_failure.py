class PersistenceFailure(RuntimeError):
    """Stable publication persistence failure without infrastructure details."""

    def __init__(self, _detail: str | None = None):
        super().__init__("snapshot publication persistence failed")
