"""add semantic_layers table

Revision ID: 0004_add_semantic
Revises: 0003_add_cache
Create Date: 2026-05-30

W-4.3: Semantic layer cache
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '0004_add_semantic'
down_revision: Union[str, None] = '0003_add_cache'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'semantic_layers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('target_date', sa.Date(), nullable=False),
        sa.Column('semantic_json', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'target_date', name='uq_semantic_user_date')
    )
    op.create_index('ix_semantic_layers_user_id', 'semantic_layers', ['user_id'])
    op.create_index('ix_semantic_layers_target_date', 'semantic_layers', ['target_date'])


def downgrade() -> None:
    op.drop_index('ix_semantic_layers_target_date', 'semantic_layers')
    op.drop_index('ix_semantic_layers_user_id', 'semantic_layers')
    op.drop_table('semantic_layers')
