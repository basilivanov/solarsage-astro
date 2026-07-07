"""extend evening checkins for real check-in flow

Revision ID: 0017
Revises: 0016
Create Date: 2026-07-06
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("evening_checkins") as batch_op:
        batch_op.add_column(sa.Column("mood_score", sa.SmallInteger(), nullable=True))
        batch_op.add_column(sa.Column("accuracy", sa.SmallInteger(), nullable=True))
        batch_op.add_column(sa.Column("energy", sa.SmallInteger(), nullable=True))
        batch_op.add_column(
            sa.Column("tags_json", sa.Text(), nullable=False, server_default="[]"),
        )
        batch_op.add_column(sa.Column("note", sa.Text(), nullable=True))
        batch_op.add_column(
            sa.Column("streak", sa.Integer(), nullable=False, server_default="0"),
        )
        batch_op.add_column(sa.Column("filled_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("CURRENT_TIMESTAMP"),
                nullable=False,
            ),
        )
        batch_op.create_check_constraint(
            "ck_evening_checkins_mood_score_range",
            "mood_score IS NULL OR (mood_score >= 1 AND mood_score <= 5)",
        )
        batch_op.create_check_constraint(
            "ck_evening_checkins_accuracy_range",
            "accuracy IS NULL OR (accuracy >= 1 AND accuracy <= 3)",
        )
        batch_op.create_check_constraint(
            "ck_evening_checkins_energy_range",
            "energy IS NULL OR (energy >= 1 AND energy <= 5)",
        )

    op.execute(
        """
        UPDATE evening_checkins
        SET
            mood_score = CASE mood
                WHEN 'great' THEN 5
                WHEN 'good' THEN 4
                WHEN 'neutral' THEN 3
                WHEN 'bad' THEN 2
                ELSE NULL
            END,
            note = notes,
            filled_at = created_at,
            updated_at = created_at
        WHERE mood_score IS NULL
        """
    )

def downgrade() -> None:
    with op.batch_alter_table("evening_checkins") as batch_op:
        batch_op.drop_constraint("ck_evening_checkins_energy_range", type_="check")
        batch_op.drop_constraint("ck_evening_checkins_accuracy_range", type_="check")
        batch_op.drop_constraint("ck_evening_checkins_mood_score_range", type_="check")
        batch_op.drop_column("updated_at")
        batch_op.drop_column("filled_at")
        batch_op.drop_column("streak")
        batch_op.drop_column("note")
        batch_op.drop_column("tags_json")
        batch_op.drop_column("energy")
        batch_op.drop_column("accuracy")
        batch_op.drop_column("mood_score")
