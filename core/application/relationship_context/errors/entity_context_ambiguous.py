class EntityContextAmbiguous(ValueError):
    """A canonical identity resolves to more than one visible occurrence."""

    def __init__(self):
        super().__init__("entity context is ambiguous; select an occurrence or project")
