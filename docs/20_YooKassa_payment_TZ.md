# ТЗ: Интеграция оплаты YooKassa

## 1. Суть

Подключить ЮKassa для приёма оплаты нескольких продуктов с рекуррентной подпиской.

### Каталог продуктов

| Slug | Название | Тип | Цена | Период | Что даёт |
|------|----------|-----|------|--------|----------|
| `subscription_month` | Подписка на 1 месяц | рекуррентная | 199 ₽ | 30 дней | Полный доступ ко всем разборам + хорарные вопросы |
| `subscription_year` | Подписка на 1 год | рекуррентная | 1990 ₽ | 365 дней | То же, со скидкой ~17% |
| `horary_1` | 1 хорарный вопрос | разовая | 50 ★ | — | 1 вопрос |
| `horary_3` | 3 хорарных вопроса | разовая | 120 ★ | — | 3 вопроса (−20%) |
| `horary_5` | 5 хорарных вопросов | разовая | 180 ★ | — | 5 вопросов (−28%) |
| `horary_10` | 10 хорарных вопросов | разовая | 300 ★ | — | 10 вопросов (−40%) |
| `synastry` | Синастрия (совместимость) | разовая | 399 ₽ | — | Полный разбор совместимости двух натальных карт |

**★** = Хорарные вопросы продаются за звезды (внутренняя валюта) или за рубли. В MVP — за рубли, цена та же (50/120/180/300 ₽). Звёзды — future feature.

**Архитектурный принцип**: каждый продукт — отдельный `product_slug`. Подписка — рекуррентная (автопродление). Хорарные вопросы и синастрия — разовые покупки.

Сейчас в проекте:
- `Payment` модель — 6 полей, `provider="telegram"`, statuses: `pending/succeeded/failed`
- `AccessService.grant_subscription()` — создаёт запись в `access_ledger` на 30 дней
- `PaymentService` — заглушка, создаёт Payment但没有реальногопровайдера
- Фронт: `AccessCard` с кнопкой «Оформить подписку» (кнопкаминёх), `Paywall` — кой
- `PAYMENTS_MODE=mock` в деве, `PAYMENTS_MODE=live` в проде

## 2. Переменные окружения

### `.env` (dev)

```env
# --- YooKassa (sandbox) ---
YOOKASSA_ENABLED=false
YOOKASSA_MODE=test
YOOKASSA_TEST_SHOP_ID=
YOOKASSA_TEST_SECRET_KEY=
YOOKASSA_RETURN_URL=http://localhost:3000/profile
YOOKASSA_WEBHOOK_SECRET=
YOOKASSA_SUBSCRIPTION_PRICE_KOPECKS=19900
YOOKASSA_SUBSCRIPTION_CURRENCY=RUB
```

### `.env.production` (prod)

```env
# --- YooKassa ---
YOOKASSA_ENABLED=true
YOOKASSA_MODE=live
YOOKASSA_LIVE_SHOP_ID=1317569
YOOKASSA_LIVE_SECRET_KEY=live_K_jp1ZvDWs89sdwLCMlvxbWIywx1Hz_mZyxPF3EjFiw
YOOKASSA_RETURN_URL=https://astro.vasiliy-ivanov.ru/profile
YOOKASSA_WEBHOOK_SECRET=
YOOKASSA_SUBSCRIPTION_PRICE_KOPECKS=19900
YOOKASSA_SUBSCRIPTION_CURRENCY=RUB
YOOKASSA_RECURRENT_ENABLED=false
```

`YOOKASSA_RECURRENT_ENABLED=false` — флаг-killswitch для автоплатежей. Пока `false`, рекуррент не списывается. Переключим на `true` после тестирования первого платежа вручную.

## 3. Backend

### 3.1. Конфиг (`apps/api/app/core/config.py`)

Добавить в `Settings`:

```python
# --- YooKassa ---
yookassa_enabled: bool = Field(False, alias="YOOKASSA_ENABLED")
yookassa_mode: str = Field("test", alias="YOOKASSA_MODE")  # "test" | "live"
yookassa_test_shop_id: str = Field("", alias="YOOKASSA_TEST_SHOP_ID")
yookassa_test_secret_key: str = Field("", alias="YOOKASSA_TEST_SECRET_KEY")
yookassa_live_shop_id: str = Field("", alias="YOOKASSA_LIVE_SHOP_ID")
yookassa_live_secret_key: str = Field("", alias="YOOKASSA_LIVE_SECRET_KEY")
yookassa_return_url: str = Field("", alias="YOOKASSA_RETURN_URL")
yookassa_webhook_secret: str = Field("", alias="YOOKASSA_WEBHOOK_SECRET")
yookassa_subscription_price_kopecks: int = Field(19900, alias="YOOKASSA_SUBSCRIPTION_PRICE_KOPECKS")
yookassa_subscription_currency: str = Field("RUB", alias="YOOKASSA_SUBSCRIPTION_CURRENCY")
yookassa_recurrent_enabled: bool = Field(False, alias="YOOKASSA_RECURRENT_ENABLED")

@property
def yookassa_shop_id(self) -> str:
    return self.yookassa_live_shop_id if self.yookassa_mode == "live" else self.yookassa_test_shop_id

@property
def yookassa_secret_key(self) -> str:
    return self.yookassa_live_secret_key if self.yookassa_mode == "live" else self.yookassa_test_secret_key
```

### 3.2. Зависимость (`apps/api/pyproject.toml`)

Добавить в `dependencies`:

```
"yookassa>=3,<4",
```

Установить:

```bash
cd apps/api && pip install yookassa>=3
```

### 3.3. YooKassa клиент (`apps/api/app/services/yookassa_client.py`)

Новый файл. Ответственность: ВСЕ обращения к YooKassa API — ТОЛЬКО через этот класс.

