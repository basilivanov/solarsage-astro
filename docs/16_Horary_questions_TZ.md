# ТЗ: Хорарные вопросы

## 1. Суть фичи

Пользователь задаёт конкретный астрологический вопрос (хорар), получает ответ «да / нет / возможно» с пояснением. Время вопроса — ключевой момент хорарной карты, поэтому оно обязательно фиксируется и подтверждается пользователем.

Хорар — один из форматов раздела «Разборы». Сейчас карточка «Хорар» в списке доступных разборов открывает заглушку (`InDevOverlay`). Задача — превратить заглушку в полноценный флоу: форма вопроса → генерация ответа → просмотр результата.

**Ключевой архитектурный принцип**: ответ хорара использует ту же блоковую систему, что и натальная карта (`BlockSchema` из `lib/contracts/natal.ts`). Переиспользуем все существующие типы блоков (`paragraph`, `lead`, `heading`, `list`, `callout`, `pros_cons`, `divider`, `quote`) и добавляем ровно 2 хорарных: `verdict_card` и `timing`. Рендерер на фронте — общий, переиспользуется из `components/readings/natal/block-renderer.tsx`.

---

## 2. Пользовательский флоу

### 2.1. Список вопросов `/readings/horary`

1. Header: стрелка «← Разборы», заголовок «Хорарные вопросы»
2. `HoraryQuotaBar` — остаток вопросов и покупка
3. Список прошлых вопросов (карточки). Нет вопросов — пустое состояние с подсказкой
4. Если `left > 0` — форма нового вопроса внизу; если `left === 0` — плашка «Вопросы закончились» + кнопка «Докупить»

### 2.2. Форма вопроса

1. **Категории-пили** (выбор опциональный, предзаполняет textarea):

| Пили       | Ключ      | Пример-плейсхолдер                              |
|-----------|-----------|-------------------------------------------------|
| 💕 Отношения | `love`    | «Выйду ли я замуж в этом году?»                 |
| 💼 Работа   | `career`  | «Стоит ли мне менять работу в этом месяце?»      |
| 💰 Деньги   | `money`   | «Будет ли у меня доход от этого проекта?»        |
| 🏥 Здоровье | `health`  | «Пройдёт ли болезнь к концу месяца?»            |
| ✈️ Переезд  | `travel`  | «Удачным ли будет переезд в новый город?»        |
| ⚡ Другое    | `other`   | «Найду ли я потерянную вещь?»                    |

2. **Textarea** — max 500 символов, min 5 для отправки. Плейсхолдер обновляется при выборе категории.
3. **Плашка подтверждения времени**:
   - Автоматически: `Intl.DateTimeFormat().resolvedOptions().timeZone()` → IANA timezone
   - Текущее локальное время: `new Date().toLocaleString("ru-RU", { timeZone })`
   - Показ: «Время вопроса: 14:32, 6 июня 2026 (Europe/Moscow)»
   - Кнопка «Изменить время» → Sheet с time/date picker
4. **Кнопка «Спросить»**:
   - Disabled при `text.length < 5`
   - Disabled при `left === 0`
   - Отправка → POST `/api/horary/questions`

### 2.3. Генерация (progress screen)

После отправки вопроса фронт показывает экран генерации:

```
┌─────────────────────────────────────┐
│          ✦ ✦ ✦                      │
│                                     │
│   Созвездия выстраиваются...        │
│                                     │
│   ████████████░░░░░░░░░ 62%        │
│                                     │
│   Анализирую аспекты Марса...       │
│                                     │
└─────────────────────────────────────┘
```

- Прогресс-бар (`shadcn Progress`) с плавной анимацией (фейковый ползунок 0→95 за ~8 сек)
- Этапы (каждые 2–3 сек):
  1. «Определяю момент вопроса...»
  2. «Строю хорарную карту...»
  3. «Анализирую аспекты...»
  4. «Формулирую ответ...»
- Иконка ✦ с `animate-pulse`
- `font-serif` для заголовка

**Polling**: Фронт поллит `GET /api/horary/questions/{id}` каждые 2 сек. Пока `status === "processing"` — показывает прогресс. Когда `status === "answered"` — переход на экран ответа.

**Timeout**: Если через 30 секунд статус всё ещё `processing` — показать плашку «Ответ формируется дольше обычного. Мы отправим уведомление, когда он будет готов.» и вернуть на список.

### 2.4. Экран ответа `/readings/horary/[id]`

1. **Header**: стрелка «← Хорарные вопросы»
2. **Карточка вопроса**: текст вопроса, категория (бейдж), дата/время вопроса
3. **Вердикт** (крупно, отдельный блок `verdict_card`):
   - `yes` → ✅ зелёный, текст «Да»
   - `no` → ❌ красный, текст «Нет»
   - `maybe` → 💫 фиолетовый, текст «Возможно»
   - Confidence bar (0–100%)
4. **Блоки ответа** — переиспользуется `BlockRenderer` из натальной карты, рендерит все стандартные блоки + 2 новых:
   - `paragraph` → обычный текст (уже есть)
   - `lead` → крупный абзац (уже есть)
   - `heading` → подзаголовок (уже есть)
   - `list` → маркированный/чек-лист (уже есть)
   - `callout` → блок с акцентом, tone: `neutral|strength|risk|insight` (уже есть)
   - `pros_cons` → за/против (уже есть)
   - `divider` → разделитель (уже есть)
   - `quote` → цитата (уже есть)
   - `timing` → **НОВЫЙ**: блок со сроками
   - `verdict_card` → **НОВЫЙ**: встроенный вердикт с confidence (для повторного показа внутри блоков)
5. **Планеты** — бейджи с русскими названиями (Меркурий, Венера и т.д.)
6. **Футер**: «Сформировано {дата}»

### 2.5. Покупка вопросов (Sheet)

`HoraryPurchaseSheet` — шторка снизу (shadcn Sheet):

| Количество | Цена (★) | Экономия |
|-----------|----------|----------|
| 1 вопрос  | 50 ★     | —        |
| 3 вопроса | 120 ★    | −20%     |
| 5 вопросов| 180 ★    | −28%     |
| 10 вопросов| 300 ★   | −40%     |

