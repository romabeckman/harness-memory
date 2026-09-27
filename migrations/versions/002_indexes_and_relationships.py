"""Create indexes and foreign keys after all tables exist."""

import sqlalchemy as sa
from alembic import op

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_foreign_key(
        "fk_projects_tenant_id", "projects", "tenants", ["tenant_id"], ["id"], ondelete="RESTRICT"
    )

    op.create_foreign_key(
        "fk_snapshots_tenant_id", "snapshots", "tenants", ["tenant_id"], ["id"], ondelete="RESTRICT"
    )

    op.create_foreign_key(
        "fk_entities_tenant_id", "entities", "tenants", ["tenant_id"], ["id"], ondelete="RESTRICT"
    )

    op.create_foreign_key(
        "fk_relations_tenant_id", "relations", "tenants", ["tenant_id"], ["id"], ondelete="RESTRICT"
    )

    op.create_foreign_key(
        "fk_evidence_tenant_id", "evidence", "tenants", ["tenant_id"], ["id"], ondelete="RESTRICT"
    )

    op.create_foreign_key(
        "fk_snapshots_project_tenant",
        "snapshots",
        "projects",
        ["project_id", "tenant_id"],
        ["id", "tenant_id"],
        ondelete="CASCADE",
    )

    op.create_foreign_key(
        "fk_entities_project_tenant",
        "entities",
        "projects",
        ["project_id", "tenant_id"],
        ["id", "tenant_id"],
        ondelete="CASCADE",
    )

    op.create_foreign_key(
        "fk_entities_snapshot_project_tenant",
        "entities",
        "snapshots",
        ["snapshot_id", "project_id", "tenant_id"],
        ["id", "project_id", "tenant_id"],
        ondelete="CASCADE",
    )

    op.create_foreign_key(
        "fk_relations_snapshot_tenant",
        "relations",
        "snapshots",
        ["snapshot_id", "tenant_id"],
        ["id", "tenant_id"],
        ondelete="CASCADE",
    )

    op.create_foreign_key(
        "fk_relations_source_entity_scope",
        "relations",
        "entities",
        ["source_entity_id", "snapshot_id", "tenant_id"],
        ["id", "snapshot_id", "tenant_id"],
        ondelete="CASCADE",
    )

    op.create_foreign_key(
        "fk_relations_target_entity_scope",
        "relations",
        "entities",
        ["target_entity_id", "snapshot_id", "tenant_id"],
        ["id", "snapshot_id", "tenant_id"],
        ondelete="CASCADE",
    )

    op.create_foreign_key(
        "fk_evidence_snapshot_tenant",
        "evidence",
        "snapshots",
        ["snapshot_id", "tenant_id"],
        ["id", "tenant_id"],
        ondelete="CASCADE",
    )

    op.create_foreign_key(
        "fk_evidence_relation_scope",
        "evidence",
        "relations",
        ["relation_id", "snapshot_id", "tenant_id"],
        ["id", "snapshot_id", "tenant_id"],
        ondelete="CASCADE",
    )

    op.create_foreign_key(
        "fk_projects_active_snapshot",
        "projects",
        "snapshots",
        ["active_snapshot_id", "id", "tenant_id"],
        ["id", "project_id", "tenant_id"],
        ondelete="SET NULL",
        deferrable=True,
        initially="DEFERRED",
    )

    op.create_foreign_key(
        "fk_users_tenant_id", "users", "tenants", ["tenant_id"], ["id"], ondelete="RESTRICT"
    )

    op.create_foreign_key(
        "tokens_user_id_fkey", "tokens", "users", ["user_id"], ["id"], ondelete="CASCADE"
    )

    op.create_foreign_key(
        "fk_service_accounts_tenant_id",
        "service_accounts",
        "tenants",
        ["tenant_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    op.create_foreign_key(
        "fk_tokens_service_account_id_service_accounts",
        "tokens",
        "service_accounts",
        ["service_account_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.create_foreign_key(
        "fk_environments_tenant_id",
        "environments",
        "tenants",
        ["tenant_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    op.create_foreign_key(
        "fk_environments_project_tenant",
        "environments",
        "projects",
        ["project_id", "tenant_id"],
        ["id", "tenant_id"],
        ondelete="CASCADE",
    )

    op.create_foreign_key(
        "fk_environments_current_snapshot",
        "environments",
        "snapshots",
        ["current_snapshot_id", "tenant_id"],
        ["id", "tenant_id"],
        ondelete="SET NULL",
    )

    op.create_foreign_key(
        "fk_knowledge_publications_tenant_id",
        "knowledge_publications",
        "tenants",
        ["tenant_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    op.create_foreign_key(
        "fk_knowledge_publications_project_tenant",
        "knowledge_publications",
        "projects",
        ["project_id", "tenant_id"],
        ["id", "tenant_id"],
        ondelete="CASCADE",
    )

    op.create_foreign_key(
        "fk_knowledge_publications_environment_tenant",
        "knowledge_publications",
        "environments",
        ["environment_id", "tenant_id"],
        ["id", "tenant_id"],
        ondelete="CASCADE",
    )

    op.create_foreign_key(
        "fk_knowledge_publications_snapshot_tenant",
        "knowledge_publications",
        "snapshots",
        ["snapshot_id", "tenant_id"],
        ["id", "tenant_id"],
        ondelete="SET NULL",
    )

    op.create_index("ix_tenants_key", "tenants", ["key"])

    op.create_index("ix_projects_tenant_key", "projects", ["tenant_id", "key"])

    op.create_index(
        "ix_snapshots_tenant_project_revision", "snapshots", ["tenant_id", "project_id", "revision"]
    )

    op.create_index(
        "ix_snapshots_tenant_project_hash", "snapshots", ["tenant_id", "project_id", "payload_hash"]
    )

    op.create_index(
        "ix_entities_snapshot_key", "entities", ["tenant_id", "snapshot_id", "entity_key"]
    )

    op.create_index("ix_entities_project", "entities", ["tenant_id", "project_id"])

    op.create_index("ix_relations_snapshot", "relations", ["tenant_id", "snapshot_id"])

    op.create_index(
        "ix_relations_source", "relations", ["tenant_id", "snapshot_id", "source_entity_id"]
    )

    op.create_index(
        "ix_relations_target", "relations", ["tenant_id", "snapshot_id", "target_entity_id"]
    )

    op.create_index("ix_evidence_snapshot", "evidence", ["tenant_id", "snapshot_id"])

    op.create_index("ix_evidence_relation", "evidence", ["tenant_id", "snapshot_id", "relation_id"])

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

    op.create_index(
        "ix_entities_tenant_identity", "entities", ["tenant_id", "identity_id", "snapshot_id"]
    )

    op.create_index(
        "ix_relations_source_identity", "relations", ["tenant_id", "source_identity_id"]
    )

    op.create_index(
        "ix_relations_target_identity", "relations", ["tenant_id", "target_identity_id"]
    )

    op.create_index(
        "ix_security_audit_tenant_time", "security_audit_events", ["tenant_id", "occurred_at"]
    )

    op.create_index(
        "ix_security_audit_event_time", "security_audit_events", ["event_type", "occurred_at"]
    )

    op.create_index("ix_security_audit_request", "security_audit_events", ["request_id"])

    op.create_index("ix_users_email", "users", ["email"])

    op.create_index("ix_users_tenant_id", "users", ["tenant_id"])

    op.create_index("ix_tokens_user_id", "tokens", ["user_id"])

    op.create_index("ix_tokens_expires_at", "tokens", ["expires_at"])

    op.create_index("ix_service_accounts_tenant_id", "service_accounts", ["tenant_id"])

    op.create_index("ix_tokens_service_account_id", "tokens", ["service_account_id"])

    op.create_index(
        "ix_environments_tenant_project_name", "environments", ["tenant_id", "project_id", "name"]
    )

    op.create_index(
        "ix_knowledge_publications_lookup",
        "knowledge_publications",
        ["tenant_id", "project_id", "environment_id", "deployment_id"],
    )

    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_entities_metadata_trgm ON entities USING gin "
        "((lower(metadata::text)) gin_trgm_ops)"
    )

    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_entities_key_snapshot_occurrence ON entities "
        "(entity_key, snapshot_id, id)"
    )

    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_entities_name_global_prefix ON entities "
        "(lower(name) text_pattern_ops, snapshot_id, entity_key, id) WHERE name IS NOT"
        " NULL"
    )

    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_projects_key_tenant_id ON projects (key, tenant_id, id)"
    )

    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_environments_name_current_snapshot ON "
        "environments (name, tenant_id, current_snapshot_id) WHERE current_snapshot_id"
        " IS NOT NULL"
    )


