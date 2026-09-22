from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base
from .tenant_id import TenantId
from .types import JSON_OBJECT


class Snapshot(Base):
    __tablename__ = "snapshots"
    __table_args__ = (
        UniqueConstraint("id", "tenant_id", name="uq_snapshots_id_tenant"),
        UniqueConstraint("id", "project_id", "tenant_id", name="uq_snapshots_id_project_tenant"),
        UniqueConstraint(
            "tenant_id",
            "project_id",
            "environment_id",
            "revision",
            name="uq_snapshots_tenant_project_environment_revision",
        ),
        UniqueConstraint(
            "tenant_id",
            "project_id",
            "environment_id",
            "payload_hash",
            name="uq_snapshots_tenant_project_environment_payload_hash",
        ),
        CheckConstraint(
            "substr(CAST(metadata AS TEXT), 1, 1) = '{'",
            name="ck_snapshots_metadata_object",
        ),
        CheckConstraint(
            "substr(CAST(payload AS TEXT), 1, 1) = '{'",
            name="ck_snapshots_payload_object",
        ),
        ForeignKeyConstraint(
            ["project_id", "tenant_id"],
            ["projects.id", "projects.tenant_id"],
            name="fk_snapshots_project_tenant",
            ondelete="CASCADE",
        ),
        Index("ix_snapshots_tenant_project_revision", "tenant_id", "project_id", "revision"),
        Index("ix_snapshots_tenant_project_hash", "tenant_id", "project_id", "payload_hash"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(
        TenantId(as_uuid=True),
        ForeignKey("tenants.id", ondelete="RESTRICT", name="fk_snapshots_tenant_id"),
        nullable=False,
    )
    project_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    environment_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    publication_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    schema_version: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSON_OBJECT, nullable=False, default=dict, server_default=text("'{}'")
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSON_OBJECT, nullable=False, default=dict, server_default=text("'{}'")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