```python
"""YooKassa API client.

All YooKassa HTTP calls go through this class.
No other module makes direct HTTP requests to YooKassa.
"""
import uuid
from yookassa import Configuration, Payment as YooPayment
from yookassa.domain.common import ConfirmationType
from yookassa.domain.models import Currency, PaymentMethodType
from yookassa.domain.request import PaymentRequest

from app.core.config import settings
from app.core.logging import logger


class YooKassaClient:
    def __init__(self):
        Configuration.configure(
            account_id=settings.yookassa_shop_id,
            secret_key=settings.yookassa_secret_key,
        )

    def _idempotence_key(self, prefix: str, subscription_id: uuid.UUID, period: str) -> str:
        """Stable idempotence key: same subscription + same period = same key."""
        return f"{prefix}-{subscription_id}-{period}"

    async def create_initial_payment(
        self,
        user_id: uuid.UUID,
        subscription_id: uuid.UUID,
        amount_kopecks: int,
        currency: str,
        description: str,
        return_url: str,
    ) -> dict:
        """Create first payment with save_payment_method=true.

        Returns dict with keys: provider_payment_id, confirmation_token, confirmation_url, status.
        Raises YooKassa API errors.
        """
        idempotence_key = self._idempotence_key("init", subscription_id, "first")

        payment_request = PaymentRequest(
            amount={"value": str(amount_kopecks / 100) + ".00", "currency": currency},
            confirmation={"type": ConfirmationType.REDIRECT, "return_url": return_url},
            save_payment_method=True,
            capture=True,
            description=description,
            metadata={
                "user_id": str(user_id),
                "subscription_id": str(subscription_id),
                "type": "initial",
            },
            idempotence_key=idempotence_key,
        )
        payment = YooPayment.create(payment_request)

        confirmation = payment.confirmation
        return {
            "provider_payment_id": payment.id,
            "confirmation_token": getattr(confirmation, "confirmation_token", None) if confirmation else None,
            "confirmation_url": getattr(confirmation, "confirmation_url", None) if confirmation else None,
            "status": payment.status,
        }

    async def create_recurrent_payment(
        self,
        user_id: uuid.UUID,
        subscription_id: uuid.UUID,
        payment_method_id: str,
        amount_kopecks: int,
        currency: str,
        description: str,
        period_label: str,
    ) -> dict:
        """Create recurrent payment using saved payment_method_id.

        Returns dict with keys: provider_payment_id, status.
        """
        idempotence_key = self._idempotence_key("rebill", subscription_id, period_label)

        payment_request = PaymentRequest(
            amount={"value": str(amount_kopecks / 100) + ".00", "currency": currency},
            capture=True,
            payment_method_id=payment_method_id,
            description=description,
            metadata={
                "user_id": str(user_id),
                "subscription_id": str(subscription_id),
                "type": "recurrent",
                "period": period_label,
            },
            idempotence_key=idempotence_key,
        )
        payment = YooPayment.create(payment_request)

        return {
            "provider_payment_id": payment.id,
            "status": payment.status,
        }

    async def get_payment(self, provider_payment_id: str) -> dict:
        """Fetch payment details from YooKassa by id.

        Returns dict: provider_payment_id, status, payment_method_id (if saved).
        """
        payment = YooPayment.find_one(provider_payment_id)
        pm_saved = getattr(payment.payment_method, "saved", False) if payment.payment_method else False
        pm_id = payment.payment_method.id if payment.payment_method else None
        return {
            "provider_payment_id": payment.id,
            "status": payment.status,
            "payment_method_id": pm_id if pm_saved else None,
            "amount": float(payment.amount.value),
            "currency": payment.amount.currency,
        }


def get_yookassa_client() -> YooKassaClient:
    """Factory: returns client only if YooKassa is enabled."""
    if not settings.yookassa_enabled:
        raise RuntimeError("YooKassa is not enabled (YOOKASSA_ENABLED=false)")
    return YooKassaClient()
```

### 3.4. Миграция `0011_add_yookassa_fields.py`

Номер 0011 потому что 0010 занят профилем (три локации).

```python
"""add yookassa payment fields, products, and subscriptions

Revision ID: 0011_add_yookassa_fields
Revises: 0010_add_profile_locations
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0011_add_yookassa_fields"
down_revision = "0010_add_profile_locations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Расширить таблицу payments
    op.add_column("payments", sa.Column("product_slug", sa.String(50), nullable=True))
    op.add_column("payments", sa.Column("provider_payment_id", sa.String(255), nullable=True))
    op.add_column("payments", sa.Column("idempotence_key", sa.String(255), nullable=True))
    op.add_column("payments", sa.Column("confirmation_token", sa.String(512), nullable=True))
    op.add_column("payments", sa.Column("confirmation_url", sa.Text(), nullable=True))
    op.add_column("payments", sa.Column("payment_method_id", sa.String(255), nullable=True))
    op.add_column("payments", sa.Column("payment_method_saved", sa.Boolean(), server_default="false", nullable=False))
    op.add_column("payments", sa.Column("raw_payload_json", sa.Text(), nullable=True))
    op.add_column("payments", sa.Column("failure_reason", sa.Text(), nullable=True))
    op.add_column("payments", sa.Column("canceled_at", sa.DateTime(timezone=True), nullable=True))

    # 2. Создать таблицу products (каталог продуктов)
    op.create_table(
        "products",
        sa.Column("slug", sa.String(50), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("product_type", sa.String(20), nullable=False),
        # "subscription_recurrent" | "one_time"
        sa.Column("price_kopecks", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="RUB"),
        sa.Column("period_days", sa.Integer(), nullable=True),
        # 30 для month, 365 для year, NULL для one_time
        sa.Column("horary_quota", sa.Integer(), nullable=True),
        # количество хорарных вопросов (для хорарных продуктов)
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Заполнить каталог продуктов
    op.execute("""
        INSERT INTO products (slug, name, description, product_type, price_kopecks, currency, period_days, horary_quota) VALUES
        ('subscription_month', 'Подписка на 1 месяц', 'Полный доступ ко всем разборам и хорарным вопросам', 'subscription_recurrent', 19900, 'RUB', 30, NULL),
        ('subscription_year', 'Подписка на 1 год', 'Полный доступ со скидкой', 'subscription_recurrent', 199000, 'RUB', 365, NULL),
        ('horary_1', '1 хорарный вопрос', 'Один вопрос к астрологу', 'one_time', 5000, 'RUB', NULL, 1),
        ('horary_3', '3 хорарных вопроса', 'Три вопроса со скидкой 20%', 'one_time', 12000, 'RUB', NULL, 3),
        ('horary_5', '5 хорарных вопросов', 'Пять вопросов со скидкой 28%', 'one_time', 18000, 'RUB', NULL, 5),
        ('horary_10', '10 хорарных вопросов', 'Десять вопросов со скидкой 40%', 'one_time', 30000, 'RUB', NULL, 10),
        ('synastry', 'Синастрия', 'Полный разбор совместимости двух натальных карт', 'one_time', 39900, 'RUB', NULL, NULL)
    """)

    # 3. Создать таблицу subscriptions (для рекуррентных подписок)
    op.create_table(
        "subscriptions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("product_slug", sa.String(50), sa.ForeignKey("products.slug"), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        # pending -> active -> past_due -> canceled -> expired
        sa.Column("price_kopecks", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="RUB"),
        sa.Column("provider", sa.String(50), nullable=False, server_default="yookassa"),
        sa.Column("payment_method_id", sa.String(255), nullable=True),
        sa.Column("current_period_start", sa.Date(), nullable=True),
        sa.Column("current_period_end", sa.Date(), nullable=True),
        sa.Column("next_charge_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("canceled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancellation_reason", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    op.create_index("ix_subscriptions_user_id_status", "subscriptions", ["user_id", "status"])
    op.create_index("ix_subscriptions_next_charge_at", "subscriptions", ["next_charge_at"])

    # 4. Создать таблицу purchases (для разовых покупок: хорар, синастрия)
    op.create_table(
        "purchases",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("product_slug", sa.String(50), sa.ForeignKey("products.slug"), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        # pending -> succeeded -> consumed (для хорара) / delivered (для синастрии)
        sa.Column("horary_quota_added", sa.Integer(), nullable=True),
        # сколько хорарных вопросов добавлено (для хорарных продуктов)
        sa.Column("payment_id", sa.Integer(), sa.ForeignKey("payments.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_index("ix_purchases_user_id", "purchases", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_purchases_user_id")
    op.drop_table("purchases")
    op.drop_index("ix_subscriptions_next_charge_at")
    op.drop_index("ix_subscriptions_user_id_status")
    op.drop_table("subscriptions")
    op.drop_table("products")
    op.drop_column("payments", "canceled_at")
    op.drop_column("payments", "failure_reason")
    op.drop_column("payments", "raw_payload_json")
    op.drop_column("payments", "payment_method_saved")
    op.drop_column("payments", "payment_method_id")
    op.drop_column("payments", "confirmation_url")
    op.drop_column("payments", "confirmation_token")
    op.drop_column("payments", "idempotence_key")
    op.drop_column("payments", "provider_payment_id")
    op.drop_column("payments", "product_slug")
```

