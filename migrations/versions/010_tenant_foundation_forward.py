"""Forward migration: enforce first-class tenants table, UUID columns, and referential integrity."""

from uuid import UUID

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None


def _json_object() -> sa.JSON:
    return sa.JSON().with_variant(JSONB(), "postgresql")


def upgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    existing_tables = set(inspector.get_table_names())

    # 1. Create tenants table if it doesn't already exist
    if "tenants" not in existing_tables:
        op.create_table(
            "tenants",
            sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
            sa.Column("key", sa.String(length=255), nullable=False),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
            sa.Column("metadata", _json_object(), server_default=sa.text("'{}'"), nullable=False),
            sa.Column(
                "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
            ),
            sa.Column(
                "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("key", name="uq_tenants_key"),
            sa.CheckConstraint("length(trim(key)) > 0", name="ck_tenants_key_non_empty"),
            sa.CheckConstraint("status IN ('active', 'disabled')", name="ck_tenants_status_valid"),
        )
        op.create_index("ix_tenants_key", "tenants", ["key"])

    # 2. Harvest all distinct tenant identities
    tenant_ids = set()
    candidate_tables = [
        "projects",
        "snapshots",
        "entities",
        "relations",
        "evidence",
        "service_accounts",
        "environments",
        "knowledge_publications",
    ]
    for table_name in candidate_tables:
        if table_name in existing_tables:
            columns = {col["name"] for col in inspector.get_columns(table_name)}
            if "tenant_id" in columns:
                rows = connection.execute(sa.text(f"SELECT DISTINCT tenant_id FROM {table_name} WHERE tenant_id IS NOT NULL")).fetchall()
                for (val,) in rows:
                    if val is not None:
                        try:
                            uid = UUID(str(val))
                            tenant_ids.add(uid)
                        except (ValueError, AttributeError) as err:
                            raise RuntimeError(
                                f"Cannot convert non-UUID tenant_id '{val}' in table '{table_name}' to UUID: remediation required."
                            ) from err

    # Check users table
    if "users" in existing_tables:
        columns = {col["name"] for col in inspector.get_columns("users")}
        if "tenant_id" not in columns:
            # users.id was used as tenant_id
            user_rows = connection.execute(sa.text("SELECT id FROM users")).fetchall()
            for (uid_val,) in user_rows:
                try:
                    uid = UUID(str(uid_val))
                    tenant_ids.add(uid)
                except (ValueError, AttributeError) as err:
                    raise RuntimeError(f"Cannot convert user id '{uid_val}' to UUID for tenant backfill: {err}") from err

    # Backfill tenants table
    existing_tenant_rows = connection.execute(sa.text("SELECT id FROM tenants")).fetchall()
    existing_tenant_ids = {UUID(str(r[0])) for r in existing_tenant_rows}
    missing_tenants = tenant_ids - existing_tenant_ids

    for missing_id in missing_tenants:
        connection.execute(
            sa.text(
                "INSERT INTO tenants (id, key, name, status, metadata, created_at, updated_at) "
                "VALUES (:id, :key, :name, 'active', '{}', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            ).bindparams(sa.bindparam("id", type_=sa.Uuid(as_uuid=True))),
            {"id": missing_id, "key": str(missing_id), "name": f"Tenant {str(missing_id)[:8]}"},
        )

    # 3. Add tenant_id column to users if not present and backfill
    if "users" in existing_tables:
        user_cols = {col["name"] for col in inspector.get_columns("users")}
        if "tenant_id" not in user_cols:
            with op.batch_alter_table("users") as batch_op:
                batch_op.add_column(sa.Column("tenant_id", sa.Uuid(as_uuid=True), nullable=True))
            connection.execute(sa.text("UPDATE users SET tenant_id = id WHERE tenant_id IS NULL"))
            with op.batch_alter_table("users") as batch_op:
                batch_op.alter_column("tenant_id", nullable=False)
                batch_op.create_foreign_key(
                    "fk_users_tenant_id", "tenants", ["tenant_id"], ["id"], ondelete="RESTRICT"
                )
                batch_op.create_index("ix_users_tenant_id", ["tenant_id"])

    # 4. Ensure foreign keys to tenants exist on tenant-scoped tables
    for table_name in candidate_tables:
        if table_name in existing_tables:
            existing_fks = {fk["name"] for fk in inspector.get_foreign_keys(table_name)}
            expected_fk_name = f"fk_{table_name}_tenant_id"
            if expected_fk_name not in existing_fks:
                try:
                    with op.batch_alter_table(table_name) as batch_op:
                        batch_op.create_foreign_key(
                            expected_fk_name,
                            "tenants",
                            ["tenant_id"],
                            ["id"],
                            ondelete="RESTRICT",
                        )
                except Exception:
                    pass


def downgrade() -> None:
    pass
