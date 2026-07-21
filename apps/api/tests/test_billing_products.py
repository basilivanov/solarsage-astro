# ############################################################################
# AI_HEADER: MODULE_TESTS_TEST_BILLING_PRODUCTS — catalog contract tests.
# ROLE: Proves the seeded products table matches the canonical CATALOG
#       exactly (prices/periods/quotas/activity) and that /api/payment/products
#       exposes only active rows with exact prices.
# ############################################################################

# START_MODULE_CONTRACT: M-TESTS-BILLING-PRODUCTS
# purpose: Guard the exact price contract of the product catalog.
# owns:
#   - apps/api/tests/test_billing_products.py
# inputs: test DB session, async client.
# outputs: assertions on catalog rows and the products endpoint.
# dependencies: product_catalog.seed_products, fixtures.
# side_effects: test DB rows only.
# emitted_logs: none.
# invariants:
#   - Exact kopeck prices: subscription_month=9900, subscription_year=99900,
#     natal_full_report=39900, horary_1/3/5/10=5000/12000/18000/30000,
#     synastry=39900 but INACTIVE (fail-closed, never listed).
# failure_policy: assertion failure.
# END_MODULE_CONTRACT: M-TESTS-BILLING-PRODUCTS

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.db.models import Product
from app.services.product_catalog import CATALOG, seed_products


@pytest.mark.asyncio
async def test_seeded_catalog_matches_canonical_prices(db_session) -> None:
    await seed_products(db_session)
    rows = {
        p.slug: p
        for p in (await db_session.execute(select(Product))).scalars().all()
    }
    expected = {p.slug: p for p in CATALOG}
    assert set(rows) == set(expected)
    for slug, row in rows.items():
        canon = expected[slug]
        assert row.price_kopecks == canon.price_kopecks, slug
        assert row.currency == canon.currency, slug
        assert row.period_days == canon.period_days, slug
        assert row.horary_quota == canon.horary_quota, slug
        assert row.is_active == canon.is_active, slug

    assert rows["subscription_month"].price_kopecks == 9900
    assert rows["subscription_month"].period_days == 30
    assert rows["subscription_year"].price_kopecks == 99900
    assert rows["subscription_year"].period_days == 365
    assert rows["natal_full_report"].price_kopecks == 39900
    assert rows["horary_1"].price_kopecks == 5000
    assert rows["horary_3"].price_kopecks == 12000
    assert rows["horary_5"].price_kopecks == 18000
    assert rows["horary_10"].price_kopecks == 30000
    assert rows["synastry"].price_kopecks == 39900
    assert rows["synastry"].is_active is False


@pytest.mark.asyncio
async def test_products_endpoint_lists_only_active_with_exact_prices(
    async_client: AsyncClient, make_initdata, db_session, monkeypatch
) -> None:
    from app.core.config import settings

    monkeypatch.setattr(settings, "yookassa_enabled", True)
    monkeypatch.setattr(settings, "natal_report_enabled", True)
    await seed_products(db_session)

    initdata = make_initdata(user_id=8101, username="bill")
    r = await async_client.post("/api/auth/telegram", json={"initData": initdata})
    assert r.status_code == 200

    r = await async_client.get("/api/payment/products")
    assert r.status_code == 200
    products = {p["slug"]: p for p in r.json()["products"]}
    assert "synastry" not in products  # fail-closed, not for sale
    assert products["subscription_month"]["priceKopecks"] == 9900
    assert products["subscription_year"]["priceKopecks"] == 99900
    assert products["natal_full_report"]["priceKopecks"] == 39900
    assert products["horary_1"]["priceKopecks"] == 5000
    assert products["horary_10"]["priceKopecks"] == 30000


@pytest.mark.asyncio
async def test_products_endpoint_disabled_returns_503(
    async_client: AsyncClient, make_initdata, monkeypatch
) -> None:
    from app.core.config import settings

    monkeypatch.setattr(settings, "yookassa_enabled", False)
    initdata = make_initdata(user_id=8102, username="bill")
    r = await async_client.post("/api/auth/telegram", json={"initData": initdata})
    assert r.status_code == 200
    r = await async_client.get("/api/payment/products")
    assert r.status_code == 503
