"""baseline (no tables yet)

Revision ID: 0000_baseline
Revises:
Create Date: 2026-05-24 00:00:00

W-1.1 baseline: empty migration so `alembic upgrade head` succeeds against
a fresh database. Tables are introduced in W-1.2 onward.
"""
from typing import Sequence, Union

revision: str = "0000_baseline"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
