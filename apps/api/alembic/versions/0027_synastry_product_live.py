"""Update products.synastry to live one_time product for 399.00 RUB (horary_quota=1).

Revision ID: 0027_synastry_product_live
Revises: 0026_synastry_spend_request_hash
"""

from alembic import op
import sqlalchemy as sa

revision = "0027_synastry_product_live"
down_revision = "0026_synastry_spend_request_hash"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    res = conn.execute(
        sa.text(
            """
            UPDATE products
            SET is_active = true,
                product_type = 'one_time',
                price_kopecks = 39900,
                currency = 'RUB',
                horary_quota = 1,
                name = 'Синастрия',
                description = 'Разбор совместимости двух карт'
            WHERE slug = 'synastry';
            """
        )
    )
    if res.rowcount != 1:
        raise RuntimeError(f"Expected exactly 1 row updated for product 'synastry', got {res.rowcount}")


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            UPDATE products
            SET is_active = false
            WHERE slug = 'synastry';
            """
        )
    )