### 3.5. ORM-модели (`apps/api/app/db/models.py`)

Добавить 3 новые модели и расширить `Payment`:

```python
class Product(Base):
    """Каталог продуктов (подписка, хорар, синастрия). W-YK-1."""

    __tablename__ = "products"

    slug: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    product_type: Mapped[str] = mapped_column(String(20), nullable=False)
    # "subscription_recurrent" | "one_time"
    price_kopecks: Mapped[int] = mapped_column(nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="RUB")
    period_days: Mapped[int | None] = mapped_column(nullable=True)
    # 30 для month, 365 для year, None для one_time
    horary_quota: Mapped[int | None] = mapped_column(nullable=True)
    # количество хорарных вопросов (для хорарных продуктов)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Subscription(Base):
    """Подписка (рекуррентная). W-YK-1."""

    __tablename__ = "subscriptions"
    __table_args__ = (
        Index("ix_subscriptions_user_id_status", "user_id", "status"),
        Index("ix_subscriptions_next_charge_at", "next_charge_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    product_slug: Mapped[str] = mapped_column(String(50), ForeignKey("products.slug"), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    # pending -> active -> past_due -> canceled -> expired
    price_kopecks: Mapped[int] = mapped_column(nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="RUB")
    provider: Mapped[str] = mapped_column(String(50), nullable=False, default="yookassa")
    payment_method_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    current_period_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    current_period_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    next_charge_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    canceled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancellation_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="subscriptions")
    product: Mapped["Product"] = relationship("Product")


class Purchase(Base):
    """Разовая покупка (хорарные вопросы, синастрия). W-YK-1."""

    __tablename__ = "purchases"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    product_slug: Mapped[str] = mapped_column(String(50), ForeignKey("products.slug"), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    # pending -> succeeded -> consumed (хорар) / delivered (синастрия)
    horary_quota_added: Mapped[int | None] = mapped_column(nullable=True)
    # сколько хорарных вопросов добавлено (для horary_* продуктов)
    payment_id: Mapped[int | None] = mapped_column(ForeignKey("payments.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user: Mapped["User"] = relationship("User")
    product: Mapped["Product"] = relationship("Product")
```

Расширить `Payment` (добавить после существующих колонок `completed_at`):

```python
    # YooKassa fields (added by 0011)
    product_slug: Mapped[str | None] = mapped_column(String(50), ForeignKey("products.slug"), nullable=True)
    provider_payment_id: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True, index=True)
    idempotence_key: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True)
    confirmation_token: Mapped[str | None] = mapped_column(String(512), nullable=True)
    confirmation_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    payment_method_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    payment_method_saved: Mapped[bool] = mapped_column(default=False, nullable=False)
    raw_payload_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    canceled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
```

Добавить relationship в `User`:

```python
    subscriptions: Mapped[list["Subscription"]] = relationship(
        "Subscription", back_populates="user", cascade="all, delete-orphan"
    )
    purchases: Mapped[list["Purchase"]] = relationship(
        "Purchase", back_populates="user", cascade="all, delete-orphan"
    )
```

Расширить `Payment`:

```python
    # YooKassa fields (added by 0011_add_yookassa_fields)
    provider_payment_id: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True, index=True)
    idempotence_key: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True)
    confirmation_token: Mapped[str | None] = mapped_column(String(512), nullable=True)
    confirmation_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    payment_method_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    payment_method_saved: Mapped[bool] = mapped_column(default=False, nullable=False)
    raw_payload_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    canceled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
```

Добавить `Subscription` в `User` relationship:

```python
    subscriptions: Mapped[list["Subscription"]] = relationship(
        "Subscription", back_populates="user", cascade="all, delete-orphan"
    )
```

### 3.6. Pydantic-схемы (`apps/api/app/schemas/payment.py`)

Полностью переписать. Бывшие `PaymentIntent` и `PaymentWebhook` — заглушки, заменить на реальные контракты.

