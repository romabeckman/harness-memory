import json

import pytest
from pydantic import ValidationError

from core.application.relationship_context.errors.entity_context_not_found import (
    EntityContextNotFound,
)
from core.application.relationship_context.errors.relationship_query_failure import (
    RelationshipQueryFailure,
)
from core.application.snapshot_publication.errors.missing_tenant_context import MissingTenantContext
from harness_memory_mcp.services.authorization_failure import AuthorizationFailure
from harness_memory_mcp.services.relationship_response_mapper import RelationshipResponseMapper


def test_relationship_mapper_maps_success_to_json():
    class Result:
        def model_dump(self, mode):
            assert mode == "json"
            return {"status": "OK"}

    assert RelationshipResponseMapper().success(Result()) == {"status": "OK"}


def test_relationship_mapper_bounds_large_repeated_document_context_and_reports_truncation():
    class Result:
        def model_dump(self, mode):
            assert mode == "json"
            entity = {"key": "doc", "metadata": {"content": "x" * 5000}}
            return {
                "entity": entity,
                "project": {"key": "p"},
                "owners": [],
                "relations": [
                    {
                        "source": entity.copy(),
                        "target": entity.copy(),
                        "evidence": [{"excerpt": "y" * 5000}],
                    }
                    for _ in range(100)
                ],
                "dependencies": [],
                "relations_truncated": False,
                "dependencies_truncated": False,
            }

    mapped = RelationshipResponseMapper().success(Result())

    assert len(json.dumps(mapped).encode("utf-8")) <= 262144
    assert mapped["response_truncated"] is True
    assert mapped["entity"]["metadata"]["content"] == "x" * 5000


def test_relationship_mapper_bounds_context_page_without_losing_newest_item():
    contexts = [
        {
            "entity": {"key": key, "metadata": {"content": "x" * 140000}},
            "project": {"key": "p"},
            "owners": [],
            "relations": [],
            "dependencies": [],
        }
        for key in ("newest", "older")
    ]
    page = {"items": contexts, "count": 2, "limit": 25, "offset": 0, "has_more": False}

    mapped = RelationshipResponseMapper().success(page)

    assert len(json.dumps(mapped).encode("utf-8")) <= 262144
    assert mapped["items"][0]["entity"]["key"] == "newest"
    assert mapped["count"] == len(mapped["items"])
    assert mapped["has_more"] is True
    assert mapped["response_truncated"] is True


def test_relationship_mapper_keeps_single_oversized_page_item_readable():
    page = {
        "items": [
            {
                "entity": {"key": "only", "metadata": {"content": "x" * 300000}},
                "project": {"key": "p"},
                "owners": [],
                "relations": [],
                "dependencies": [],
            }
        ],
        "count": 1,
        "limit": 25,
        "offset": 0,
        "has_more": False,
    }

    mapped = RelationshipResponseMapper().success(page)

    assert mapped["items"][0]["entity"]["key"] == "only"
    assert mapped["items"][0]["entity"]["metadata"] == {"truncated": True}
    assert mapped["count"] == 1
    assert len(json.dumps(mapped).encode("utf-8")) <= 262144


def test_relationship_mapper_uses_one_safe_not_found_shape():
    mapper = RelationshipResponseMapper()

    first = mapper.failure(EntityContextNotFound("tenant-a/known"))
    second = mapper.failure(EntityContextNotFound("tenant-b/other"))

    assert (
        first
        == second
        == {
            "status": "ERROR",
            "error": {"code": "ENTITY_NOT_FOUND", "message": "entity context not found"},
        }
    )
    assert "tenant" not in str(first).lower()


def test_relationship_mapper_hides_persistence_details():
    error = RelationshipQueryFailure(
        "SELECT * FROM relations", "postgres://user:password@host/db", "tenant-a", "stack trace"
    )

    response = RelationshipResponseMapper().failure(error)

    assert response == {
        "status": "ERROR",
        "error": {
            "code": "RELATIONSHIP_QUERY_FAILED",
            "message": "relationship query failed",
        },
    }
    assert all(value not in str(response) for value in ["SELECT", "password", "tenant-a", "stack"])


def test_relationship_mapper_maps_validation_and_missing_context():
    mapper = RelationshipResponseMapper()
    from core.application.relationship_context.use_cases.get_context.inbound import GetContextInput

    with pytest.raises(ValidationError) as caught:
        GetContextInput(entity_id="bad")
    validation = caught.value

    assert mapper.failure(validation)["error"]["code"] == "INVALID_RELATIONSHIP_CONTRACT"
    assert mapper.failure(MissingTenantContext("secret tenant"))["error"]["code"] == (
        "MISSING_TENANT_CONTEXT"
    )


def test_relationship_mapper_maps_authorization_failure_without_details():
    response = RelationshipResponseMapper().failure(
        AuthorizationFailure("missing memory:read", required_scope="memory:read")
    )

    assert response == {
        "status": "ERROR",
        "error": {
            "code": "RELATIONSHIP_UNAUTHORIZED",
            "message": "relationship access is unauthorized",
        },
    }
