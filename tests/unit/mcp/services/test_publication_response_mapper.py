from harness_memory_mcp.services.authorization_failure import AuthorizationFailure
from harness_memory_mcp.services.publication_response_mapper import PublicationResponseMapper


def test_publication_scope_failures_have_stable_unauthorized_code():
    result = PublicationResponseMapper().failure(
        AuthorizationFailure(required_scope="memory:publish")
    )

    assert result == {
        "status": "ERROR",
        "error": {
            "code": "PUBLICATION_UNAUTHORIZED",
            "message": "snapshot publication authorization required",
        },
    }
