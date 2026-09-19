"""Add project-scoped graph identities for impact analysis."""

from uuid import NAMESPACE_URL, uuid5

import sqlalchemy as sa
from alembic import op

revision = "f006_canonical_impact_identity"
down_revision = "f003_entity_search_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "entities",
        sa.Column("identity_id", sa.Uuid(as_uuid=True), nullable=True),
    )
    op.add_column(
        "relations",
        sa.Column("source_identity_id", sa.Uuid(as_uuid=True), nullable=True),
    )
    op.add_column(
        "relations",
        sa.Column("target_identity_id", sa.Uuid(as_uuid=True), nullable=True),
    )
    connection = op.get_bind()
    entity_rows = connection.execute(
        sa.text(
            "SELECT entities.id, entities.tenant_id, entities.entity_type, "
            "entities.entity_key, projects.key AS project_key "
            "FROM entities JOIN projects ON projects.id = entities.project_id "
            "AND projects.tenant_id = entities.tenant_id"
        )
    ).mappings()
    identities = {
        (row["tenant_id"], row["id"]): uuid5(
            NAMESPACE_URL,
            f"harness-memory:{row['tenant_id']}:{row['entity_type']}:"
            f"project:{row['project_key']}:{row['entity_key']}",
        )
        for row in entity_rows
    }
    if identities:
        connection.execute(
            sa.text(
                "UPDATE entities SET identity_id = :identity_id "
                "WHERE id = :entity_id AND tenant_id = :tenant_id"
            ),
            [
                {
                    "identity_id": identity,
                    "entity_id": entity_id,
                    "tenant_id": tenant_id,
                }
                for (tenant_id, entity_id), identity in identities.items()
            ],
        )
    relation_rows = connection.execute(
        sa.text(
            "SELECT id, tenant_id, source_entity_id, target_entity_id "
            "FROM relations"
        )
    ).mappings()
    relation_updates = []
    for row in relation_rows:
        source_identity = identities.get((row["tenant_id"], row["source_entity_id"]))
        target_identity = identities.get((row["tenant_id"], row["target_entity_id"]))
        if source_identity is None or target_identity is None:
            continue
        relation_updates.append(
            {
                "relation_id": row["id"],
                "tenant_id": row["tenant_id"],
                "source_identity_id": source_identity,
                "target_identity_id": target_identity,
            }
        )
    if relation_updates:
        connection.execute(
            sa.text(
                "UPDATE relations SET source_identity_id = :source_identity_id, "
                "target_identity_id = :target_identity_id "
                "WHERE id = :relation_id AND tenant_id = :tenant_id"
            ),
            relation_updates,
        )
    op.create_index(
        "ix_entities_tenant_identity",
        "entities",
        ["tenant_id", "identity_id", "snapshot_id"],
    )
    op.create_index(
        "ix_relations_source_identity",
        "relations",
        ["tenant_id", "source_identity_id"],
    )
    op.create_index(
        "ix_relations_target_identity",
        "relations",
        ["tenant_id", "target_identity_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_relations_target_identity", table_name="relations")
    op.drop_index("ix_relations_source_identity", table_name="relations")
    op.drop_index("ix_entities_tenant_identity", table_name="entities")
    op.drop_column("relations", "target_identity_id")
    op.drop_column("relations", "source_identity_id")
    op.drop_column("entities", "identity_id")
