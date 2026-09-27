from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class ProjectLinkModel(Base):
    __tablename__ = "project_links"
    __table_args__ = (
        CheckConstraint(
            "project_a_id <> project_b_id",
            name="ck_project_links_distinct_projects",
        ),
        UniqueConstraint(
            "project_a_id",
            "project_b_id",
            name="uq_project_links_a_b",
        ),
        Index("ix_project_links_project_a_id", "project_a_id"),
        Index("ix_project_links_project_b_id", "project_b_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    project_a_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE", name="fk_project_links_project_a_id"),
        nullable=False,
    )
    project_b_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE", name="fk_project_links_project_b_id"),
        nullable=False,
    )
    created_by: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL", name="fk_project_links_created_by"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
    )
