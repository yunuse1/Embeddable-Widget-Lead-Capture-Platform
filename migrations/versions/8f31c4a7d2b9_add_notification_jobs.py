"""Add notification jobs table

Revision ID: 8f31c4a7d2b9
Revises: 7d4c1b9e2a11
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "8f31c4a7d2b9"
down_revision: Union[str, Sequence[str], None] = "7d4c1b9e2a11"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "notification_jobs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("submission_id", sa.Integer(), nullable=False),
        sa.Column("job_type", sa.String(length=30), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["submission_id"], ["submissions.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_notification_jobs_submission_id",
        "notification_jobs",
        ["submission_id"],
        unique=False,
    )
    op.create_index(
        "ix_notification_jobs_status",
        "notification_jobs",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_notification_jobs_available_at",
        "notification_jobs",
        ["available_at"],
        unique=False,
    )
    op.create_index(
        "ix_notification_jobs_status_available_at",
        "notification_jobs",
        ["status", "available_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_notification_jobs_status_available_at", table_name="notification_jobs")
    op.drop_index("ix_notification_jobs_available_at", table_name="notification_jobs")
    op.drop_index("ix_notification_jobs_status", table_name="notification_jobs")
    op.drop_index("ix_notification_jobs_submission_id", table_name="notification_jobs")
    op.drop_table("notification_jobs")
