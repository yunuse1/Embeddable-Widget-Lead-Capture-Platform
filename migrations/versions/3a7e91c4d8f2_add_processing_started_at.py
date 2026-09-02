"""Add processing start timestamp to notification jobs

Revision ID: 3a7e91c4d8f2
Revises: 8f31c4a7d2b9
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "3a7e91c4d8f2"
down_revision: Union[str, Sequence[str], None] = "8f31c4a7d2b9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "notification_jobs",
        sa.Column("processing_started_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_notification_jobs_processing_started_at",
        "notification_jobs",
        ["processing_started_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_notification_jobs_processing_started_at",
        table_name="notification_jobs",
    )
    op.drop_column("notification_jobs", "processing_started_at")
