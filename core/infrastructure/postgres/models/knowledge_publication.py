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
from .tenant_id import TenantId
from .types import JSON_OBJECT


class KnowledgePublication(Base):
    __tablename__ = "knowledge_publications"
    __table_args__ = (
        UniqueConstraint("id", "tenant_id", name="uq_knowledge_publications_id_tenant"),
        UniqueConstraint(
            "tenant_id",
            "project_id",
            "environment_id",
            "deployment_id",
            name="uq_knowledge_publications_tenant_project_env_deploy",
        ),
        CheckConstraint(
            "length(trim(deployment_id)) > 0",
            name="ck_knowledge_publications_deployment_id_non_empty",
        ),
        CheckConstraint(
            "substr(CAST(metadata AS TEXT), 1, 1) = '{'",
            name="ck_knowledge_publications_metadata_object",
        ),
        ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_knowledge_publications_tenant_id",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["project_id", "tenant_id"],
            ["projects.id", "projects.tenant_id"],
            name="fk_knowledge_publications_project_tenant",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["environment_id", "tenant_id"],
            ["environments.id", "environments.tenant_id"],
            name="fk_knowledge_publications_environment_tenant",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["snapshot_id", "tenant_id"],
            ["snapshots.id", "snapshots.tenant_id"],
            name="fk_knowledge_publications_snapshot_tenant",
            ondelete="SET NULL",
        ),
        Index(
            "ix_knowledge_publications_lookup",
            "tenant_id",
            "project_id",
            "environment_id",
            "deployment_id",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(TenantId(as_uuid=True), nullable=False)
    project_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    environment_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    deployment_id: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING")
    snapshot_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSON_OBJECT, nullable=False, default=dict, server_default=text("'{}'")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
