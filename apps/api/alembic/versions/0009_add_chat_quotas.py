# AI_HEADER
# module: M-MIGRATION-0009
# wave: W-CHAT-4
# purpose: Add chat_quotas table

"""add chat_quotas table

Revision ID: 0009_add_chat_quotas
Revises: 0008_add_chat_tables
Create Date: 2026-05-30

W-CHAT-4: Chat quota tracking.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = '0009_add_chat_quotas'
down_revision = '0008_add_chat_tables'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'chat_quotas',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), nullable=False),
        sa.Column('messages_used', sa.Integer(), nullable=False),
        sa.Column('messages_limit', sa.Integer(), nullable=False),
        sa.Column('reset_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', name='uq_chat_quota_user')
    )


def downgrade() -> None:
    op.drop_table('chat_quotas')
