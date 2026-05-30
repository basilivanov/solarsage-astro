"""add today_payloads_cache table

Revision ID: 0003_add_cache
Revises: 0002_add_access_ledger
Create Date: 2026-05-30

W-5.2: Cache layer for TodayPayload
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '0003_add_cache'
down_revision: Union[str, None] = '0002_add_access_ledger'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create today_payloads_cache table
    op.create_table(
        'today_payloads_cache',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('target_date', sa.Date(), nullable=False),
        sa.Column('payload_json', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'target_date', name='uq_user_date')
    )
    op.create_index('ix_today_payloads_cache_user_id', 'today_payloads_cache', ['user_id'])
    op.create_index('ix_today_payloads_cache_target_date', 'today_payloads_cache', ['target_date'])


def downgrade() -> None:
    op.drop_index('ix_today_payloads_cache_target_date', 'today_payloads_cache')
    op.drop_index('ix_today_payloads_cache_user_id', 'today_payloads_cache')
    op.drop_table('today_payloads_cache')