```python
from __future__ import annotations

from typing import Literal
from uuid import UUID

from ._base import CamelModel


# --- Product catalog (read-only, seeded by migration) ---

class ProductRead(CamelModel):
    """Каталог продуктов. Фронтенд показывает этот каталог."""
    slug: str
    name: str
    description: str | None = None
    product_type: Literal["subscription_recurrent", "one_time"]
    price_kopecks: int
    currency: str
    period_days: int | None = None
    horary_quota: int | None = None


# --- Start subscription ---

class SubscriptionStartRequest(CamelModel):
    """POST /api/payment/subscription/start — запрос на создание подписки."""
    product_slug: str = "subscription_month"
    # по умолчанию месячная, можно указать subscription_year


class SubscriptionStartResponse(CamelModel):
    """Ответ: token для YooKassa Widget + url для redirect."""
    subscription_id: UUID
    product_slug: str
    provider_payment_id: str
    confirmation_token: str | None = None
    confirmation_url: str | None = None
    status: str


# --- One-time purchase (horary, synastry) ---

class PurchaseStartRequest(CamelModel):
    """POST /api/payment/purchase/start — разовая покупка (хорар/синастрия)."""
    product_slug: str  # "horary_1", "horary_3", "horary_5", "horary_10", "synastry"


class PurchaseStartResponse(CamelModel):
    provider_payment_id: str
    confirmation_token: str | None = None
    confirmation_url: str | None = None
    status: str


# --- Subscription status ---

class SubscriptionStatusResponse(CamelModel):
    """GET /api/payment/subscription/status — текущее состояние подписки."""
    subscription_id: UUID | None = None
    product_slug: str | None = None
    status: Literal["pending", "active", "past_due", "canceled", "expired", "none"]
    price_kopecks: int
    currency: str
    current_period_start: str | None = None
    current_period_end: str | None = None
    next_charge_at: str | None = None
    has_access: bool
    access_until: str | None = None


# --- Cancel subscription ---

class SubscriptionCancelRequest(CamelModel):
    """POST /api/payment/subscription/cancel — отмена подписки."""
    reason: str | None = None


class SubscriptionCancelResponse(CamelModel):
    subscription_id: UUID | None
    status: str


# --- Products list ---

class ProductsListResponse(CamelModel):
    """GET /api/payment/products — каталог доступных продуктов."""
    products: list[ProductRead]


# --- Webhook ---

class YooKassaWebhookEvent(CamelModel):
    """POST /api/payment/webhook/yookassa — входящее уведомление."""
    type: str  # "payment.succeeded", "payment.canceled", etc.
    event: str | None = None
    object: dict | None = None
```

### 3.7. Subscription Service (`apps/api/app/services/subscription_service.py`)

Новый файл. ВСЯ бизнес-логика подписок и покупок — ЗДЕСЬ.

