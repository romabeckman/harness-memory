class ImpactQueryFailure(RuntimeError):
    """Safe failure for impact graph queries."""

    def __init__(self, *_details: object):
        super().__init__("impact analysis query failed")
