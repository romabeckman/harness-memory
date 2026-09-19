class ImpactEntityNotFound(RuntimeError):
    """Safe failure for unknown, stale, or foreign change targets."""

    def __init__(self, *_details: object):
        super().__init__("impact analysis entity not found")
