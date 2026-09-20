from typing import get_type_hints

from core.application.relationship_context.ports.relationship_query_repository import (
    RelationshipQueryRepository,
)


def test_relationship_query_port_declares_both_tenant_scoped_read_operations():
    hints = get_type_hints(RelationshipQueryRepository.load_context)
    dependency_hints = get_type_hints(RelationshipQueryRepository.load_dependencies)

    assert "scope" in hints
    assert "query" in hints
    assert "scope" in dependency_hints
    assert "query" in dependency_hints
