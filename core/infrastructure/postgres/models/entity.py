from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Index,
    String,
    UniqueConstraint,
    Uuid,
    column,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base
from .types import JSON_OBJECT


class Entity(Base):
    __tablename__ = "entities"
    __table_args__ = (
        UniqueConstraint("id", "snapshot_id", "tenant_id", name="uq_entities_id_snapshot_tenant"),
        UniqueConstraint("tenant_id", "snapshot_id", "entity_key", name="uq_entities_snapshot_key"),
        CheckConstraint("length(trim(tenant_id)) > 0", name="ck_entities_tenant_id_non_empty"),
        CheckConstraint(
            "substr(CAST(metadata AS TEXT), 1, 1) = '{'",
            name="ck_entities_metadata_object",
        ),
        ForeignKeyConstraint(
            ["project_id", "tenant_id"],
            ["projects.id", "projects.tenant_id"],
            name="fk_entities_project_tenant",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["snapshot_id", "project_id", "tenant_id"],
            ["snapshots.id", "snapshots.project_id", "snapshots.tenant_id"],
            name="fk_entities_snapshot_project_tenant",
            ondelete="CASCADE",
        ),
        Index("ix_entities_snapshot_key", "tenant_id", "snapshot_id", "entity_key"),
        Index("ix_entities_project", "tenant_id", "project_id"),
        Index("ix_entities_tenant_identity", "tenant_id", "identity_id", "snapshot_id"),
        Index(
            "ix_entities_tenant_key_active_search",
            "tenant_id",
            "entity_key",
            "snapshot_id",
            "id",
        ),
        Index(
            "ix_entities_tenant_type_active_search",
            "tenant_id",
            "entity_type",
            "snapshot_id",
            "entity_key",
            "id",
        ),
        Index(
            "ix_entities_tenant_name_prefix_search",
            "tenant_id",
            func.lower(column("name")).label("name_lower"),
            "snapshot_id",
            "entity_key",
            "id",
            postgresql_ops={"name_lower": "text_pattern_ops"},
            postgresql_where=text("name IS NOT NULL"),
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[str] = mapped_column(String(255), nullable=False)
    identity_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    project_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    snapshot_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    entity_key: Mapped[str] = mapped_column(String(255), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSON_OBJECT, nullable=False, default=dict, server_default=text("'{}'")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
