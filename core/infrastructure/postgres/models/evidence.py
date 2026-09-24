from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base
from .tenant_id import TenantId
from .types import JSON_OBJECT


class Evidence(Base):
    __tablename__ = "evidence"
    __table_args__ = (
        CheckConstraint(
            "substr(CAST(metadata AS TEXT), 1, 1) = '{'",
            name="ck_evidence_metadata_object",
        ),
        ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_evidence_tenant_id",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["snapshot_id", "tenant_id"],
            ["snapshots.id", "snapshots.tenant_id"],
            name="fk_evidence_snapshot_tenant",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["relation_id", "snapshot_id", "tenant_id"],
            ["relations.id", "relations.snapshot_id", "relations.tenant_id"],
            name="fk_evidence_relation_scope",
            ondelete="CASCADE",
        ),
        Index("ix_evidence_snapshot", "tenant_id", "snapshot_id"),
        Index("ix_evidence_relation", "tenant_id", "snapshot_id", "relation_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(TenantId(as_uuid=True), nullable=False)
    snapshot_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    relation_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    source: Mapped[str] = mapped_column(String(1024), nullable=False)
    excerpt: Mapped[str | None] = mapped_column(String(4096), nullable=True)
    graph_position: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSON_OBJECT, nullable=False, default=dict, server_default=text("'{}'")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