При нажатии — тостер «Оплата будет доступна в ближайшее время» (заглушка).

---

## 3. Архитектура

### 3.1. Backend-first: контракты

Source of truth — Pydantic-схемы в `apps/api/app/schemas/`. Pipeline:

```
apps/api/app/schemas/horary.py  (Pydantic, CamelModel)
        ↓  scripts/contracts/generate.sh
packages/contracts/openapi.json
        ↓  npx openapi-typescript
packages/contracts/_generated.ts
        ↓  per-feature shim
packages/contracts/horary.ts
```

Фронтенд импортирует типы только из `packages/contracts/`. Zod-схемы для форм — в `lib/contracts/horary.ts`.

### 3.2. Блоковая система: переиспользование натальной карты

Натальная карта использует универсальную `BlockSchema` (`lib/contracts/natal.ts`) — discriminated union из 11 типов блоков. Фронтендный рендерер `BlockRenderer` уже умеет рисовать все эти блоки.

Хорарный ответ переиспользует **ту же самую блоковую систему**. Добавляем только 2 хорарных типа блока:

| Тип блока      | Уже есть в natal | Используется в horary | Описание |
|---------------|:---:|:---:|----------|
| `paragraph`   | ✅ | ✅ | Обычный текст |
| `lead`        | ✅ | ✅ | Крупный абзац-вывод |
| `heading`     | ✅ | ✅ | Подзаголовок (h2/h3) |
| `list`        | ✅ | ✅ | Маркированный/чек-лист |
| `callout`     | ✅ | ✅ | Блок с акцентом (neutral/strength/risk/insight) |
| `pros_cons`   | ✅ | ✅ | За/против |
| `divider`     | ✅ | ✅ | Горизонтальный разделитель |
| `quote`       | ✅ | ✅ | Цитата |
| `stat_grid`   | ✅ | — | Сетка значений (не нужен в хораре) |
| `spheres_widget` | ✅ | — | Виджет сфер (не нужен) |
| `planets_widget` | ✅ | — | Виджет планет (не нужен) |
| `verdict_card` | **НОВЫЙ** | ✅ | Вердикт да/нет/возможно + confidence |
| `timing`      | **НОВЫЙ** | ✅ | Сроки реализации |

**Pydantic-сторона** — добавляем `HoraryBlock` union, который включает все стандартные блоки + 2 новых:

```python
HoraryBlock = Annotated[
    ParagraphBlock
    | LeadBlock
    | HeadingBlock
    | ListBlock
    | CalloutBlock
    | ProsConsBlock
    | DividerBlock
    | QuoteBlock
    | VerdictCardBlock      # НОВЫЙ
    | TimingBlock,          # НОВЫЙ
    Field(discriminator="type"),
]
```

Существующие блок-классы (`ParagraphBlock`, `LeadBlock` и т.д.) импортируются из `schemas/natal.py` или выносятся в общий `schemas/blocks.py`.

### 3.3. DB модели

Три таблицы (миграция `alembic/versions/0010_add_horary.py`):

```python
class HoraryQuestion(Base):
    __tablename__ = "horary_questions"
    id: Mapped[uuid.UUID]       PK, default=uuid4
    user_id: Mapped[uuid.UUID]  FK → users.id, CASCADE, index
    text: Mapped[str]            max_length=500
    category: Mapped[str|None]   max_length=20, nullable
    status: Mapped[str]          default="pending", max_length=20
                                 # pending → processing → answered | expired
    client_timezone: Mapped[str]  max_length=100
    client_local_time: Mapped[str|None]  nullable  # ISO datetime
    created_at: Mapped[datetime]  server_default=now()

class HoraryAnswer(Base):
    __tablename__ = "horary_answers"
    id: Mapped[uuid.UUID]          PK, default=uuid4
    question_id: Mapped[uuid.UUID]  FK → horary_questions.id, CASCADE, unique
    verdict: Mapped[str]            max_length=10  # yes/no/maybe
    confidence: Mapped[float]
    blocks_json: Mapped[str]        Text  # JSON list[HoraryBlock]
    planets_json: Mapped[str]       Text  # JSON list[str]
    generated_at: Mapped[datetime]  server_default=now()

class HoraryQuota(Base):
    __tablename__ = "horary_quotas"
    id: Mapped[int]               PK
    user_id: Mapped[uuid.UUID]    FK → users.id, unique, index
    questions_used: Mapped[int]   default=0
    questions_limit: Mapped[int]  default=3  # стартовых бесплатных
    reset_at: Mapped[datetime]
    created_at: Mapped[datetime]  server_default=now()
```

### 3.4. Pydantic-схемы (`apps/api/app/schemas/horary.py`)

