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


class Relation(Base):
    __tablename__ = "relations"
    __table_args__ = (
        UniqueConstraint("id", "snapshot_id", "tenant_id", name="uq_relations_id_snapshot_tenant"),
        CheckConstraint("length(trim(tenant_id)) > 0", name="ck_relations_tenant_id_non_empty"),
        CheckConstraint(
            "substr(CAST(metadata AS TEXT), 1, 1) = '{'",
            name="ck_relations_metadata_object",
        ),
        ForeignKeyConstraint(
            ["snapshot_id", "tenant_id"],
            ["snapshots.id", "snapshots.tenant_id"],
            name="fk_relations_snapshot_tenant",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["source_entity_id", "snapshot_id", "tenant_id"],
            ["entities.id", "entities.snapshot_id", "entities.tenant_id"],
            name="fk_relations_source_entity_scope",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["target_entity_id", "snapshot_id", "tenant_id"],
            ["entities.id", "entities.snapshot_id", "entities.tenant_id"],
            name="fk_relations_target_entity_scope",
            ondelete="CASCADE",
        ),
        CheckConstraint(
            "provenance_kind IN ('declared', 'inferred', 'observed', 'manual')",
            name="ck_relations_provenance_kind",
        ),
        Index("ix_relations_snapshot", "tenant_id", "snapshot_id"),
        Index("ix_relations_source", "tenant_id", "snapshot_id", "source_entity_id"),
        Index("ix_relations_target", "tenant_id", "snapshot_id", "target_entity_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[str] = mapped_column(String(255), nullable=False)
    snapshot_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    source_entity_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    target_entity_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    relation_type: Mapped[str] = mapped_column(String(64), nullable=False)
    provenance_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSON_OBJECT, nullable=False, default=dict, server_default=text("'{}'")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
