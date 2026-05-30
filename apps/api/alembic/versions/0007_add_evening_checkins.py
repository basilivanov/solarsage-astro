"""add evening_checkins table

Revision ID: 0007_add_evening_checkins
Revises: 0006_add_payments
Create Date: 2026-05-30

W-8.1: Evening checkin table.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = '0007_add_evening_checkins'
down_revision: Union[str, None] = '0006_add_payments'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'evening_checkins',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), nullable=False),
        sa.Column('target_date', sa.Date(), nullable=False),
        sa.Column('mood', sa.String(50), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'target_date', name='uq_checkin_user_date')
    )
    op.create_index('ix_evening_checkins_user_id', 'evening_checkins', ['user_id'])
    op.create_index('ix_evening_checkins_target_date', 'evening_checkins', ['target_date'])


def downgrade() -> None:
    op.drop_index('ix_evening_checkins_target_date', 'evening_checkins')
    op.drop_index('ix_evening_checkins_user_id', 'evening_checkins')
    op.drop_table('evening_checkins')
