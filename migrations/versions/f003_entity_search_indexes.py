"""Add bounded Entity discovery indexes."""

import sqlalchemy as sa
from alembic import op

revision = "f003_entity_search_indexes"
down_revision = "f001_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_entities_tenant_key_active_search",
        "entities",
        ["tenant_id", "entity_key", "snapshot_id", "id"],
    )
    op.create_index(
        "ix_entities_tenant_type_active_search",
        "entities",
        ["tenant_id", "entity_type", "snapshot_id", "entity_key", "id"],
    )
    op.create_index(
        "ix_entities_tenant_name_prefix_search",
        "entities",
        ["tenant_id", sa.text("lower(name) text_pattern_ops"), "snapshot_id", "entity_key", "id"],
        postgresql_where=sa.text("name IS NOT NULL"),
    )
    op.create_index(
        "ix_projects_tenant_active_snapshot",
        "projects",
        ["tenant_id", "active_snapshot_id", "id"],
        postgresql_where=sa.text("active_snapshot_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_projects_tenant_active_snapshot", table_name="projects")
    op.drop_index("ix_entities_tenant_name_prefix_search", table_name="entities")
    op.drop_index("ix_entities_tenant_type_active_search", table_name="entities")
    op.drop_index("ix_entities_tenant_key_active_search", table_name="entities")
