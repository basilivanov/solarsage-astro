"""add_is_onboarded_to_user_profiles

Revision ID: dab464195b91
Revises: 0001_users
Create Date: 2026-05-30 13:30:28.459837

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'dab464195b91'
down_revision: Union[str, None] = '0001_users'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # W-1.3: Add is_onboarded column to user_profiles
    op.add_column(
        'user_profiles',
        sa.Column('is_onboarded', sa.Boolean(), nullable=False, server_default='false')
    )


def downgrade() -> None:
    # W-1.3: Remove is_onboarded column from user_profiles
    op.drop_column('user_profiles', 'is_onboarded')