def downgrade() -> None:
    op.drop_index("ix_environments_name_current_snapshot")
    op.drop_index("ix_projects_key_tenant_id")
    op.drop_index("ix_entities_name_global_prefix")
    op.drop_index("ix_entities_key_snapshot_occurrence")
    op.drop_index("ix_entities_metadata_trgm")
    op.drop_index("ix_knowledge_publications_lookup", table_name="knowledge_publications")
    op.drop_index("ix_environments_tenant_project_name", table_name="environments")
    op.drop_index("ix_tokens_service_account_id", table_name="tokens")
    op.drop_index("ix_service_accounts_tenant_id", table_name="service_accounts")
    op.drop_index("ix_tokens_expires_at", table_name="tokens")
    op.drop_index("ix_tokens_user_id", table_name="tokens")
    op.drop_index("ix_users_tenant_id", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_index("ix_security_audit_request", table_name="security_audit_events")
    op.drop_index("ix_security_audit_event_time", table_name="security_audit_events")
    op.drop_index("ix_security_audit_tenant_time", table_name="security_audit_events")
    op.drop_index("ix_relations_target_identity", table_name="relations")
    op.drop_index("ix_relations_source_identity", table_name="relations")
    op.drop_index("ix_entities_tenant_identity", table_name="entities")
    op.drop_index("ix_projects_tenant_active_snapshot", table_name="projects")
    op.drop_index("ix_entities_tenant_name_prefix_search", table_name="entities")
    op.drop_index("ix_entities_tenant_type_active_search", table_name="entities")
    op.drop_index("ix_entities_tenant_key_active_search", table_name="entities")
    op.drop_index("ix_evidence_relation", table_name="evidence")
    op.drop_index("ix_evidence_snapshot", table_name="evidence")
    op.drop_index("ix_relations_target", table_name="relations")
    op.drop_index("ix_relations_source", table_name="relations")
    op.drop_index("ix_relations_snapshot", table_name="relations")
    op.drop_index("ix_entities_project", table_name="entities")
    op.drop_index("ix_entities_snapshot_key", table_name="entities")
    op.drop_index("ix_snapshots_tenant_project_hash", table_name="snapshots")
    op.drop_index("ix_snapshots_tenant_project_revision", table_name="snapshots")
    op.drop_index("ix_projects_tenant_key", table_name="projects")
    op.drop_index("ix_tenants_key", table_name="tenants")
    op.drop_constraint(
        "fk_knowledge_publications_snapshot_tenant", "knowledge_publications", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_knowledge_publications_environment_tenant", "knowledge_publications", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_knowledge_publications_project_tenant", "knowledge_publications", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_knowledge_publications_tenant_id", "knowledge_publications", type_="foreignkey"
    )
    op.drop_constraint("fk_environments_current_snapshot", "environments", type_="foreignkey")
    op.drop_constraint("fk_environments_project_tenant", "environments", type_="foreignkey")
    op.drop_constraint("fk_environments_tenant_id", "environments", type_="foreignkey")
    op.drop_constraint(
        "fk_tokens_service_account_id_service_accounts", "tokens", type_="foreignkey"
    )
    op.drop_constraint("fk_service_accounts_tenant_id", "service_accounts", type_="foreignkey")
    op.drop_constraint("tokens_user_id_fkey", "tokens", type_="foreignkey")
    op.drop_constraint("fk_users_tenant_id", "users", type_="foreignkey")
    op.drop_constraint("fk_projects_active_snapshot", "projects", type_="foreignkey")
    op.drop_constraint("fk_evidence_relation_scope", "evidence", type_="foreignkey")
    op.drop_constraint("fk_evidence_snapshot_tenant", "evidence", type_="foreignkey")
    op.drop_constraint("fk_relations_target_entity_scope", "relations", type_="foreignkey")
    op.drop_constraint("fk_relations_source_entity_scope", "relations", type_="foreignkey")
    op.drop_constraint("fk_relations_snapshot_tenant", "relations", type_="foreignkey")
    op.drop_constraint("fk_entities_snapshot_project_tenant", "entities", type_="foreignkey")
    op.drop_constraint("fk_entities_project_tenant", "entities", type_="foreignkey")
    op.drop_constraint("fk_snapshots_project_tenant", "snapshots", type_="foreignkey")
    op.drop_constraint("fk_evidence_tenant_id", "evidence", type_="foreignkey")
    op.drop_constraint("fk_relations_tenant_id", "relations", type_="foreignkey")
    op.drop_constraint("fk_entities_tenant_id", "entities", type_="foreignkey")
    op.drop_constraint("fk_snapshots_tenant_id", "snapshots", type_="foreignkey")
    op.drop_constraint("fk_projects_tenant_id", "projects", type_="foreignkey")
