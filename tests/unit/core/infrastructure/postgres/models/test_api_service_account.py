from uuid import uuid4

import pytest
import sqlalchemy as sa

from core.infrastructure.postgres.models.api_service_account import ApiServiceAccount
from core.infrastructure.postgres.models.tenant import Tenant


@pytest.mark.parametrize("tenant_values", [{}, {"tenant_id": None}])
def test_service_account_accepts_no_tenant_and_preserves_foreign_key(tenant_values):
    metadata = sa.MetaData()
    tenants = Tenant.__table__.to_metadata(metadata)
    accounts = ApiServiceAccount.__table__.to_metadata(metadata)
    engine = sa.create_engine("sqlite:///:memory:")
    try:
        with engine.begin() as connection:
            connection.exec_driver_sql("PRAGMA foreign_keys=ON")
            metadata.create_all(connection)
            account_id, tenant_id = uuid4(), uuid4()
            connection.execute(
                accounts.insert(), {"id": account_id, "name": "Unassigned", **tenant_values}
            )
            assert (
                connection.scalar(
                    sa.select(accounts.c.tenant_id).where(accounts.c.id == account_id)
                )
                is None
            )
            connection.execute(
                tenants.insert(), {"id": tenant_id, "key": "tenant", "name": "Tenant"}
            )
            connection.execute(
                accounts.insert(), {"id": uuid4(), "name": "Assigned", "tenant_id": tenant_id}
            )
            with pytest.raises(sa.exc.IntegrityError):
                connection.execute(
                    accounts.insert(), {"id": uuid4(), "name": "Invalid", "tenant_id": uuid4()}
                )
            with pytest.raises(sa.exc.IntegrityError):
                connection.execute(tenants.delete().where(tenants.c.id == tenant_id))
    finally:
        engine.dispose()
