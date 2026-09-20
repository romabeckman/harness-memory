class EntityContextNotFound(Exception):
    """Safe application failure for absent, stale, or foreign entity identities."""

    def __init__(self, *_details: object):
        super().__init__("entity context not found")
