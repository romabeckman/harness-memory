from sqlalchemy import true
from sqlalchemy.sql.elements import ColumnElement

from core.application.entity_discovery.contracts.tenant_scope import TenantScope


def tenant_scope_predicate(scope: TenantScope, tenant_column) -> ColumnElement[bool]:
    return true() if scope.is_admin else tenant_column == scope.tenant_id
