"""add profile locations (current + birthday)

Revision ID: 0010_add_profile_locations
Revises: 0009_add_chat_quotas
"""

from alembic import op
import sqlalchemy as sa

revision = "0010_add_profile_locations"
down_revision = "0009_add_chat_quotas"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("user_profiles", sa.Column("current_city", sa.String(200), nullable=True))
    op.add_column("user_profiles", sa.Column("current_lat", sa.Numeric(8, 5), nullable=True))
    op.add_column("user_profiles", sa.Column("current_lon", sa.Numeric(9, 5), nullable=True))
    op.add_column("user_profiles", sa.Column("current_tz", sa.String(64), nullable=True))
    op.add_column("user_profiles", sa.Column("birthday_city", sa.String(200), nullable=True))
    op.add_column("user_profiles", sa.Column("birthday_lat", sa.Numeric(8, 5), nullable=True))
    op.add_column("user_profiles", sa.Column("birthday_lon", sa.Numeric(9, 5), nullable=True))
    op.add_column("user_profiles", sa.Column("birthday_tz", sa.String(64), nullable=True))

    op.execute(
        """
        UPDATE user_profiles
        SET current_city = birth_city,
            current_lat = birth_lat,
            current_lon = birth_lon,
            current_tz  = birth_tz,
            birthday_city = birth_city,
            birthday_lat = birth_lat,
            birthday_lon = birth_lon,
            birthday_tz  = birth_tz
        """
    )

    op.create_check_constraint(
        "ck_user_profiles_current_lat_range",
        "user_profiles",
        "current_lat IS NULL OR (current_lat >= -90 AND current_lat <= 90)",
    )
    op.create_check_constraint(
        "ck_user_profiles_current_lon_range",
        "user_profiles",
        "current_lon IS NULL OR (current_lon >= -180 AND current_lon <= 180)",
    )
    op.create_check_constraint(
        "ck_user_profiles_birthday_lat_range",
        "user_profiles",
        "birthday_lat IS NULL OR (birthday_lat >= -90 AND birthday_lat <= 90)",
    )
    op.create_check_constraint(
        "ck_user_profiles_birthday_lon_range",
        "user_profiles",
        "birthday_lon IS NULL OR (birthday_lon >= -180 AND birthday_lon <= 180)",
    )


def downgrade() -> None:
    op.drop_constraint("ck_user_profiles_current_lat_range", "user_profiles")
    op.drop_constraint("ck_user_profiles_current_lon_range", "user_profiles")
    op.drop_constraint("ck_user_profiles_birthday_lat_range", "user_profiles")
    op.drop_constraint("ck_user_profiles_birthday_lon_range", "user_profiles")
    op.drop_column("user_profiles", "birthday_tz")
    op.drop_column("user_profiles", "birthday_lon")
    op.drop_column("user_profiles", "birthday_lat")
    op.drop_column("user_profiles", "birthday_city")
    op.drop_column("user_profiles", "current_tz")
    op.drop_column("user_profiles", "current_lon")
    op.drop_column("user_profiles", "current_lat")
    op.drop_column("user_profiles", "current_city")