```python
from typing import Annotated, Literal
from pydantic import Field
from ._base import CamelModel

# Переиспользуем блоки из natal, импортируем общие классы.
# Для новых типов блоков определяем их здесь. При необходимости
# общие блоки можно вынести в schemas/blocks.py.

class ParagraphBlock(CamelModel):
    type: Literal["paragraph"]
    text: str

class LeadBlock(CamelModel):
    type: Literal["lead"]
    text: str

class HeadingBlock(CamelModel):
    type: Literal["heading"]
    level: Literal[2, 3]
    text: str

class ListBlock(CamelModel):
    type: Literal["list"]
    style: Literal["bullet", "check"] | None = None
    items: list[str]

class CalloutBlock(CamelModel):
    type: Literal["callout"]
    tone: Literal["neutral", "strength", "risk", "insight"] | None = None
    title: str | None = None
    text: str

class ProsConsBlock(CamelModel):
    type: Literal["pros_cons"]
    pros_label: str | None = None
    cons_label: str | None = None
    pros: list[str] | None = None
    cons: list[str] | None = None

class DividerBlock(CamelModel):
    type: Literal["divider"]

class QuoteBlock(CamelModel):
    type: Literal["quote"]
    text: str
    source: str | None = None

# ---- Хорарные блоки (НОВЫЕ) ----

class VerdictCardBlock(CamelModel):
    """Крупная карточка вердикта: да/нет/возможно + confidence."""
    type: Literal["verdict_card"]
    verdict: Literal["yes", "no", "maybe"]
    confidence: float  # 0.0–1.0
    label: str | None = None  # Короткий текст рядом с вердиктом

class TimingBlock(CamelModel):
    """Блок со сроками реализации."""
    type: Literal["timing"]
    time_range: str  # "2–3 недели", "до конца месяца" и т.д.
    text: str | None = None  # Пояснение

# ---- Хорарный Block union ----

HoraryBlock = Annotated[
    ParagraphBlock
    | LeadBlock
    | HeadingBlock
    | ListBlock
    | CalloutBlock
    | ProsConsBlock
    | DividerBlock
    | QuoteBlock
    | VerdictCardBlock
    | TimingBlock,
    Field(discriminator="type"),
]

# ---- Request/Response схемы ----

class HoraryQuestionCreate(CamelModel):
    text: str = Field(..., min_length=5, max_length=500)
    category: Literal["love", "career", "money", "health", "travel", "other"] | None = None
    client_timezone: str = Field(..., max_length=100)
    client_local_time: str | None = None

class HoraryAnswerRead(CamelModel):
    verdict: Literal["yes", "no", "maybe"]
    confidence: float
    blocks: list[HoraryBlock]
    planets: list[str]
    generated_at: str

class HoraryQuestionRead(CamelModel):
    id: str
    text: str
    category: str | None
    status: Literal["pending", "processing", "answered", "expired"]
    client_timezone: str
    client_local_time: str | None
    created_at: str
    answer: HoraryAnswerRead | None = None

class HoraryQuotaRead(CamelModel):
    left: int
    next_in_days: int
    can_purchase: bool = True
```

**Примечание**: в перспективе общие блоки (`ParagraphBlock`, `LeadBlock` и т.д.) стоит вынести в `schemas/blocks.py` и импортировать оттуда в `schemas/natal.py` и `schemas/horary.py`. Сейчас для простоты дублируем определения — при контрактах они идентичны.

### 3.5. Сервис (`apps/api/app/services/horary_service.py`)

```python
class HoraryService:
    def __init__(self, db: AsyncSession): ...

    async def get_or_create_quota(self, user_id: UUID) -> HoraryQuota:
        """Создать квоту при первом обращении (3 бесплатных вопроса)."""

    async def check_quota(self, user_id: UUID) -> bool:
        """Есть ли свободный вопрос? Автоматический сброс при истечении reset_at."""

    async def create_question(self, user_id: UUID, data: HoraryQuestionCreate) -> HoraryQuestion:
        """Создать вопрос, списать квоту, поставить status=processing,
           запустить фоновую генерацию ответа."""

    async def generate_answer(self, question: HoraryQuestion) -> HoraryAnswer:
        """1. Загрузить натальные данные пользователя (profile.birth).
           2. Вычислить хорарную карту на момент вопроса (astro engine).
           3. Определить вердикт и планеты.
           4. LLM narration — рассказать ответ простым языком (LLMService).
           5. Собрать HoraryAnswer, записать в БД, обновить status=answered."""

    async def get_question(self, user_id: UUID, question_id: UUID) -> HoraryQuestion | None:
        """Получить вопрос с ответом. Проверка user_id."""

    async def list_questions(self, user_id: UUID, limit: int = 20, offset: int = 0) -> list[HoraryQuestion]:
        """Список вопросов пользователя, последние сверху."""

    async def increase_limit(self, user_id: UUID, additional: int) -> None:
        """Увеличить лимит вопросов (после покупки)."""
```

**Порядок генерации ответа:**

1. Загрузить `UserProfile` (birthday, birth_time, birth_city, birth_lat, birth_lon, birth_tz)
2. Построить хорарную карту на `client_local_time` + `client_timezone` (если null — на текущий момент)
3. Астрологический движок определяет: вердикт (yes/no/maybe), confidence, задействованные планеты/дома
4. LLM получает контекст (аспекты, дома, знаки) и пишет рассказ на русском языке, на «ты», в стиле дневного разбора
5. LLM возвращает JSON с блоками `HoraryBlock` (формат: массив блоков с `type`-дискриминатором)
6. Собрать `HoraryAnswer`, записать в БД, обновить `status=answered`

### 3.6. API (`apps/api/app/api/horary.py`)

| Метод  | URL                           | Описание                          |
|--------|-------------------------------|-----------------------------------|
| GET    | `/api/horary/quota`           | Квота вопросов (left, nextInDays) |
| GET    | `/api/horary/questions`       | Список вопросов (?limit=20&offset=0) |
| POST   | `/api/horary/questions`       | Создать вопрос (HoraryQuestionCreate) |
| GET    | `/api/horary/questions/{id}`  | Вопрос + ответ                    |

Все endpoints требуют авторизацию (`require_session`).

POST при отсутствии квоты возвращает `403 { "detail": "Horary quota exceeded" }`.

### 3.7. Регистрация роутера

В `apps/api/app/main.py` добавить:

```python
from app.api import horary
app.include_router(horary.router)
```

---

## 4. Frontend

### 4.1. Файловая структура

```
app/(grace)/readings/horary/
  page.tsx                        — Список вопросов + форма
  [id]/page.tsx                   — Детальный ответ

components/readings/horary/
  horary-screen.tsx               — Главный экран (композиция)
  horary-form.tsx                 — Форма вопроса
  horary-question-card.tsx        — Карточка прошлого вопроса
  horary-answer-view.tsx          — Экран ответа с блоками
  horary-quota-bar.tsx            — Баланс вопросов + «Докупить»
  horary-purchase-sheet.tsx       — Sheet покупки вопросов
  horary-progress.tsx             — Прогресс-заглушка при генерации
  horary-time-confirm.tsx         — Плашка/Sheet подтверждения времени

lib/contracts/horary.ts           — Zod-схемы + типы (расширяет natal BlockSchema)
lib/api/horary.ts                  — API-фасад
packages/contracts/horary.ts       — Shim-реэкспорт из _generated.ts
```

