"""add microcopy_misses table

Revision ID: 0005_add_microcopy_misses
Revises: 0004_add_semantic
Create Date: 2026-05-30

W-9.2: Microcopy miss tracking
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '0005_add_microcopy_misses'
down_revision: Union[str, None] = '0004_add_semantic'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'microcopy_misses',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('key', sa.String(255), nullable=False),
        sa.Column('context', sa.Text(), nullable=True),
        sa.Column('first_seen', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('last_seen', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('hit_count', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_microcopy_misses_key', 'microcopy_misses', ['key'])


def downgrade() -> None:
    op.drop_index('ix_microcopy_misses_key', 'microcopy_misses')
    op.drop_table('microcopy_misses')