```python
"""Subscription and purchase service.

Handles:
- Creating subscription payments (monthly/yearly)
- Creating one-time purchase payments (horary questions, synastry)
- Activating subscriptions / granting purchases on payment success
- Canceling subscriptions
- Rebilling active subscriptions (scheduled job)

Invariants:
- One active subscription per user.
- Idempotent: same subscription_id + same period = same idempotence_key.
- Access is granted through AccessService.grant_subscription() for subscriptions.
- Horary quotas are granted by increasing horary_questions.questions_limit.
- Synastry access is tracked through purchases table (status=succeeded/delivered).
"""
import uuid
from datetime import date, datetime, timedelta, UTC
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import logger
from app.db.models import Payment, Subscription, Purchase, Product
from app.services.access_service import AccessService
from app.services.chat_quota_service import ChatQuotaService
from app.services.yookassa_client import YooKassaClient, get_yookassa_client


SUBSCRIPTION_DAYS_MONTH = 30
SUBSCRIPTION_DAYS_YEAR = 365
REBILL_RETRY_SCHEDULE = [1, 3, 5]  # days


class SubscriptionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Products ──────────────────────────────────────────────────

    async def get_products(self) -> list[Product]:
        """Return all active products from catalog."""
        result = await self.db.execute(
            select(Product).where(Product.is_active == True).order_by(Product.price_kopecks)
        )
        return list(result.scalars().all())

    async def get_product_by_slug(self, slug: str) -> Product | None:
        result = await self.db.execute(
            select(Product).where(Product.slug == slug, Product.is_active == True)
        )
        return result.scalar_one_or_none()

    # ── Start subscription (recurrent) ────────────────────────────

    async def start_subscription(
        self, user_id: uuid.UUID, product_slug: str = "subscription_month"
    ) -> dict:
        """Create initial payment for subscription.

        Returns dict with provider_payment_id, confirmation_token, confirmation_url, status.
        If user already has active subscription, returns existing one.
        """
        product = await self.get_product_by_slug(product_slug)
        if not product:
            raise ValueError(f"Product not found: {product_slug}")
        if product.product_type != "subscription_recurrent":
            raise ValueError(f"Product {product_slug} is not a subscription")

        # Check for existing active subscription
        existing = await self._get_active_subscription(user_id)
        if existing:
            return {"subscription_id": existing.id, "status": "already_active"}

        # Create subscription record
        subscription = Subscription(
            user_id=user_id,
            product_slug=product_slug,
            status="pending",
            price_kopecks=product.price_kopecks,
            currency=product.currency,
            provider="yookassa",
        )
        self.db.add(subscription)
        await self.db.flush()

        # Create YooKassa payment
        client = get_yookassa_client()
        result = await client.create_initial_payment(
            user_id=user_id,
            subscription_id=subscription.id,
            amount_kopecks=product.price_kopecks,
            currency=product.currency,
            description=product.name,
            return_url=settings.yookassa_return_url,
        )

        # Create local Payment record
        payment = Payment(
            user_id=user_id,
            amount=product.price_kopecks,
            currency=product.currency,
            status="pending",
            provider="yookassa",
            product_slug=product_slug,
            provider_payment_id=result["provider_payment_id"],
            idempotence_key=f"init-{subscription.id}-first",
            confirmation_token=result.get("confirmation_token"),
            confirmation_url=result.get("confirmation_url"),
            description=product.name,
        )
        self.db.add(payment)
        await self.db.commit()

        return {
            "subscription_id": subscription.id,
            "product_slug": product_slug,
            "provider_payment_id": result["provider_payment_id"],
            "confirmation_token": result.get("confirmation_token"),
            "confirmation_url": result.get("confirmation_url"),
            "status": result["status"],
        }

    # ── Start one-time purchase (horary, synastry) ────────────────

    async def start_purchase(self, user_id: uuid.UUID, product_slug: str) -> dict:
        """Create payment for one-time purchase (horary questions, synastry).

        Returns dict with confirmation data.
        """
        product = await self.get_product_by_slug(product_slug)
        if not product:
            raise ValueError(f"Product not found: {product_slug}")
        if product.product_type != "one_time":
            raise ValueError(f"Product {product_slug} is not a one-time purchase")

        # Create purchase record
        purchase = Purchase(
            user_id=user_id,
            product_slug=product_slug,
            status="pending",
            horary_quota_added=product.horary_quota,
        )
        self.db.add(purchase)
        await self.db.flush()

        # Create YooKassa payment (no save_payment_method for one-time)
        # For one-time purchases, we don't need save_payment_method=True
        # but we still use redirect confirmation
        client = get_yookassa_client()
        result = await client.create_initial_payment(
            user_id=user_id,
            subscription_id=purchase.id,  # reuse as idempotency key prefix
            amount_kopecks=product.price_kopecks,
            currency=product.currency,
            description=product.name,
            return_url=settings.yookassa_return_url,
        )

        # Create local Payment record
        payment = Payment(
            user_id=user_id,
            amount=product.price_kopecks,
            currency=product.currency,
            status="pending",
            provider="yookassa",
            product_slug=product_slug,
            provider_payment_id=result["provider_payment_id"],
            idempotence_key=f"purchase-{purchase.id}",
            confirmation_token=result.get("confirmation_token"),
            confirmation_url=result.get("confirmation_url"),
            description=product.name,
        )
        self.db.add(payment)

        # Link payment to purchase
        purchase.payment_id = payment.id  # type: ignore[assignment]
        await self.db.commit()

        return {
            "purchase_id": purchase.id,
            "product_slug": product_slug,
            "provider_payment_id": result["provider_payment_id"],
            "confirmation_token": result.get("confirmation_token"),
            "confirmation_url": result.get("confirmation_url"),
            "status": result["status"],
        }

    # ── Webhook handlers ───────────────────────────────────────────

    async def handle_webhook_payment_succeeded(
        self,
        provider_payment_id: str,
        payment_method_id: str | None,
        amount: float,
        currency: str,
        raw_payload: dict,
    ) -> None:
        """Handle payment.succeeded webhook. Idempotent."""
        result = await self.db.execute(
            select(Payment).where(Payment.provider_payment_id == provider_payment_id)
        )
        payment = result.scalar_one_or_none()

        if payment and payment.status == "succeeded":
            logger.info(f"[YooKassa] Payment {provider_payment_id} already processed, skipping")
            return

        if not payment:
            logger.warning(f"[YooKassa] Payment {provider_payment_id} not found in DB")
            return

        # Update payment
        payment.status = "succeeded"
        payment.completed_at = datetime.now(UTC)
        if payment_method_id:
            payment.payment_method_id = payment_method_id
            payment.payment_method_saved = True
        payment.raw_payload_json = str(raw_payload)

        # Route to handler based on product type
        product = await self.get_product_by_slug(payment.product_slug) if payment.product_slug else None

        if product and product.product_type == "subscription_recurrent":
            await self._activate_subscription(payment, payment_method_id)
        elif product and product.product_type == "one_time":
            await self._fulfill_purchase(payment, product)
        else:
            logger.warning(f"[YooKassa] Payment {provider_payment_id} has no product_slug, falling back to legacy access grant")
            # Legacy: grant 30 days
            access_service = AccessService(self.db)
            await access_service.grant_subscription(
                user_id=payment.user_id, start_date=date.today(), days=30
            )

        await self.db.commit()

    async def _activate_subscription(self, payment: Payment, payment_method_id: str | None) -> None:
        """Activate subscription after successful payment."""
        result = await self.db.execute(
            select(Subscription).where(
                Subscription.user_id == payment.user_id,
                Subscription.status.in_(["pending", "past_due"]),
            ).order_by(Subscription.created_at.desc())
        )
        subscription = result.scalar_one_or_none()

        if subscription:
            product = await self.get_product_by_slug(subscription.product_slug)
            period_days = product.period_days if product else SUBSCRIPTION_DAYS_MONTH

            subscription.status = "active"
            start = date.today()
            end = start + timedelta(days=period_days - 1)
            subscription.current_period_start = start
            subscription.current_period_end = end
            subscription.next_charge_at = datetime(
                end.year, end.month, end.day, 12, 0, 0, tzinfo=UTC
            )
            if payment_method_id:
                subscription.payment_method_id = payment_method_id

        # Grant access
        access_service = AccessService(self.db)
        product = await self.get_product_by_slug(payment.product_slug) if payment.product_slug else None
        days = product.period_days if product else SUBSCRIPTION_DAYS_MONTH
        await access_service.grant_subscription(
            user_id=payment.user_id, start_date=date.today(), days=days
        )

        logger.info(f"[YooKassa] Subscription activated for user {payment.user_id}")

    async def _fulfill_purchase(self, payment: Payment, product: Product) -> None:
        """Fulfill one-time purchase after successful payment."""
        result = await self.db.execute(
            select(Purchase).where(
                Purchase.user_id == payment.user_id,
                Purchase.status == "pending",
            ).order_by(Purchase.created_at.desc())
        )
        purchase = result.scalar_one_or_none()

        if not purchase:
            logger.warning(f"[YooKassa] No pending purchase found for payment {payment.id}")
            return

        purchase.status = "succeeded"

        # Grant product-specific benefit
        if product.horary_quota:
            # Increase horary question limit
            from app.db.models import HoraryQuota
            # HoraryQuota will be created by horary feature (doc 16)
            # For now, increase if exists
            result = await self.db.execute(
                select(HoraryQuota).where(HoraryQuota.user_id == payment.user_id)
            )
            quota = result.scalar_one_or_none()
            if quota:
                quota.questions_limit += product.horary_quota
                purchase.horary_quota_added = product.horary_quota
            # If no quota yet, horary feature will create it on first access
            purchase.horary_quota_added = product.horary_quota

        elif product.slug == "synastry":
            # TODO: grant synastry access (documented in synastry TZ)
            purchase.status = "delivered"
            logger.info(f"[YooKassa] Synastry purchase delivered for user {payment.user_id}")

        logger.info(f"[YooKassa] Purchase {purchase.id} fulfilled for user {payment.user_id}, product={product.slug}")

    async def handle_webhook_payment_canceled(
        self, provider_payment_id: str, raw_payload: dict
    ) -> None:
        """Handle payment.canceled webhook."""
        result = await self.db.execute(
            select(Payment).where(Payment.provider_payment_id == provider_payment_id)
        )
        payment = result.scalar_one_or_none()

        if not payment:
            logger.warning(f"[YooKassa] Canceled payment {provider_payment_id} not found")
            return

        payment.status = "canceled"
        payment.canceled_at = datetime.now(UTC)
        payment.raw_payload_json = str(raw_payload)
        await self.db.commit()

    # ── Cancel subscription ────────────────────────────────────────

    async def cancel_subscription(self, user_id: uuid.UUID, reason: str | None = None) -> dict:
        """Cancel active subscription. Does NOT revoke current access period."""
        result = await self.db.execute(
            select(Subscription).where(
                Subscription.user_id == user_id,
                Subscription.status.in_(["active", "past_due", "pending"]),
            ).order_by(Subscription.created_at.desc())
        )
        subscription = result.scalar_one_or_none()

        if not subscription:
            return {"subscription_id": None, "status": "no_active_subscription"}

        subscription.status = "canceled"
        subscription.canceled_at = datetime.now(UTC)
        subscription.cancellation_reason = reason or "user_request"
        await self.db.commit()

        return {"subscription_id": subscription.id, "status": "canceled"}

    # ── Status ──────────────────────────────────────────────────────

    async def get_subscription_status(self, user_id: uuid.UUID) -> dict:
        """Get current subscription status for user."""
        result = await self.db.execute(
            select(Subscription).where(
                Subscription.user_id == user_id,
            ).order_by(Subscription.created_at.desc())
        )
        subscription = result.scalar_one_or_none()

        access_service = AccessService(self.db)
        access_state = await access_service.can_access_day(user_id, date.today())

        if not subscription:
            return {
                "subscription_id": None,
                "product_slug": None,
                "status": "none",
                "price_kopecks": settings.yookassa_subscription_price_kopecks,
                "currency": settings.yookassa_subscription_currency,
                "current_period_start": None,
                "current_period_end": None,
                "next_charge_at": None,
                "has_access": access_state.state == "full",
                "access_until": access_state.access_until,
            }

        return {
            "subscription_id": subscription.id,
            "product_slug": subscription.product_slug,
            "status": subscription.status,
            "price_kopecks": subscription.price_kopecks,
            "currency": subscription.currency,
            "current_period_start": subscription.current_period_start.isoformat() if subscription.current_period_start else None,
            "current_period_end": subscription.current_period_end.isoformat() if subscription.current_period_end else None,
            "next_charge_at": subscription.next_charge_at.isoformat() if subscription.next_charge_at else None,
            "has_access": access_state.state == "full",
            "access_until": access_state.access_until,
        }

    # ── Recurring billing ──────────────────────────────────────────

    async def rebill_due_subscriptions(self) -> int:
        """Rebill all active subscriptions where next_charge_at <= now.

        Called by scheduled job every 30-60 minutes.
        Returns number of rebill attempts made.
        """
        if not settings.yookassa_recurrent_enabled:
            logger.info("[YooKassa] Recurrent billing disabled (YOOKASSA_RECURRENT_ENABLED=false)")
            return 0

        now = datetime.now(UTC)
        result = await self.db.execute(
            select(Subscription).where(
                Subscription.status.in_(["active", "past_due"]),
                Subscription.next_charge_at <= now,
                Subscription.payment_method_id.isnot(None),
            )
        )
        due = result.scalars().all()

        if not due:
            return 0

        client = get_yookassa_client()
        count = 0
        for sub in due:
            try:
                period_label = f"{sub.current_period_end.isoformat()}"
                result = await client.create_recurrent_payment(
                    user_id=sub.user_id,
                    subscription_id=sub.id,
                    payment_method_id=sub.payment_method_id,
                    amount_kopecks=sub.price_kopecks,
                    currency=sub.currency,
                    description=f"Подписка SolarSage — автопродление",
                    period_label=period_label,
                )
                count += 1
                logger.info(f"[YooKassa] Rebill initiated for subscription {sub.id}")
            except Exception as e:
                logger.error(f"[YooKassa] Rebill failed for subscription {sub.id}: {e}")
                sub.status = "past_due"
                retry_day = 1
                sub.next_charge_at = now + timedelta(days=retry_day)
                await self.db.commit()

        return count

    # ── Helpers ─────────────────────────────────────────────────────

    async def _get_active_subscription(self, user_id: uuid.UUID) -> Subscription | None:
        result = await self.db.execute(
            select(Subscription).where(
                Subscription.user_id == user_id,
                Subscription.status == "active",
            )
        )
        return result.scalar_one_or_none()
```

