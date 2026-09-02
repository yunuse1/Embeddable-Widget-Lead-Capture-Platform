"""Add submission idempotency key

Revision ID: 9a7e6b5c4d3e
Revises: 8f31c4a7d2b9
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "9a7e6b5c4d3e"
down_revision: Union[str, Sequence[str], None] = "8f31c4a7d2b9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "submissions",
        sa.Column("idempotency_key", sa.String(length=255), nullable=True),
    )
    op.create_unique_constraint(
        "uq_submissions_widget_idempotency_key",
        "submissions",
        ["widget_id", "idempotency_key"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_submissions_widget_idempotency_key",
        "submissions",
        type_="unique",
    )
    op.drop_column("submissions", "idempotency_key")
