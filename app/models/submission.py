from typing import TYPE_CHECKING
from datetime import datetime, timezone

from sqlalchemy import (
    String,
    Text,
    DateTime,
    ForeignKey,
    JSON,
    Index
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.widget import Widget


class Submission(Base):
    __tablename__ = "submissions"

    id: Mapped[int] = mapped_column(primary_key=True)

    widget_id: Mapped[int] = mapped_column(
        ForeignKey("widgets.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    data: Mapped[dict] = mapped_column(
        JSON,
        nullable=False
    )

    ip_address: Mapped[str | None] = mapped_column(
        String(45),
        nullable=True
    )

    country: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )

    city: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )

    geo_provider: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )

    widget: Mapped["Widget"] = relationship(
        back_populates="submissions"
    )

    __table_args__ = (
        Index(
            "ix_submissions_widget_created_at",
            "widget_id",
            "created_at"
        ),
    )