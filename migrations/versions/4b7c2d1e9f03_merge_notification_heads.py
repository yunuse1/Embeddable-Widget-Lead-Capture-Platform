"""Merge notification migration heads

Revision ID: 4b7c2d1e9f03
Revises: 3a7e91c4d8f2, 9a7e6b5c4d3e
"""
from typing import Sequence, Union


revision: str = "4b7c2d1e9f03"
down_revision: Union[str, Sequence[str], None] = (
    "3a7e91c4d8f2",
    "9a7e6b5c4d3e",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
