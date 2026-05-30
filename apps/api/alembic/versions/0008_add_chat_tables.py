"""add chat_threads and chat_messages tables

Revision ID: 0008_add_chat_tables
Revises: 0007_add_evening_checkins
Create Date: 2026-05-30

W-CHAT-1: Chat backend storage.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = '0008_add_chat_tables'
down_revision: Union[str, None] = '0007_add_evening_checkins'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # chat_threads
    op.create_table(
        'chat_threads',
        sa.Column('id', UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_chat_threads_user_id', 'chat_threads', ['user_id'])

    # chat_messages
    op.create_table(
        'chat_messages',
        sa.Column('id', UUID(as_uuid=True), nullable=False),
        sa.Column('thread_id', UUID(as_uuid=True), nullable=False),
        sa.Column('role', sa.String(20), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['thread_id'], ['chat_threads.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_chat_messages_thread_id', 'chat_messages', ['thread_id'])


def downgrade() -> None:
    op.drop_index('ix_chat_messages_thread_id', 'chat_messages')
    op.drop_table('chat_messages')
    op.drop_index('ix_chat_threads_user_id', 'chat_threads')
    op.drop_table('chat_threads')
