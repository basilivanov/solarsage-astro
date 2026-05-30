"""add access_ledger and referrals tables

Revision ID: 0002_add_access_ledger
Revises: dab464195b91
Create Date: 2026-05-30

W-ACCESS.1: Access service (access_ledger, referral_bonus, subscription)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '0002_add_access_ledger'
down_revision: Union[str, None] = 'dab464195b91'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create access_ledger table
    op.create_table(
        'access_ledger',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('entry_type', sa.String(50), nullable=False),
        sa.Column('days_granted', sa.Integer(), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_access_ledger_user_id', 'access_ledger', ['user_id'])

    # Create referrals table
    op.create_table(
        'referrals',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('referrer_id', sa.Uuid(), nullable=False),
        sa.Column('invitee_id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['referrer_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['invitee_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_referrals_referrer_id', 'referrals', ['referrer_id'])
    op.create_index('ix_referrals_invitee_id', 'referrals', ['invitee_id'])


def downgrade() -> None:
    op.drop_index('ix_referrals_invitee_id', 'referrals')
    op.drop_index('ix_referrals_referrer_id', 'referrals')
    op.drop_table('referrals')

    op.drop_index('ix_access_ledger_user_id', 'access_ledger')
    op.drop_table('access_ledger')