### 4.2. Типы (`lib/contracts/horary.ts`)

Расширяем `BlockSchema` из `lib/contracts/natal.ts` двумя новыми типами:

```typescript
import { z } from "zod"
import {
  BlockSchema,
  ParagraphBlockSchema,
  LeadBlockSchema,
  HeadingBlockSchema,
  ListBlockSchema,
  CalloutBlockSchema,
  ProsConsBlockSchema,
  DividerBlockSchema,
  QuoteBlockSchema,
} from "@/lib/contracts/natal"

// ---- Хорарные блоки (НОВЫЕ) ----

export const VerdictCardBlockSchema = z.object({
  type: z.literal("verdict_card"),
  verdict: z.enum(["yes", "no", "maybe"]),
  confidence: z.number().min(0).max(1),
  label: z.string().optional(),
})

export const TimingBlockSchema = z.object({
  type: z.literal("timing"),
  timeRange: z.string().min(1),
  text: z.string().optional(),
})

// ---- Расширенный Block union для хорара ----
// Включает все натальные блоки (кроме виджетов specific для натала)
// + 2 хорарных. Виджеты (spheres_widget, planets_widget, stat_grid)
// не включены — они не нужны в хорарном контексте.

export const HoraryBlockSchema = z.discriminatedUnion("type", [
  ParagraphBlockSchema,
  LeadBlockSchema,
  HeadingBlockSchema,
  ListBlockSchema,
  CalloutBlockSchema,
  ProsConsBlockSchema,
  DividerBlockSchema,
  QuoteBlockSchema,
  VerdictCardBlockSchema,
  TimingBlockSchema,
])

// ---- Категории и схемы запросов/ответов ----

export const HoraryCategorySchema = z.enum([
  "love", "career", "money", "health", "travel", "other"
])

export const HoraryQuestionCreateSchema = z.object({
  text: z.string().min(5).max(500),
  category: HoraryCategorySchema.optional(),
  clientTimezone: z.string(),
  clientLocalTime: z.string().optional(),
})

export const HoraryAnswerSchema = z.object({
  verdict: z.enum(["yes", "no", "maybe"]),
  confidence: z.number(),
  blocks: z.array(HoraryBlockSchema),
  planets: z.array(z.string()),
  generatedAt: z.string(),
})

export const HoraryQuestionSchema = z.object({
  id: z.string(),
  text: z.string(),
  category: HoraryCategorySchema.optional().nullable(),
  status: z.enum(["pending", "processing", "answered", "expired"]),
  clientTimezone: z.string(),
  clientLocalTime: z.string().optional().nullable(),
  createdAt: z.string(),
  answer: HoraryAnswerSchema.optional().nullable(),
})

export const HoraryQuotaSchema = z.object({
  left: z.number(),
  nextInDays: z.number(),
  canPurchase: z.boolean(),
})

// ---- Типы ----

export type HoraryCategory = z.infer<typeof HoraryCategorySchema>
export type HoraryQuestionCreate = z.infer<typeof HoraryQuestionCreateSchema>
export type HoraryBlock = z.infer<typeof HoraryBlockSchema>
export type VerdictCardBlock = z.infer<typeof VerdictCardBlockSchema>
export type TimingBlock = z.infer<typeof TimingBlockSchema>
export type HoraryAnswer = z.infer<typeof HoraryAnswerSchema>
export type HoraryQuestion = z.infer<typeof HoraryQuestionSchema>
export type HoraryQuota = z.infer<typeof HoraryQuotaSchema>

// ---- Категории для формы ----

export const HORARY_CATEGORIES: {
  key: HoraryCategory
  label: string
  emoji: string
  placeholder: string
}[] = [
  { key: "love", label: "Отношения", emoji: "💕", placeholder: "Выйду ли я замуж в этом году?" },
  { key: "career", label: "Работа", emoji: "💼", placeholder: "Стоит ли мне менять работу в этом месяце?" },
  { key: "money", label: "Деньги", emoji: "💰", placeholder: "Будет ли у меня доход от этого проекта?" },
  { key: "health", label: "Здоровье", emoji: "🏥", placeholder: "Пройдёт ли болезнь к концу месяца?" },
  { key: "travel", label: "Переезд", emoji: "✈️", placeholder: "Удачным ли будет переезд в новый город?" },
  { key: "other", label: "Другое", emoji: "⚡", placeholder: "Найду ли я потерянную вещь?" },
]
```

### 4.3. Рендерер блоков

В натальной карте уже есть `BlockRenderer` (`components/readings/natal/block-renderer.tsx`). Для хорара нужен `HoraryBlockRenderer`, который:

1. Переиспользует все существующие блок-рендереры из натальной карты для стандартных типов (`paragraph`, `lead`, `heading`, `list`, `callout`, `pros_cons`, `divider`, `quote`)
2. Добавляет рендеринг 2 новых типов:
   - `verdict_card` → крупная плашка с вердиктом и confidence bar
   - `timing` → блок со сроками и иконкой ⏱

Структура:

```
components/readings/natal/
  block-renderer.tsx       — Существующий, рендерит natal-блоки

components/readings/horary/
  horary-block-renderer.tsx — Расширяет BlockRenderer,
                               добавляет verdict_card + timing
```

`HoraryBlockRenderer` может быть реализован двумя способами:
- **Вариант А**: Обёртка, которая сначала проверяет horary-специфичные типы, а для остальных делегирует в `BlockRenderer`
- **Вариант Б** (рекомендуется): Рефакторинг `BlockRenderer` — вынести общие рендереры в `components/ui/block-renderers/` (paragraph.tsx, lead.tsx и т.д.) и собирать из них и `NatalBlockRenderer`, и `HoraryBlockRenderer`

На первом этапе (MVP) — Вариант А: простой switch, который для horary-типов рендерит своё, для остальных вызывает существующий `BlockRenderer`.

### 4.4. API-фасад (`lib/api/horary.ts`)

