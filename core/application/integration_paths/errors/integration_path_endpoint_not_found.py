class IntegrationPathEndpointNotFound(RuntimeError):
    """Safe failure for unknown, stale, or foreign path endpoints."""

    def __init__(self, *_details: object):
        super().__init__("integration path endpoint not found")

