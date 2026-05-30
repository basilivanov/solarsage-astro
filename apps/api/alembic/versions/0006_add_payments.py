"""add payments table

Revision ID: 0006_add_payments
Revises: 0005_add_microcopy_misses
Create Date: 2026-05-30

W-6.1: Payment transactions table for Telegram Payments integration.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = '0006_add_payments'
down_revision: Union[str, None] = '0005_add_microcopy_misses'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'payments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), nullable=False),
        sa.Column('amount', sa.Integer(), nullable=False),
        sa.Column('currency', sa.String(3), nullable=False),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('provider', sa.String(50), nullable=False),
        sa.Column('provider_payment_id', sa.String(255), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_payments_user_id', 'payments', ['user_id'])


def downgrade() -> None:
    op.drop_index('ix_payments_user_id', 'payments')
    op.drop_table('payments')
