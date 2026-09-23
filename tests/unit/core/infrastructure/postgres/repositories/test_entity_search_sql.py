import pytest
from sqlalchemy.dialects import postgresql

from core.application.entity_discovery.contracts.entity_search_criteria import (
    EntitySearchCriteria,
)
from core.application.entity_discovery.contracts.tenant_scope import TenantScope
from core.infrastructure.postgres.repositories.entity_search_repository import (
    PostgresEntitySearchRepository,
)


@pytest.mark.parametrize(
    "criteria",
    [EntitySearchCriteria(name="gobox"), EntitySearchCriteria(project="gobox")],
)
def test_postgresql_prefix_queries_use_a_literal_safe_escape_character(criteria):
    statement = PostgresEntitySearchRepository._statement(
        TenantScope("tenant-a"), criteria, None, 100
    )

    sql = str(statement.compile(dialect=postgresql.dialect()))

    assert "ESCAPE '!'" in sql
