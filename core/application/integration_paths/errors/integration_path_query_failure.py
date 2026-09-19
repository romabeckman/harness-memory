class IntegrationPathQueryFailure(RuntimeError):
    """Safe failure for integration path persistence queries."""

    def __init__(self, *_details: object):
        super().__init__("integration path query failed")

