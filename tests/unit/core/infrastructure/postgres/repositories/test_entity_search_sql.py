from sqlalchemy.dialects import postgresql

from core.application.entity_discovery.contracts.entity_search_criteria import (
    EntitySearchCriteria,
)
from core.application.entity_discovery.contracts.tenant_scope import TenantScope
from core.infrastructure.postgres.repositories.entity_search_repository import (
    PostgresEntitySearchRepository,
)


def test_postgresql_name_prefix_query_uses_a_literal_safe_escape_character():
    statement = PostgresEntitySearchRepository._statement(
        TenantScope("tenant-a"), EntitySearchCriteria(name="gobox"), None, 100
    )

    sql = str(statement.compile(dialect=postgresql.dialect()))

    assert "ESCAPE '!'" in sql


def test_project_filter_compiles_as_exact_equality_and_query_searches_json_metadata():
    statement = PostgresEntitySearchRepository._statement(
        TenantScope("tenant-a"),
        EntitySearchCriteria(project="send", query="database"),
        None,
        25,
    )

    sql = str(statement.compile(dialect=postgresql.dialect()))

    assert "projects.key =" in sql
    assert "lower(CAST(entities.metadata AS TEXT)) LIKE" in sql