```typescript
import type {
  HoraryQuestion, HoraryQuestionCreate, HoraryQuota
} from "@/lib/contracts/horary"

const API_BASE = process.env.NEXT_PUBLIC_API_URL || ""

export async function getHoraryQuota(): Promise<HoraryQuota> {
  const res = await fetch(`${API_BASE}/api/horary/quota`, { credentials: "include" })
  if (!res.ok) throw new Error("Failed to fetch horary quota")
  return res.json()
}

export async function listHoraryQuestions(
  limit = 20, offset = 0
): Promise<HoraryQuestion[]> {
  const res = await fetch(
    `${API_BASE}/api/horary/questions?limit=${limit}&offset=${offset}`,
    { credentials: "include" }
  )
  if (!res.ok) throw new Error("Failed to list horary questions")
  return res.json()
}

export async function getHoraryQuestion(id: string): Promise<HoraryQuestion> {
  const res = await fetch(`${API_BASE}/api/horary/questions/${id}`, {
    credentials: "include",
  })
  if (!res.ok) throw new Error("Failed to fetch horary question")
  return res.json()
}

export async function createHoraryQuestion(
  data: HoraryQuestionCreate
): Promise<HoraryQuestion> {
  const res = await fetch(`${API_BASE}/api/horary/questions`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  })
  if (res.status === 403) throw new Error("Horary quota exceeded")
  if (!res.ok) throw new Error("Failed to create horary question")
  return res.json()
}
```

### 4.5. Компоненты

#### `horary-screen.tsx` — Главный экран

Композиция: header + quota-bar + past-questions + form. Состояния:
- `loading` — загрузка квоты и списка
- `idle` — форма видимая
- `submitting` — вопрос отправлен, показываем progress
- `polling` — поллим статус вопроса

#### `horary-form.tsx`

Состоит из:
- Категории-пили (6 кнопок, одна может быть выбрана)
- Textarea с автоплейсхолдером по категории
- `HoraryTimeConfirm` — подтверждение текущего времени
- Счётчик символов (0/500)
- Кнопка «Спросить» (disabled if `text.length < 5 || left === 0`)

#### `horary-question-card.tsx`

Карточка в списке прошлых вопросов:
- Иконка вердикта (✅ / ❌ / 💫)
- Текст вопроса (обрезанный до 2 строк, `line-clamp-2`)
- Дата создания (формат: «6 июня, 14:32»)
- Категория (бейдж)
- Chevron → переход на `/readings/horary/{id}`

#### `horary-answer-view.tsx`

Экран детального ответа. Рендерит:
1. Карточка вопроса (текст, категория, дата/время)
2. `HoraryBlockRenderer` для `answer.blocks` — каждый блок рендерится по своему типу
3. Планеты — бейджи с русскими названиями
4. Футер «Сформировано {дата}»

#### `horary-quota-bar.tsx`

```
┌────────────────────────────────────────────────────────┐
│  🪙  Хорарные вопросы: 2 из 3                         │
│  Следующий через 4 дн.  ·  [Докупить ★]              │
└────────────────────────────────────────────────────────┘
```

При `left === 0`: красная плашка «Вопросы закончились» + кнопка «Докупить».

#### `horary-purchase-sheet.tsx`

`Sheet` (снизу) с вариантами покупки. Заглушка — при нажатии тостер «Оплата будет доступна в ближайшее время».

#### `horary-progress.tsx`

Экран генерации (замещает форму после отправки):
- Анимированный Progress-бар (фейковый, 0→95 за ~8 сек)
- 4 этапа с текстом (каждые 2 сек):
  1. «Определяю момент вопроса...»
  2. «Строю хорарную карту...»
  3. «Анализирую аспекты...»
  4. «Формулирую ответ...»
- Заголовок `font-serif`: «Созвездия выстраиваются...»
- Иконка ✦ с `animate-pulse`
- При получении `status === "answered"` → автоматический переход на `/readings/horary/{id}`
- Таймаут 30 сек → плашка «Ответ формируется дольше обычного»

#### `horary-time-confirm.tsx`

Inline-плашка в форме:
- Показывает текущее время: «Время вопроса: 14:32, 6 июня 2026 (Europe/Moscow)»
- Кнопка «Изменить» → открывает Sheet с datetime-picker
- `clientTimezone` = `Intl.DateTimeFormat().resolvedOptions().timeZone`
- `clientLocalTime` = ISO datetime (по умолчанию текущее, или изменённое)

### 4.6. Страницы

#### `/readings/horary` — page.tsx

```tsx
"use client"
import { HoraryScreen } from "@/components/readings/horary/horary-screen"
export default function HoraryPage() {
  return <HoraryScreen />
}
```

#### `/readings/horary/[id]` — page.tsx

```tsx
"use client"
import { useEffect, useState } from "react"
import { useParams } from "next/navigation"
import { HoraryAnswerView } from "@/components/readings/horary/horary-answer-view"
import { HoraryProgress } from "@/components/readings/horary/horary-progress"
import { getHoraryQuestion, type HoraryQuestion } from "@/lib/api/horary"

export default function HoraryAnswerPage() {
  const { id } = useParams<{ id: string }>()
  const [question, setQuestion] = useState<HoraryQuestion | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getHoraryQuestion(id).then(q => {
      setQuestion(q)
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [id])

  if (loading) return <HoraryProgress />
  if (!question || !question.answer) return <NotFoundFallback />
  return <HoraryAnswerView question={question} />
}
```

### 4.7. Изменение навигации

В `components/readings/readings-screen.tsx`:
- Убрать `openComingHorary` и `comingAvailable` state
- Заменить `onClick` карточки horary на `router.push("/readings/horary")`

---

## 5. Хорарный движок (astro)

### 5.1. Принцип

Хорарная астрология строит карту на момент вопроса:
- **Время вопроса** = `client_local_time` (подтверждённое пользователем) или текущий момент
- **Место** = `current_city` или `birth_place` из профиля пользователя
- **Натальная карта** = данные рождения из профиля

Движок:
1. Строит транзитную карту на момент вопроса
2. Определяет ASC (асцендент) и его управителя
3. Анализирует аспекты управителя к со-управителю, Луне и сигнификатору вопроса
4. Определяет вердикт (yes/no/maybe) и confidence
5. Собирает задействованные планеты и дома

