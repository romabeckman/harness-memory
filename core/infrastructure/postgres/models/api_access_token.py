import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, CheckConstraint, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class ApiAccessToken(Base):
    __tablename__ = "tokens"
    __table_args__ = (
        CheckConstraint(
            "(user_id IS NOT NULL AND service_account_id IS NULL) "
            "OR (user_id IS NULL AND service_account_id IS NOT NULL)",
            name="ck_token_owner_exactly_one",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )
    service_account_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("service_accounts.id", ondelete="CASCADE"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    scopes: Mapped[list[str]] = mapped_column(
        JSON, nullable=False, default=lambda: ["memory:read"]
    )
    user = relationship("ApiUser", back_populates="tokens")
    service_account = relationship("ApiServiceAccount", back_populates="tokens")
