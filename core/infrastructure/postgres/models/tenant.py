from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base
from .tenant_id import TenantId
from .types import JSON_OBJECT


class Tenant(Base):
    __tablename__ = "tenants"
    __table_args__ = (
        UniqueConstraint("key", name="uq_tenants_key"),
        CheckConstraint("length(trim(key)) > 0", name="ck_tenants_key_non_empty"),
        CheckConstraint("status IN ('active', 'disabled')", name="ck_tenants_status_valid"),
        CheckConstraint(
            "substr(CAST(metadata AS TEXT), 1, 1) = '{'",
            name="ck_tenants_metadata_object",
        ),
    )

    id: Mapped[UUID] = mapped_column(TenantId(as_uuid=True), primary_key=True, default=uuid4)
    key: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active", server_default="active")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSON_OBJECT, nullable=False, default=dict, server_default=text("'{}'")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
