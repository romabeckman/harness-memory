from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    Uuid,
    func,
    case,
    select,
    text,
)
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base
from .environment import Environment
from .tenant_id import TenantId
from .types import JSON_OBJECT


class Project(Base):
    __tablename__ = "projects"
    __table_args__ = (
        UniqueConstraint("id", "tenant_id", name="uq_projects_id_tenant"),
        UniqueConstraint("key", name="uq_projects_key"),
        UniqueConstraint("tenant_id", "key", name="uq_projects_tenant_key"),
        CheckConstraint(
            "length(trim(CAST(tenant_id AS TEXT))) > 0",
            name="ck_projects_tenant_id_non_empty",
        ),
        CheckConstraint(
            "substr(CAST(metadata AS TEXT), 1, 1) = '{'",
            name="ck_projects_metadata_object",
        ),
        Index("ix_projects_tenant_key", "tenant_id", "key"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(
        TenantId(as_uuid=True),
        ForeignKey("tenants.id", ondelete="RESTRICT", name="fk_projects_tenant_id"),
        nullable=False,
    )
    key: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    environments: Mapped[list[Environment]] = relationship(Environment)

    @hybrid_property
    def active_snapshot_id(self) -> UUID | None:
        """Resolve the preferred current environment snapshot for legacy callers."""
        environments = sorted(
            self.environments,
            key=lambda env: (env.current_snapshot_id is None, env.type != "production", env.name),
        )
        return environments[0].current_snapshot_id if environments else None

    @active_snapshot_id.setter
    def active_snapshot_id(self, snapshot_id: UUID | None) -> None:
        environment = next((env for env in self.environments if env.name == "production"), None)
        if environment is None:
            environment = Environment(name="production", type="production", metadata_json={})
            self.environments.append(environment)
        environment.current_snapshot_id = snapshot_id

    @active_snapshot_id.expression
    def active_snapshot_id(cls):
        return (
            select(Environment.current_snapshot_id)
            .where(Environment.project_id == cls.id, Environment.tenant_id == cls.tenant_id)
            .order_by(
                case((Environment.current_snapshot_id.is_not(None), 0), else_=1),
                case((Environment.type == "production", 0), else_=1),
                Environment.name,
            )
            .limit(1)
            .correlate(cls)
            .scalar_subquery()
        )

    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSON_OBJECT, nullable=False, default=dict, server_default=text("'{}'")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