### 3.8. API endpoints (`apps/api/app/api/payment.py`)

Переписать полностью. Бывший `create_payment_intent` и `payment_webhook` — заглушки.

```python
"""Payment and subscription endpoints. W-YK-1: YooKassa integration."""
import uuid
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.dependencies import require_session
from app.db.models import User
from app.db.session import get_session
from app.schemas.payment import (
    SubscriptionStartRequest,
    SubscriptionStartResponse,
    SubscriptionStatusResponse,
    SubscriptionCancelRequest,
    SubscriptionCancelResponse,
)
from app.services.subscription_service import SubscriptionService

router = APIRouter()


@router.post("/api/payment/subscription/start", response_model=SubscriptionStartResponse)
async def start_subscription(
    _req: SubscriptionStartRequest,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(require_session),
):
    """Create initial payment for subscription.

    Returns confirmation token for YooKassa Widget.
    """
    if not settings.yookassa_enabled:
        raise HTTPException(status_code=503, detail="Payments are not available")

    service = SubscriptionService(db)
    result = await service.start_subscription(user_id=user.id)

    if result.get("status") == "already_active":
        raise HTTPException(status_code=409, detail="Subscription already active")

    return SubscriptionStartResponse(
        subscription_id=result["subscription_id"],
        provider_payment_id=result["provider_payment_id"],
        confirmation_token=result.get("confirmation_token"),
        confirmation_url=result.get("confirmation_url"),
        status=result["status"],
    )


@router.get("/api/payment/subscription/status", response_model=SubscriptionStatusResponse)
async def get_subscription_status(
    db: AsyncSession = Depends(get_session),
    user: User = Depends(require_session),
):
    """Get current subscription status."""
    service = SubscriptionService(db)
    result = await service.get_subscription_status(user_id=user.id)
    return SubscriptionStatusResponse(
        subscription_id=result["subscription_id"],
        status=result["status"],
        price_kopecks=result["price_kopecks"],
        currency=result["currency"],
        current_period_start=result.get("current_period_start"),
        current_period_end=result.get("current_period_end"),
        next_charge_at=result.get("next_charge_at"),
        has_access=result["has_access"],
        access_until=result.get("access_until"),
    )


@router.post("/api/payment/subscription/cancel", response_model=SubscriptionCancelResponse)
async def cancel_subscription(
    req: SubscriptionCancelRequest,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(require_session),
):
    """Cancel active subscription. Access remains until period end."""
    service = SubscriptionService(db)
    result = await service.cancel_subscription(user_id=user.id, reason=req.reason)
    return SubscriptionCancelResponse(
        subscription_id=result["subscription_id"],
        status=result["status"],
    )


@router.post("/api/payment/webhook/yookassa")
async def yookassa_webhook(
    request: Request,
    db: AsyncSession = Depends(get_session),
):
    """Handle YooKassa webhook notifications.

    This endpoint is called by YooKassa servers, NOT by our frontend.
    It is NOT behind require_session.
    """
    payload = await request.json()
    event_type = payload.get("type", "")

    # Verify webhook signature if WEBHOOK_SECRET is set
    # (YooKassa sends HTTP header with signature)
    # For MVP, we just process the event.
    # TODO: Verify webhook authenticity if YOOKASSA_WEBHOOK_SECRET is set.

    service = SubscriptionService(db)

    if event_type == "payment.succeeded":
        obj = payload.get("object", {})
        provider_payment_id = obj.get("id", "")
        payment_method = obj.get("payment_method", {})
        payment_method_id = payment_method.get("id") if payment_method.get("saved") else None
        amount = float(obj.get("amount", {}).get("value", 0))
        currency = obj.get("amount", {}).get("currency", "RUB")

        await service.handle_webhook_payment_succeeded(
            provider_payment_id=provider_payment_id,
            payment_method_id=payment_method_id,
            amount=amount,
            currency=currency,
            raw_payload=payload,
        )

    elif event_type == "payment.canceled":
        obj = payload.get("object", {})
        provider_payment_id = obj.get("id", "")
        await service.handle_webhook_payment_canceled(
            provider_payment_id=provider_payment_id,
            raw_payload=payload,
        )

    elif event_type == "payment.waiting_for_capture":
        # For save_payment_method, we use capture=True, so this should not happen
        pass

    else:
        pass  # Unknown event, ignore

    return {"ok": True}
```

