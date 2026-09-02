from typing import TYPE_CHECKING
from datetime import datetime, timezone

from sqlalchemy import (
    String,
    Text,
    DateTime,
    ForeignKey,
    JSON,
    Boolean,
    Index
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.submission import Submission
    from app.models.tenant import Tenant


class Widget(Base):
    __tablename__ = "widgets"

    id: Mapped[int] = mapped_column(primary_key=True)

    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    public_id: Mapped[str] = mapped_column(
        String(32),
        unique=True,
        nullable=False,
        index=True
    )

    widget_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False
    )

    title: Mapped[str] = mapped_column(
        String(150),
        nullable=False
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    button_text: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="Submit"
    )

    fields: Mapped[list] = mapped_column(
        JSON,
        nullable=False,
        default=list
    )

    display_options: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        default=dict
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    tenant: Mapped["Tenant"] = relationship(
        back_populates="widgets"
    )

    submissions: Mapped[list["Submission"]] = relationship(
        back_populates="widget",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_widgets_tenant_id_public_id", "tenant_id", "public_id"),
    )