### 5.2. Сигнификаторы по категориям

| Категория | Сигнификатор (управитель) | Дома |
|-----------|---------------------------|------|
| love      | Венера, 7 дом            | 5, 7 |
| career    | Сатурн, 10 дом           | 2, 6, 10 |
| money     | Юпитер, 2 дом            | 2, 8 |
| health    | Марс, 6 дом              | 1, 6, 12 |
| travel    | Меркурий, 9 дом           | 3, 9 |
| other     | Луна (общий сигнификатор)| зависит от вопроса |

### 5.3. LLM narration

Промпт для `LLMService` получает:
- Текст вопроса
- Вердикт и confidence от движка
- Задействованные планеты, дома, аспекты
- Категорию

LLM возвращает JSON с блоками в формате `HoraryBlock[]`:

```json
{
  "blocks": [
    { "type": "verdict_card", "verdict": "yes", "confidence": 0.78, "label": "Скорее да" },
    { "type": "lead", "text": "Звёзды говорят «да», но с оговорками..." },
    { "type": "heading", "level": 2, "text": "Что говорит карта" },
    { "type": "paragraph", "text": "Меркурий в соединении с Венерой..." },
    { "type": "pros_cons", "pros": ["Сильный управитель ASC", "Луна в земном знаке"], "cons": ["Квадратура к Сатурну"] },
    { "type": "timing", "timeRange": "2–3 недели", "text": "Событие может произойти в ближайшие 2–3 недели..." },
    { "type": "callout", "tone": "insight", "title": "Обратите внимание", "text": "Не торопите события..." },
    { "type": "advice_block_or_paragraph" }
  ]
}
```

Стиль: разговорный, на «ты», как в дневном разборе. Запрещены англицизмы, вещественные имена планет на русском. Переиспользуются те же блоки что и в натальной карте для консистентности UI.

---

## 6. Квоты и покупка

### 6.1. Модель квот

- Стартовый лимит: **3 бесплатных вопроса**
- Период начисления: **+1 вопрос каждые 7 дней** (сброс `reset_at`)
- `questions_used` увеличивается при создании вопроса
- `questions_limit` увеличивается при покупке или начислении
- Проверка: `questions_used < questions_limit`

### 6.2. Покупка (заглушка)

`POST /api/horary/quota/purchase` — эндпоинт на будущее, пока не подключена оплата.
На фронте — `HoraryPurchaseSheet` с вариантами и тостер-заглушкой.

В перспективе оплата через **Telegram Stars** через `Telegram.WebApp.openInvoice()` — нативная интеграция для Mini App, не требует секретного ключа ЮKassa на бэкенде.

### 6.3. Связь с `HoraryCard` на профиле

`HoraryCard` в профиле уже показывает `left` и `nextInDays`.
После подключения horary API заменить моковые данные в `getProfileMeta()`
на реальные данные из `GET /api/horary/quota`.

---

## 7. Порядок реализации

| # | Файлы | Что |
|---|-------|-----|
| 1 | `apps/api/app/schemas/horary.py` | Pydantic-схемы (блоки + request/response) |
| 2 | `apps/api/app/db/models.py` | +3 модели (HoraryQuestion, HoraryAnswer, HoraryQuota) |
| 3 | `apps/api/alembic/versions/0010_add_horyary.py` | Миграция |
| 4 | `apps/api/app/services/horary_service.py` | Бизнес-логика (квота, CRUD, generate_answer — заглушка для движка) |
| 5 | `apps/api/app/api/horary.py` | 4 endpoints |
| 6 | `apps/api/app/main.py` | `app.include_router(horary.router)` |
| 7 | `pnpm contracts:generate` | Регенерация `_generated.ts` |
| 8 | `packages/contracts/horary.ts` | Shim-реэкспорт |
| 9 | `lib/contracts/horary.ts` | Zod-схемы + типы (расширяет natal BlockSchema) |
| 10 | `lib/api/horary.ts` | API-фасад |
| 11 | `components/readings/horary/horary-screen.tsx` | Главный экран |
| 12 | `components/readings/horary/horary-form.tsx` | Форма вопроса |
| 13 | `components/readings/horary/horary-question-card.tsx` | Карточка вопроса |
| 14 | `components/readings/horary/horary-answer-view.tsx` | Экран ответа |
| 15 | `components/readings/horary/horary-block-renderer.tsx` | Расширенный рендерер блоков (natal + verdict_card + timing) |
| 16 | `components/readings/horary/horary-quota-bar.tsx` | Баланс + покупка |
| 17 | `components/readings/horary/horary-purchase-sheet.tsx` | Sheet покупки |
| 18 | `components/readings/horary/horary-progress.tsx` | Прогресс-заглушка |
| 19 | `components/readings/horary/horary-time-confirm.tsx` | Подтверждение времени |
| 20 | `app/(grace)/readings/horary/page.tsx` | Страница-список |
| 21 | `app/(grace)/readings/horary/[id]/page.tsx` | Страница-ответ |
| 22 | `components/readings/readings-screen.tsx` | Навигация на /readings/horary |
| 23 | `lib/api/profile-meta.ts` | Замена моковых данных horary на реальный API |
| 24 | Тесты: `apps/api/tests/test_horary_endpoints.py` | API тесты |

---

## 8. Ревью-патч: решения по пробелам ТЗ

Ревью выявило 10 пробелов. Ниже — окончательные решения по каждому.

### 8.1. Хорарный движок: алгоритм вердикта

Новый эндпоинт в SolarSage **не нужен**. Хорарная карта — это повторный вызов `/v1/natal` с временем и местом вопроса вместо рождения.

**Алгоритм** (новый файл `apps/api/app/services/horary_engine.py`):

