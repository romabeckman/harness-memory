class RelationshipQueryFailure(Exception):
    """Safe application failure for relationship persistence queries."""

    def __init__(self, *_details: object):
        super().__init__("relationship query failed")
