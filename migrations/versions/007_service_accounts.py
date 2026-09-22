"""Add service accounts and allow non-expiring service-account tokens."""

import sqlalchemy as sa
from alembic import op

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "service_accounts",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], name="fk_service_accounts_tenant_id", ondelete="RESTRICT"
        ),
    )
    op.create_index("ix_service_accounts_tenant_id", "service_accounts", ["tenant_id"])

    op.drop_constraint("ck_token_expiration_window", "tokens", type_="check")
    op.alter_column("tokens", "user_id", existing_type=sa.Uuid(as_uuid=True), nullable=True)
    op.alter_column("tokens", "expires_at", existing_type=sa.DateTime(timezone=True), nullable=True)
    op.add_column("tokens", sa.Column("service_account_id", sa.Uuid(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_tokens_service_account_id_service_accounts",
        "tokens",
        "service_accounts",
        ["service_account_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_tokens_service_account_id", "tokens", ["service_account_id"])
    op.create_check_constraint(
        "ck_token_owner_exactly_one",
        "tokens",
        "(user_id IS NOT NULL AND service_account_id IS NULL) "
        "OR (user_id IS NULL AND service_account_id IS NOT NULL)",
    )
    op.create_check_constraint(
        "ck_token_expiration_window",
        "tokens",
        "expires_at IS NULL OR (expires_at > created_at "
        "AND expires_at <= created_at + INTERVAL '90 days')",
    )


def downgrade() -> None:
    connection = op.get_bind()
    has_service_accounts = connection.execute(
        sa.text("SELECT 1 FROM service_accounts LIMIT 1")
    ).first()
    if has_service_accounts:
        raise RuntimeError("Cannot downgrade while service accounts exist")

    op.drop_constraint("ck_token_expiration_window", "tokens", type_="check")
    op.drop_constraint("ck_token_owner_exactly_one", "tokens", type_="check")
    op.drop_index("ix_tokens_service_account_id", table_name="tokens")
    op.drop_constraint(
        "fk_tokens_service_account_id_service_accounts", "tokens", type_="foreignkey"
    )
    op.drop_column("tokens", "service_account_id")
    op.alter_column("tokens", "user_id", existing_type=sa.Uuid(as_uuid=True), nullable=False)
    op.alter_column(
        "tokens", "expires_at", existing_type=sa.DateTime(timezone=True), nullable=False
    )
    op.create_check_constraint(
        "ck_token_expiration_window",
        "tokens",
        "expires_at > created_at AND expires_at <= created_at + INTERVAL '90 days'",
    )
    op.drop_index("ix_service_accounts_tenant_id", table_name="service_accounts")
    op.drop_table("service_accounts")
