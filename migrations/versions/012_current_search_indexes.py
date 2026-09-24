"""Index current search selectors and literal metadata phrase lookup."""

from alembic import op

revision = "012"
down_revision = "011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_entities_metadata_trgm "
        "ON entities USING gin ((lower(metadata::text)) gin_trgm_ops)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_entities_key_snapshot_occurrence "
        "ON entities (entity_key, snapshot_id, id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_entities_name_global_prefix "
        "ON entities (lower(name) text_pattern_ops, snapshot_id, entity_key, id) "
        "WHERE name IS NOT NULL"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_projects_key_tenant_id "
        "ON projects (key, tenant_id, id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_environments_name_current_snapshot "
        "ON environments (name, tenant_id, current_snapshot_id) "
        "WHERE current_snapshot_id IS NOT NULL"
    )


def downgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    for name in (
        "ix_environments_name_current_snapshot",
        "ix_projects_key_tenant_id",
        "ix_entities_name_global_prefix",
        "ix_entities_key_snapshot_occurrence",
        "ix_entities_metadata_trgm",
    ):
        op.execute(f"DROP INDEX IF EXISTS {name}")