### 3.9. Регистрация роутера (`apps/api/app/main.py`)

Уже есть `from app.api import payment`. Просто проверить что роутер зарегистрирован:

```python
app.include_router(payment.router)  # уже есть
```

### 3.10. Контракты (`scripts/contracts/export_openapi.py`)

Добавить новые топ-level модели в `_TOP_LEVEL_NAMES`:

```python
_TOP_LEVEL_NAMES: tuple[str, ...] = (
    # ... существующие ...
    "SubscriptionStartRequest",
    "SubscriptionStartResponse",
    "SubscriptionStatusResponse",
    "SubscriptionCancelRequest",
    "SubscriptionCancelResponse",
)
```

После — `pnpm contracts:generate`.

### 3.11. Scheduled job для рекуррента

Создать `apps/api/app/services/billing_job.py`:

```python
"""Scheduled job for subscription rebilling.

Called by Prefect worker or cron. Runs every 30 minutes.
"""
from app.core.logging import logger
from app.db.session import async_session_factory
from app.services.subscription_service import SubscriptionService


async def rebill_due_subscriptions():
    """Rebill all due subscriptions. Called by Prefect or cron."""
    async with async_session_factory() as db:
        service = SubscriptionService(db)
        count = await service.rebill_due_subscriptions()
        logger.info(f"[BillingJob] Rebill attempt count: {count}")
        await db.commit()
```

Для MVP подключить через cron или Prefect-задачу. Не добавлять в API-роутер.

## 4. Frontend

### 4.1. Установить YooKassa Widget SDK

```bash
pnpm add @yookassa/yookassa-payments-widget
```

Если пакет не подходит — использовать redirect-вариант через `window.open(confirmation_url)`.

### 4.2. API-фасад (`lib/api/subscription.ts`)

Новый файл:

```typescript
const API_BASE = process.env.NEXT_PUBLIC_API_URL || ""

export interface SubscriptionStartResult {
  subscriptionId: string
  providerPaymentId: string
  confirmationToken: string | null
  confirmationUrl: string | null
  status: string
}

export interface SubscriptionStatusResult {
  subscriptionId: string | null
  status: "none" | "pending" | "active" | "past_due" | "canceled" | "expired"
  priceKopecks: number
  currency: string
  currentPeriodStart: string | null
  currentPeriodEnd: string | null
  nextChargeAt: string | null
  hasAccess: boolean
  accessUntil: string | null
}

export async function startSubscription(): Promise<SubscriptionStartResult> {
  const res = await fetch(`${API_BASE}/api/payment/subscription/start`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({}),
  })
  if (res.status === 409) throw new Error("Subscription already active")
  if (!res.ok) throw new Error("Failed to start subscription")
  return res.json()
}

export async function getSubscriptionStatus(): Promise<SubscriptionStatusResult> {
  const res = await fetch(`${API_BASE}/api/payment/subscription/status`, {
    credentials: "include",
  })
  if (!res.ok) throw new Error("Failed to get subscription status")
  return res.json()
}

export async function cancelSubscription(reason?: string): Promise<{ subscriptionId: string | null; status: string }> {
  const res = await fetch(`${API_BASE}/api/payment/subscription/cancel`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ reason: reason || null }),
  })
  if (!res.ok) throw new Error("Failed to cancel subscription")
  return res.json()
}
```

### 4.3. Компонент оплаты (`components/subscription/yookassa-paywall.tsx`)

Новый файл. Заменяет кнопки «Оформить подписку» в `AccessCard` и `Paywall`.

```typescript
"use client"

import { useState } from "react"
import { startSubscription, getSubscriptionStatus } from "@/lib/api/subscription"

type Props = {
  onSuccess?: () => void
  onError?: (error: string) => void
}

export function YookassaPaywall({ onSuccess, onError }: Props) {
  const [loading, setLoading] = useState(false)

  const handleSubscribe = async () => {
    setLoading(true)
    try {
      const result = await startSubscription()

      if (result.confirmationUrl) {
        // Вариант 1: redirect (надёжнее для Telegram WebApp)
        window.open(result.confirmationUrl, "_blank")
      } else if (result.confirmationToken) {
        // Вариант 2: YooKassa Widget (если позволяет среда)
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const checkout = new (window as any).YooKassaCheckout({
          confirmation_token: result.confirmationToken,
          return_url: window.location.origin + "/profile",
          error_callback: (error: Error) => {
            onError?.(error.message)
          },
        })
        checkout.open()
      }

      // Poll for status
      const poll = setInterval(async () => {
        try {
          const status = await getSubscriptionStatus()
          if (status.hasAccess) {
            clearInterval(poll)
            onSuccess?.()
          }
          if (status.status === "none" || status.status === "expired") {
            // Payment failed or subscription expired
            clearInterval(poll)
          }
        } catch {
          // Ignore poll errors
        }
      }, 3000)

      // Timeout after 5 minutes
      setTimeout(() => clearInterval(poll), 5 * 60 * 1000)

    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : "Ошибка оплаты"
      onError?.(message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <button
      type="button"
      onClick={handleSubscribe}
      disabled={loading}
      className="inline-flex h-11 items-center justify-center gap-2 rounded-full bg-foreground px-5 text-[13px] font-medium text-background transition active:scale-[0.99] disabled:opacity-50"
    >
      {loading ? "Перенаправляем..." : "Оформить подписку · 199 ₽/мес"}
    </button>
  )
}
```

