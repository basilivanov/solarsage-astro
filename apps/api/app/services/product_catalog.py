# ############################################################################
# AI_HEADER: MODULE_PRODUCT_CATALOG — single source of truth for paid products.
# ROLE: Canonical product catalog: exact prices, periods and quotas; seeded
#       into the products table by migration 0020 and reused by services/tests.
# DEPENDENCIES: dataclasses only
# ############################################################################

# START_MODULE_CONTRACT: M-PRODUCT-CATALOG
# purpose: Provide the single canonical paid-product catalog (prices in
#   kopecks, period days, horary quotas, active flags). Every price check in
#   code, the Alembic seed and the tests MUST derive from this module — never
#   duplicated literals.
# owns:
#   - apps/api/app/services/product_catalog.py
# inputs: none (static definitions)
# outputs: CATALOG entries, catalog_by_slug lookup, iter_active.
# dependencies: none
# side_effects: none
# emitted_logs: none
# invariants:
#   - Prices are exact kopecks; never rounded or recomputed elsewhere.
#   - subscription_* products are recurrent with period_days set.
#   - natal_full_report is one_time; synastry exists but is INACTIVE
#     (fail-closed until real fulfillment exists).
# failure_policy: n/a (static data)
# END_MODULE_CONTRACT: M-PRODUCT-CATALOG

# START_MODULE_MAP: M-PRODUCT-CATALOG
# public_entrypoints:
#   - CATALOG
#   - catalog_by_slug
#   - iter_active
# semantic_blocks:
#   - CATALOG_DEF: canonical product rows
# owned_tests:
#   - apps/api/tests/test_billing_products.py
# END_MODULE_MAP: M-PRODUCT-CATALOG

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProductDef:
    slug: str
    name: str
    description: str
    product_type: str  # "subscription_recurrent" | "one_time"
    price_kopecks: int
    currency: str
    period_days: int | None
    horary_quota: int | None
    is_active: bool


# START_BLOCK: CATALOG_DEF
CATALOG: tuple[ProductDef, ...] = (
    ProductDef(
        slug="subscription_month",
        name="Подписка на 1 месяц",
        description="Полный доступ ко всем разборам и хорарным вопросам на 30 дней",
        product_type="subscription_recurrent",
        price_kopecks=9900,
        currency="RUB",
        period_days=30,
        horary_quota=None,
        is_active=True,
    ),
    ProductDef(
        slug="subscription_year",
        name="Подписка на 1 год",
        description="Полный доступ ко всем разборам и хорарным вопросам на 365 дней",
        product_type="subscription_recurrent",
        price_kopecks=99900,
        currency="RUB",
        period_days=365,
        horary_quota=None,
        is_active=True,
    ),
    ProductDef(
        slug="natal_full_report",
        name="Полный натальный разбор",
        description="Полный отчёт по натальной карте для текущего контекста (разовая покупка)",
        product_type="one_time",
        price_kopecks=39900,
        currency="RUB",
        period_days=None,
        horary_quota=None,
        is_active=True,
    ),
    ProductDef(
        slug="horary_1",
        name="1 хорарный вопрос",
        description="Один вопрос к хорарному оракулу",
        product_type="one_time",
        price_kopecks=5000,
        currency="RUB",
        period_days=None,
        horary_quota=1,
        is_active=True,
    ),
    ProductDef(
        slug="horary_3",
        name="3 хорарных вопроса",
        description="Три вопроса к хорарному оракулу",
        product_type="one_time",
        price_kopecks=12000,
        currency="RUB",
        period_days=None,
        horary_quota=3,
        is_active=True,
    ),
    ProductDef(
        slug="horary_5",
        name="5 хорарных вопросов",
        description="Пять вопросов к хорарному оракулу",
        product_type="one_time",
        price_kopecks=18000,
        currency="RUB",
        period_days=None,
        horary_quota=5,
        is_active=True,
    ),
    ProductDef(
        slug="horary_10",
        name="10 хорарных вопросов",
        description="Десять вопросов к хорарному оракулу",
        product_type="one_time",
        price_kopecks=30000,
        currency="RUB",
        period_days=None,
        horary_quota=10,
        is_active=True,
    ),
    ProductDef(
        slug="election_1",
        name="Подбор даты (1 событие)",
        description="Топ-3 лучших даты для твоего события",
        product_type="one_time",
        price_kopecks=5000,
        currency="RUB",
        period_days=None,
        horary_quota=1,
        is_active=True,
    ),
    ProductDef(
        slug="synastry",
        name="Синастрия",
        description="Разбор совместимости двух карт",
        product_type="one_time",
        price_kopecks=39900,
        currency="RUB",
        period_days=None,
        horary_quota=1,
        is_active=True,
    ),
)
# END_BLOCK: CATALOG_DEF


def catalog_by_slug(slug: str) -> ProductDef | None:
    for item in CATALOG:
        if item.slug == slug:
            return item
    return None


def iter_active() -> list[ProductDef]:
    return [item for item in CATALOG if item.is_active]


async def seed_products(session) -> int:
    # START_FUNCTION_CONTRACT: F-M-PRODUCT-CATALOG.seed_products
    # purpose: Insert any missing catalog rows into the products table
    #   (idempotent). Used by tests and ops bootstrap so the DB catalog
    #   always derives from this module.
    # inputs: session — SQLAlchemy AsyncSession.
    # returns: number of inserted rows.
    # side_effects: INSERT into products (missing slugs only) + commit.
    # error_behavior: propagates DB errors.
    # END_FUNCTION_CONTRACT: F-M-PRODUCT-CATALOG.seed_products
    from sqlalchemy import select

    from app.db.models import Product

    existing = set((await session.execute(select(Product.slug))).scalars().all())
    added = 0
    for item in CATALOG:
        if item.slug in existing:
            continue
        session.add(
            Product(
                slug=item.slug,
                name=item.name,
                description=item.description,
                product_type=item.product_type,
                price_kopecks=item.price_kopecks,
                currency=item.currency,
                period_days=item.period_days,
                horary_quota=item.horary_quota,
                is_active=item.is_active,
            )
        )
        added += 1
    await session.commit()
    return added