```
1. natal = SolarSageClient.get_natal(birth_date, birth_time, birth_lat, birth_lon, birth_tz)
2. horary_chart = SolarSageClient.get_natal(
     birth_date=client_local_time.date(),
     birth_time=client_local_time.time(),
     birth_lat=question_lat,  # из question_lat/question_lon, fallback на birth_lat/birth_lon
     birth_lon=question_lon,
     birth_tz=client_timezone
   )
3. transits = SolarSageClient.get_transits(
     target_date=client_local_time.date(),
     target_time=client_local_time.time(),
     target_tz=client_timezone
   )
4. signals = NormalizationService.normalize(horary_chart, transits)
5. verdict = HoraryEngine.compute_verdict(horary_chart, signals, category)
```

**Вердикт (yes/no/maybe) и confidence (0.0–1.0)**:

| Категория | Сигнификатор | Дома |
|-----------|--------------|------|
| love      | Венера        | 5, 7 |
| career    | Сатурн        | 2, 6, 10 |
| money     | Юпитер        | 2, 8 |
| health    | Марс          | 1, 6, 12 |
| travel    | Меркурий      | 3, 9 |
| other     | Луна          | зависит от вопроса |

**Формула**:
```
main_aspect_score = аспект_между(ASC_управитель, сигнификатор)
  трин/секстиль → +0.7..1.0
  соединение    → +0.5..0.8
  квадратура    → -0.5..-0.7
  оппозиция     → -0.6..-0.9

moon_score      = луна_в_доброй_части ? +0.3 : -0.2
combustion      = ASC_управитель_в_8_доме_или_сожжён ? -0.2 : 0
formal          = ASC_в_1_или_7_доме(для_love) ? +0.1 : 0

score = 0.4 * main_aspect_score + 0.3 * moon_score + combustion + 0.1 * formal
verdict  = "yes"   if score >= 0.6
           "no"    if score <= 0.3
           "maybe" otherwise
confidence = abs(score)
```

### 8.2. Pydantic-асимметрия: в horary.py — все типы с нуля

`apps/api/app/schemas/natal.py` содержит 4 типа (`ParagraphBlock`, `BulletsBlock`, `HighlightsBlock`, `QuoteBlock`), а фронтенд `lib/contracts/natal.ts` — 11 типов. Хорарный ответ использует фронтендный набор.

**Решение**: в `schemas/horary.py` определяем все 9 общих + 2 новых типа **с нуля**. Не трогаем `schemas/natal.py`. После MVP — рефакторинг: вынести общие типы в `schemas/blocks.py`.

**Важно для кодера**: Pydantic-блоки в `horary.py` НЕ импортируются из `natal.py`. Каждый тип определяется отдельно. Имена полей и типы должны точно совпадать с Zod-схемами из `lib/contracts/natal.ts` (server отдаёт camelCase через `CamelModel`).

### 8.3. Место хорарной карты: `question_lat`/`question_lon`

**Решение**: Добавить в `HoraryQuestion` два опциональных поля:

```python
question_lat: Mapped[Decimal | None] = mapped_column(Numeric(8, 5), nullable=True)
question_lon: Mapped[Decimal | None] = mapped_column(Numeric(9, 5), nullable=True)
```

В `HoraryQuestionCreate`:
```python
question_lat: float | None = None
question_lon: float | None = None
```

Логика в сервисе:
```python
# Если координаты не переданы — берём из профиля рождения
lat = data.question_lat or float(profile.birth_lat or 0)
lon = data.question_lon or float(profile.birth_lon or 0)
```

**Полный профиль трёх локаций** — пререквизит (ТЗ `19_Profile_three_locations_TZ.md`):
текущий город, город на ДР, место рождения. Когда профили расширены, fallback-цепочка:
```
question_lat/question_lon → current_lat/current_lon → birth_lat/birth_lon
```

### 8.4. Фоновая генерация и обработка ошибок

`generate_answer` запускается как `asyncio.create_task` из обработчика POST.

- При успехе: `status = "answered"`
- При исключении: `status = "expired"`, логировать ошибку через `logger.error`
- **Lazy TTL**: при `GET /api/horary/questions/{id}` если `status == "processing"` и `created_at < now - 5min` → атомарно обновить на `"expired"`
- **Prefect (после MVP)**: вынести `generate_answer` в Prefect-задачу для ретраев и мониторинга

### 8.5. Миграция: номер и голова

Хорарная миграция = `0012_add_horary.py`. Очерёдность:
- `0010` = профиль (три локации)
- `0011` = YooKassa (оплата)
- `0012` = хорар

`down_revision = '0011_add_yookassa_fields'`. Перед созданием проверить `alembic current` — если `dab464195b91` не в основной цепочке, создать merge-миграцию.

### 8.6. `export_openapi.py`: добавление хорарных схем

В `scripts/contracts/export_openapi.py` добавить в `_TOP_LEVEL_NAMES`:
```python
"HoraryQuestionCreate",
"HoraryQuestionRead",
"HoraryAnswerRead",
"HoraryQuotaRead",
```

Это шаг 7 в плане реализации, который не упоминался явно. Без него `pnpm contracts:generate` не сгенерирует типы для хорара.

### 8.7. Date/Time picker

`react-day-picker` (v9.13.2) и `date-fns` (v4.1.0) **уже установлены** в проекте. Отдельной установки не требуется.

### 8.8. LLM-промпт: полная спека

**System prompt**:
```
Ты — астролог, отвечающий на хорарный вопрос. Стиль: разговорный, на «ты», без англицизмов.
Планеты и дома называй по-русски. Не выдумывай аспекты — используй только данные из контекста.

Обязательные блоки в порядке:
1. verdict_card — вердикт и confidence
2. lead — одно предложение, главный вывод
3. paragraph — объяснение сигнификатора и ASC-управителя
4. pros_cons — за и против
5. timing — сроки реализации
6. callout (tone=insight) — совет
7. paragraph — итог
```

**User prompt** (шаблон):
```
Вопрос: {text}
Категория: {category}
Вердикт: {verdict} (confidence: {confidence})
Сигнификатор: {significator}
Управитель ASC: {asc_ruler}
Фаза Луны: {moon_phase}
Ключевые аспекты: {top_aspects}
Задействованные дома: {houses}

Верни ТОЛЬКО валидный JSON (без markdown):
{{
  "blocks": [
    { "type": "verdict_card", "verdict": "yes|no|maybe", "confidence": 0.0-1.0, "label": "..." }},
    ...
  ]
}}
```