### 4.4. Интеграция с `AccessCard` и `Paywall`

В `components/profile/access-card.tsx` и `components/monetization/paywall.tsx` заменить кнопку «Оформить подписку» на `<YookassaPaywall />`.

Конкретно: в `AccessCard`, где `primary.onClick = onSubscribe`, подключить `<YookassaPaywall onSuccess={onSuccess} />`.

### 4.5. Страница `/profile` после оплаты

Когда пользователь возвращается с `return_url`, страница `/profile` должна:
1. Вызвать `getSubscriptionStatus()`.
2. Если `hasAccess === true` — показать «Подписка активна».
3. Если `status === "pending"` — показать «Проверяем оплату...» с поллингом каждые 3 сек, таймаут 2 мин.

## 5. Инварианты

1. **Один payment per subscription period**: `idempotence_key = "init-{subscription_id}-first"` гарантирует, что повторный запрос не создаст дубль.
2. **Idempotent webhook**: если `payment.status == "succeeded"` — пропускаем обработку.
3. **Один активный subscription per user**: если у пользователя уже есть `active` подписка — `start_subscription` возвращает 409.
4. **Cancel ≠ revoke**: отмена подписки НЕ отзывает текущий период. Доступ сохраняется до `current_period_end`.
5. **YOOKASSA_ENABLED**: при `false` все/payment endpoints возвращают 503.
6. **YOOKASSA_RECURRENT_ENABLED**: при `false` `rebill_due_subscriptions()` логирует и возвращает 0. Kill-switch.
7. **Webhook не требует авторизации**: `/api/payment/webhook/yookassa` НЕ использует `require_session`. YooKassa вызывает его со своим IP-адресом. При `YOOKASSA_WEBHOOK_SECRET` — проверять签名.
8. **Все суммы в копейках**: `price_kopecks = 19900` = 199.00 ₽. В YooKassa передаём `"199.00"`.

## 6. Порядок реализации

| # | Файл | Что |
|---|------|-----|
| 1 | `.env`, `.env.production` | Добавить YooKassa env vars |
| 2 | `apps/api/pyproject.toml` | Добавить `yookassa` dependency |
| 3 | `apps/api/app/core/config.py` | Добавить YooKassa settings |
| 4 | `apps/api/alembic/versions/0011_add_yookassa_fields.py` | Миграция: расширить payments + создать subscriptions |
| 5 | `apps/api/app/db/models.py` | +8 колонок в Payment, +Subscription модель |
| 6 | `apps/api/app/schemas/payment.py` | Переписать: SubscriptionStart*, Status*, Cancel*, Webhook |
| 7 | `apps/api/app/services/yookassa_client.py` | Новый: YooKassa HTTP клиент |
| 8 | `apps/api/app/services/subscription_service.py` | Новый: бизнес-логика подписок |
| 9 | `apps/api/app/services/billing_job.py` | Новый: scheduled rebill job |
| 10 | `apps/api/app/api/payment.py` | Переписать: 4 endpoints (start, status, cancel, webhook) |
| 11 | `apps/api/app/main.py` | Проверить `include_router(payment.router)` |
| 12 | `scripts/contracts/export_openapi.py` | Добавить новые схемы в `_TOP_LEVEL_NAMES` |
| 13 | `pnpm contracts:generate` | Регенерация `_generated.ts` |
| 14 | `lib/api/subscription.ts` | Новый: API-фасад |
| 15 | `components/subscription/yookassa-paywall.tsx` | Новый: компонент оплаты |
| 16 | `components/profile/access-card.tsx` | Заменить кнопку на `<YookassaPaywall />` |
| 17 | `components/monetization/paywall.tsx` | Заменить кнопку на `<YookassaPaywall />` |
| 18 | `apps/api/tests/test_subscription_endpoints.py` | API-тесты |
| 19 | `apps/api/tests/test_yookassa_webhook.py` | Webhook-тесты |
| 20 | `apps/api/tests/test_subscription_service.py` | Юнит-тесты сервиса |

## 7. Тестовый режим: что проверить

1. **Первый успешный платёж**: `POST /api/payment/subscription/start` → получить `confirmation_url` → перейти → оплата тестовой картой `5555 5555 5555 4444, 12/26, 000` → webhook `payment.succeeded` → `subscription.status = active`, `access_ledger` создан.
2. **Повторный запрос**: `start` при активной подписке → `409`.
3. **Отклонённый платёж**: тестовая карта `5555 5555 5555 4477` → webhook `payment.canceled` → подписка остаётся `pending`.
4. **Сохранение payment_method**: после успешного платежа проверить `payment.payment_method_saved = True` и `subscription.payment_method_id` заполнен.
5. **Отмена подписки**: `POST /api/payment/subscription/cancel` → `subscription.status = canceled`, доступ до `current_period_end` сохранён.
6. **Повторный webhook**: отправить `payment.succeeded` дважды с одним `provider_payment_id` → не создать дубль `access_ledger`.
7. **Webhook до return_url**: webhook пришел раньше, чем пользователь вернулся на `/profile` → `getSubscriptionStatus` возвращает `hasAccess: true`.
8. **Kill-switch**: `YOOKASSA_ENABLED=false` → все endpoints возвращают 503.

## 8. Non-goals

- Telegram Stars (отдельная задача, позже).
- ЮKасса Checkout.js как основной сценарий (только Widget или redirect).
- Мобильные SDK (пока нет нативного приложения).
- Сбор email для 54-ФЗ (MVP без чеков; добавить в следующей волне).
- Автоматический refund через API (только ручной через личный кабинет ЮKассы).
- Пробный период (free trial) — все пользователи начинают с платной подписки.