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
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base
from .types import JSON_OBJECT


class Project(Base):
    __tablename__ = "projects"
    __table_args__ = (
        UniqueConstraint("id", "tenant_id", name="uq_projects_id_tenant"),
        UniqueConstraint("tenant_id", "key", name="uq_projects_tenant_key"),
        CheckConstraint("length(trim(tenant_id)) > 0", name="ck_projects_tenant_id_non_empty"),
        CheckConstraint(
            "substr(CAST(metadata AS TEXT), 1, 1) = '{'",
            name="ck_projects_metadata_object",
        ),
        ForeignKeyConstraint(
            ["active_snapshot_id", "id", "tenant_id"],
            ["snapshots.id", "snapshots.project_id", "snapshots.tenant_id"],
            name="fk_projects_active_snapshot",
            deferrable=True,
            initially="DEFERRED",
            ondelete="SET NULL",
        ),
        Index("ix_projects_tenant_key", "tenant_id", "key"),
        Index(
            "ix_projects_tenant_active_snapshot",
            "tenant_id",
            "active_snapshot_id",
            "id",
            postgresql_where=text("active_snapshot_id IS NOT NULL"),
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[str] = mapped_column(String(255), nullable=False)
    key: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    active_snapshot_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSON_OBJECT, nullable=False, default=dict, server_default=text("'{}'")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