**Параметры**: `max_tokens = 1500`, `temperature = 0.4`

**Fallback**: если LLM не вернул валидный JSON за 2 попытки — вернуть минимальный ответ из детерминистических данных:
```json
{
  "blocks": [
    {"type": "verdict_card", "verdict": "<from_engine>", "confidence": <from_engine>},
    {"type": "lead", "text": "<краткий вывод на основе вердикта>"}
  ],
  "planets": ["<из движка>"]
}
```

### 8.9. Тесты: полный список

**API-тесты** (`apps/api/tests/test_horary_endpoints.py`):
1. `POST /api/horary/questions` — 201 при валидных данных
2. `POST /api/horary/questions` — 403 при исчерпанной квоте
3. `POST /api/horary/questions` — 422 при `text.length < 5`
4. `POST /api/horary/questions` — 422 при `text.length > 500`
5. `POST /api/horary/questions` — 401 без авторизации
6. `GET /api/horary/questions` — список вопросов пользователя
7. `GET /api/horary/questions/{id}` — чужой вопрос → 404
8. `GET /api/horary/questions/{id}` — статус `processing` → polling
9. `GET /api/horary/quota` — корректный `left`, `nextInDays`
10. `GET /api/horary/quota` — авто-ресет при истёкшем `reset_at`

**Юнит-тесты** (`apps/api/tests/test_horary_service.py`):
1. `HoraryEngine.compute_verdict` — `yes` при хорошем аспекте (трин к сигнификатору)
2. `HoraryEngine.compute_verdict` — `no` при оппозиции к сигнификатору
3. `HoraryEngine.compute_verdict` — `maybe` при смешанных аспектах
4. `HoraryEngine.compute_significator` — правильный сигнификатор по категории (`love` → Венера, `career` → Сатурн и т.д.)
5. `HoraryQuotaService.get_or_create_quota` — создание при первом обращении
6. `HoraryQuotaService.check_quota` — `False` при исчерпанной квоте
7. `HoraryQuotaService.check_quota` — авто-ресет при истёкшем `reset_at`
8. `HoraryService.create_question` — списание квоты при создании
9. `HoraryService.create_question` — `403` при `left === 0`
10. `GET /api/horary/questions/{id}` — ownership-проверка

### 8.10. HoraryCard на профиле: замена моковых данных

`lib/api/profile-meta.ts` (строки 14-15) берёт данные из `/api/chat/quota`. После подключения horary API заменить:

```typescript
// БЫЛО:
const quotaRes = await fetch("/api/chat/quota", { ... })

// СТАЛО:
const quotaRes = await fetch("/api/horary/quota", { ... })
```

## 9. Invariants

1. **Backend-first**: все контракты создаются в Pydantic, регенерируются в TS через `pnpm contracts:generate`. Фронтенд не придумывает типы.
2. **CamelCase on wire**: `clientTimezone`, `createdAt`, `nextInDays` — все поля через `CamelModel.alias_generator = to_camel`.
3. **Общая блоковая система**: хорарный ответ использует те же блоки что и натальная карта (`paragraph`, `lead`, `heading`, `list`, `callout`, `pros_cons`, `divider`, `quote`). Новые типы — только `verdict_card` и `timing`. Рендерер переиспользует `BlockRenderer` из natal.
4. **Pydantic-асимметрия**: в `schemas/horary.py` все 11 типов блоков определяются с нуля. Не импортировать из `schemas/natal.py`. После MVP — рефакторинг в `schemas/blocks.py`.
5. **Время вопроса**: обязательно `client_timezone` (IANA) и опционально `client_local_time` (ISO). Если `client_local_time` не передан — сервер использует текущий момент.
6. **Место вопроса**: `question_lat`/`question_lon` опциональны в `HoraryQuestionCreate`. Fallback на `current_lat`/`current_lon` из профиля (ТЗ 19), затем на `birth_lat`/`birth_lon`.
7. **Квота**: проверка `questions_used < questions_limit` при создании вопроса. При превышении — `403`.
8. **Авторизация**: все endpoints требуют `require_session`.
9. **Ownership**: `GET /api/horary/questions/{id}` проверяет `user_id` — нельзя читать чужие вопросы.
10. **Хорарный движок**: не зависит от LLM. Движок считает аспекты и вердикт детерминистически. LLM только narrates результат на русском в формате блоков.
11. **Статусы**: `pending` → `processing` → `answered` | `expired`. Переход в `processing` происходит сразу при создании.
12. **Lazy TTL**: при `GET /api/horary/questions/{id}` если `status == "processing"` и `created_at < now - 5min` → атомарно обновить на `"expired"`.
13. **Фоновая генерация**: `asyncio.create_task` для MVP. При исключении — `status = "expired"`. После MVP — Prefect.
14. **Фронт**: polling каждые 2 сек при `status === "processing"`, таймаут 30 сек.
15. **Миграция**: `0012_add_horary.py`, `down_revision = '0011_add_yookassa_fields'`.
16. **Контракты**: добавить `HoraryQuestionCreate`, `HoraryQuestionRead`, `HoraryAnswerRead`, `HoraryQuotaRead` в `_TOP_LEVEL_NAMES` `export_openapi.py`.
17. **LLM fallback**: если LLM не вернул валидный JSON за 2 попытки — минимальный ответ из детерминистических данных (verdict_card + lead).

---

## 10. Non-goals (не делаем в этой волне)

- Реальная оплата хорарных вопросов через ЮKassa (будет через ТЗ 20)
- SSE/streaming генерации (не нужно, ответ приходит быстро)
- Редактирование или удаление вопросов
- Обратная связь / оценка ответа (лайк/дизлайк)
- Push-уведомления о готовности ответа
- Хорарный движок с полным расчётом домов (используем `/v1/natal` + `/v1/transits`)
- Кэширование ответов (повторный вопрос = новый ответ на новый момент)
- Рефакторинг BlockRenderer (вынос общих компонентов в `components/ui/block-renderers/`)
- `stat_grid`-блоки в хорарном контексте