# ТЗ: Натальная карта — лендинг и генерация

## 1. Суть фичи

Натальная карта — платный разбор за 999₽. Не списывает хорарные вопросы, оплачивается отдельно.

**Ключевой инсайт**: движок уже считает натальную карту мгновенно (для дневного разбора). Это значит, что **preview-данные (цифры, доминанты, планеты) можно показать мгновенно и бесплатно**. LLM нужен только для narrative-текста (секции с блоками).

Поэтому флоу такой:
1. **Лендинг** — мгновенный, бесплатный, персонализированный. Показывает реальные данные из карты пользователя.
2. **Полный разбор** — платный (999₽). Генерируется по секциям через LLM. Однажды сгенерированный — кешируется навсегда.

---

## 2. Пайплайн данных (что уже работает)

```
SolarSage sidecar (POST /v1/natal)
  → planets[], houses[], special_points[], house_system
    → NormalizationService.normalize()
      → AstroSignal[] (planet_in_house, planet_in_sign, aspect, etc.)
        → ScoringService.score()
          → sphere_scores{}, day_status, top_signals
```

Этот пайплайн уже работает в `today_service` для дневного разбора. Все данные — мгновенные, детерминистические, без LLM.

**Что считаем мгновенно:**
- Позиции планет (знак, дом, градус, ретроградность)
- Система домов (Placidus)
- Доминанты сфер (9 сфер: карьера, отношения, деньги, здоровье, дом, мышление, смысл, кризисы, внутренний фон)
- Достоинства планет (dignity, exaltation, detriment, fall)
- Composite Score планет
- Бонификации (sect, combustion, retrograde)
- Аспекты (conjunction, opposition, trine, square, sextile)
- Специальные точки (узлы, Лилит, Хирон, Парсы, Селена, Вертекс)
- Фиксированные звёзды (соединения с планетами)
- Мидпойнты

**Что требует LLM:**
- Текстовый рассказ по каждой секции (narrative blocks)
- Текстовые выводы (lead-блоки, callout-блоки)
- За/против для аспектов (pros_cons-блоки)

---

## 3. Пользовательский флоу

### 3.1. Лендинг `/readings/natal` (мгновенный, бесплатный)

```
┌─────────────────────────────────────┐
│  ← Разборы                          │
│                                     │
│  Натальная карта                    │
│  Жанна · 7 янв 1993 · Чирчик      │
│  Placidus · ASC Рыбы 11°55'        │
│                                     │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌────┐│
│  │ ASC  │ │Управ.│ │Домин.│ │Дома││
│  │ Рыбы │ │Непт  │ │Карьера│ │10-11││
│  └──────┘ └──────┘ └──────┘ └────┘│
│                                     │
│  ▓▓▓▓▓▓▓▓▓▓▓░░░ Карьера   3.65    │
│  ▓▓▓▓▓▓▓▓░░░░░ Личность   3.29    │
│  ▓▓▓▓▓▓▓░░░░░░ Деньги      3.24   │
│  ▓▓▓▓▓▓░░░░░░░ Смыслы      2.66  │
│  ▓▓▓▓▓░░░░░░░░ Любовь      2.45   │
│  ░░░░░░░░░░░░░ Дом          0.98  │
│                                     │
│  ─ Планеты ──────────────────────── │
│  Меркурий   Дева 1д   ████████ 8  │
│  Солнце     Козерог 11д ██████  5  │
│  Венера     Рыбы 12д   █████    3   │
│  Марс       Рак 5д     ██░░░░   2   │
│  Сатурн     Водолей 12д ██░░░░ -6  │
│                                     │
│  ─ Главы разбора ───────────────── │
│  1  Из чего ты собрана          🔒 │
│  2  Как ты входишь в жизнь       🔒 │
│  3  Кто здесь главный           🔒 │
│  4  Главные аспекты             🔒 │
│  5  Сферы жизни                 🔒 │
│  6  Планетарные функции         🔒 │
│  7  Тень и защитные паттерны    🔒 │
│  8  Итоговый синтез             🔒 │
│                                     │
│  ─ Что входит в полный разбор ──── │
│                                     │
│  ✦ 300+ параметров                │
│  Собственная модель скоринга       │
│  Достоинства, сект, сжигание       │
│  Мидпойнты и фиксированные звёзды  │
│  Узлы, Парсы, Хирон, Лилит         │
│  Селена и Вертекс                 │
│  Конфигурации: стеллиумы,          │
│  Т-квадраты, мистич. прямоугольники│
│  8 глав глубокого разбора          │
│                                     │
│  Жанна, твоя карта уникальна.     │
│  Меркурий в Деве — финальный      │
│  диспозитор, Управитель ASC,      │
│  8 баллов Composite Score.         │
│  Это значит, что твой ум —         │
│  главный инструмент карты.         │
│                                     │
│  [═══ Открыть полный разбор ═══]  │
│           999 ₽                    │
│                                     │
└─────────────────────────────────────┘
```

### 3.2. Секции лендинга

#### Hero
- Имя, дата рождения, место, система домов
- ASC знак и градус (из реальных данных)

#### HighlightsStrip
- 4-5 бейджей из реальных данных карты:
  - Восходящий знак (ASC)
  - Управитель карты (финальный диспозитор)
  - Доминантная сфера (топ сфера из scoring)
  - Акцентные дома (где больше всего планет)
  - Система домов

#### SpheresWidget
- Горизонтальные прогресс-бары для каждой сферы
- Реальные данные из `ScoringService.score()`
- Топ-3 сферы — расширенные с объяснением, остальные — свёрнутые

#### PlanetScores
- Список планет с composite/dignity барами
- Реальные данные из скоринга
- Цветовая кодировка: зелёный для сильных, красный для напряжённых

#### Section List (замки)
- 8 глав с замком 🔒
- Заголовки секций — из шаблона (не LLM), определяются по данным карты
- При тапе на заблокированную секцию — скролл к CTA

#### «Почему наш разбор особый» (продающий блок)
- Персонализированный: берёт 2-3 ключевых факта из карты пользователя
  - «Жанна, твоя Меркурий — финальный диспозитор. Это значит...»
  - «В твоей карте 3 планеты в 11 доме — это сильный акцент на будущее и команды.»
  - «Самая напряжённая сфера — здоровье (0.84) — мы разберём почему.»
- Статический список: 300+ параметров, собственная модель, dignity/sect/combustion, мидпойнты, фиксированные звёзды, узлы, Парсы, Хирон, Лилит, Селена, Вертекс, конфигурации
- Не LLM — формируется из данных скоринга + шаблонных фраз

#### CTA
- Кнопка «Открыть полный разбор — 999 ₽»
- Если уже куплен — кнопка «Читать полный разбор» (без замков)

### 3.3. Генерация (после оплаты)

1. Создаём запись `NatalReport` с `status: "processing"`
2. Генерируем секции по одной через LLM:
   - Каждый вызов = 1 секция, строгий JSON-формат `ReportSection`
   - Если модель не справилась (invalid JSON) — retry с другой моделью
   - Максимум 2 попытки на секцию, потом skip (показываем заглушку)
3. LLM получает контекст: позиции планет, дома, аспекты, достоинства, скоринг, конфигурации
4. По мере готовности секций — фронт обновляет UI (polling каждые 3 сек)

### 3.4. Полный разбор `/readings/natal/[id]` (после генерации)

Та же страница лендинга, но:
- Замки 🔒 сняты с уже готовых секций
- Секции с замком — те, что ещё генерируются (show progress)
- Каждая секция — отдельная страница `/readings/natal/[id]` с `BlockRenderer`
- Полностью переиспользуем блоковую систему из `lib/contracts/natal.ts`

### 3.5. Повторный визит

Если пользователь уже купил наталку:
- Лендинг показывает всё сразу (из кеша)
- Кнопка «Читать полный разбор» (бесплатно, уже оплачено)
- Кнопка «Обновить» (перегенерировать narrative, тоже 999₽) — опционально

---

## 4. Архитектура

### 4.1. Backend: новые схемы и endpoints

#### `apps/api/app/schemas/natal.py` — расширение

```python
class NatalSectionTitle(CamelModel):
    id: str
    title: str
    eyebrow: str | None = None
    icon_name: str | None = None


class NatalPreview(CamelModel):
    """Мгновенный preview — бесплатный, без narrative."""
    meta: NatalMeta
    highlights: list[HighlightItem]
    spheres: list[SphereScoreItem]      # из ScoringService
    planets: list[PlanetScoreItem]       # из ScoringService
    section_titles: list[NatalSectionTitle]
    has_full_report: bool               # уже сгенерирован?
    personal_hook: str                   # персонализированный продающий абзац
    price: int = 999                     # в копейках


class NatalGenerateRequest(CamelModel):
    """Запрос на генерацию полного разбора."""
    # Пока пустой — профиль берётся из сессии
    pass


class NatalGenerateResponse(CamelModel):
    """Ответ на запрос генерации."""
    report_id: str
    status: Literal["processing", "answered", "failed"]
    sections_ready: list[str]            # id готовых секций
    sections_total: int


class NatalReportRead(CamelModel):
    """Полный отчёт — только если куплен."""
    meta: NatalMeta
    highlights: list[HighlightItem]
    spheres: list[SphereScoreItem]
    planets: list[PlanetScoreItem]
    sections: list[NatalSection]          # с blocks[] — полный narrative
```

#### API endpoints

| Метод | URL | Описание | Стоимость |
|-------|-----|----------|-----------|
| GET | `/api/natal/preview` | Мгновенный preview (мета, highlights, сферы, планеты, заголовки секций) | Бесплатно |
| POST | `/api/natal/generate` | Запуск генерации полного разбора (999₽) | 999₽ |
| GET | `/api/natal/report` | Полный отчёт (если куплен и сгенерирован) | Бесплатно (если куплен) |
| GET | `/api/natal/report/{section_id}` | Отдельная секция (если куплен) | Бесплатно (если куплен) |

#### DB модели

```python
class NatalReport(Base):
    __tablename__ = "natal_reports"
    id: Mapped[uuid.UUID]          PK, default=uuid4
    user_id: Mapped[uuid.UUID]     FK → users.id, unique, index
    status: Mapped[str]            default="processing"  # processing → answered | failed
    paid: Mapped[bool]             default=False
    sections_json: Mapped[str]     Text, nullable         # JSON list[NatalSection]
    preview_json: Mapped[str]      Text, nullable         # JSON NatalPreview (кеш)
    created_at: Mapped[datetime]  server_default=now()
    updated_at: Mapped[datetime]  server_default=now(), onupdate=now()
```

`sections_json` хранит только готовые секции. По мере генерации — добавляются.

### 4.2. Сервис `NatalService` — расширение

```python
class NatalService:
    async def get_preview(self, user_id: UUID) -> NatalPreview:
        """Мгновенный preview. Считает данные через SolarSageClient + ScoringService.
        Не требует LLM. Бесплатно."""

    async def get_report(self, user_id: UUID) -> NatalReportRead | None:
        """Полный отчёт. Только если куплен (paid=True) и сгенерирован (status=answered)."""

    async def get_section(self, user_id: UUID, section_id: str) -> NatalSection | None:
        """Отдельная секция. Проверяет paid + ищет в sections_json."""

    async def generate_report(self, user_id: UUID) -> NatalGenerateResponse:
        """Запуск генерации. Проверяет оплату. Создаёт NatalReport.
        Запускает фоновую генерацию по секциям."""

    async def _generate_section(self, user_id: UUID, section_id: str, context: dict) -> NatalSection | None:
        """Генерация одной секции через LLM.
        Строгий JSON-формат. Retry: 2 попытки текущей моделью,
        затем fallback на другую модель. Если обе — skip секция."""

    async def _build_personal_hook(self, preview: NatalPreview) -> str:
        """Персонализированный продающий абзац для лендинга.
        Берёт топ-3 факта из scoring + шаблон."""
```

### 4.3. Генерация по секциям

Порядок секций (из Жанниного разбора):

| # | id | eyebrow | title | Контекст для LLM |
|---|----|---------|-------|-------------------|
| 1 | `portrait` | Глава 1 | Из чего ты собрана | Общие доминанты, баланс сфер, главная ось |
| 2 | `asc` | Глава 2 | Как ты входишь в жизнь | ASC знак, управитель, дом управителя |
| 3 | `rulers` | Глава 3 | Кто здесь главный | Финальный диспозитор, цепочка управления |
| 4 | `aspects` | Глава 4 | Главные аспекты | Аспекты с орбами, за/против |
| 5 | `spheres` | Глава 5 | Сферы жизни | Скоринг сфер, акцентные дома |
| 6 | `planets` | Глава 6 | Планетарные функции | Composite Score, dignity, bonification |
| 7 | `shadow` | Глава 7 | Тень и защитные паттерны | Напряжённые позиции, detriment/fall |
| 8 | `synthesis` | Глава 8 | Итоговый синтез | Сводка всего |

Каждая секция:
1. Собирается детерминистический контекст из скоринга (планеты, дома, аспекты, достоинства)
2. Формируется промпт для LLM с требованием JSON-ответа в формате `ReportSection`
3. LLM генерирует `{id, title, eyebrow, blocks: [...]}`
4. Если JSON невалидный — retry (максимум 2 раза с текущей моделью)
5. Если не справилась — fallback на запасную модель
6. Если обе не справились — секция пропускается, показываем заглушку

### 4.4. LLM промпт (формат)

```python
NATAL_SECTION_PROMPT = """Ты пишешь секцию «{section_title}» натального разбора.

Данные карты: {context_json}

Правила:
- Пиши на «ты», без англицизмов
- Каждый абзац — мысль, а не энциклопедическая статья
- Объясняй астрологические термины простыми словами при первом упоминании
- Не придумывай то, чего нет в данных
- Используй творительный падеж после «с» правильно

Формат ответа — строго JSON:
{{
  "id": "{section_id}",
  "title": "...",
  "eyebrow": "Глава {n}",
  "blocks": [
    {{"type": "lead", "text": "..."}},
    {{"type": "paragraph", "text": "..."}},
    {{"type": "heading", "level": 2, "text": "..."}},
    {{"type": "list", "style": "bullet", "items": ["...", "..."]}},
    {{"type": "callout", "tone": "insight", "title": "...", "text": "..."}},
    {{"type": "pros_cons", "pros": ["..."], "cons": ["..."]}},
    {{"type": "divider"}}
  ]
}}

JSON:"""
```

### 4.5. Персонализированный продающий блок

Не LLM — формируется из данных скоринга + шаблоны. Примеры:

```python
def _build_personal_hook(preview: NatalPreview) -> str:
    # Топ-сфера
    top = preview.spheres[0]
    # Самая сильная планета
    strongest = max(preview.planets, key=lambda p: p.composite or 0)
    # Самая напряжённая
    weakest = min(preview.planets, key=lambda p: p.composite or 0)

    hooks = []
    hooks.append(f"{preview.meta.name}, твоя карта уникальна.")
    hooks.append(f"{strongest.name} в {strongest.sign} — {strongest.note or 'ключевая планета'}. Composite Score: {strongest.composite}.")
    if weakest.note:
        hooks.append(f"А вот {weakest.name} — {weakest.note}. Это зона роста, а не слабость.")
    hooks.append(f"Топ-сфера — {top.title} ({top.dominance:.1f}). Мы разберём почему.")

    return " ".join(hooks)
```

### 4.6. Модели LLM и retry-стратегия

| Приоритет | Модель | Использование |
|-----------|--------|---------------|
| 1 | `deepseek-v4-pro` или `kimi-k2.6` | Основная модель для генерации |
| 2 | `minimax-m3` | Fallback если основная не справилась |

Retry-логика для каждой секции:
1. Попытка 1: основная модель
2. Попытка 2: основная модель (если JSON невалидный)
3. Попытка 3: fallback модель
4. Если все 3 провалились — skip секция, показать заглушку `{type: "callout", tone: "neutral", text: "Эта секция будет обновлена позже"}`

---

## 5. Frontend

### 5.1. Файловая структура

```
components/readings/natal/
  natal-toc.tsx              — Существующий TOC (обновлённый)
  natal-section.tsx           — Существующий (обновлённый)
  block-renderer.tsx          — Существующий
  highlights-strip.tsx        — Существующий
  widgets/
    spheres-widget.tsx        — Существующий
    planets-widget.tsx        — Новый (или обновлённый)

components/readings/natal/landing/
  natal-landing.tsx           — Главный лендинг-экран
  natal-hero.tsx              — Hero: имя, дата, ASC
  natal-personal-hook.tsx     — Персонализированный продающий блок
  natal-why-block.tsx         — «Почему наш разбор особый»
  natal-section-list.tsx       — Список глав с замками
  natal-cta-button.tsx        — Кнопка «Открыть полный разбор — 999 ₽»

lib/api/natal.ts              — API-фасад (расширить)
lib/contracts/natal.ts        — Уже существует, расширить preview-типами
```

### 5.2. Новые типы (`lib/contracts/natal.ts`)

```typescript
// К существующим типам добавить:

export const NatalSectionTitleSchema = z.object({
  id: z.string().min(1),
  title: z.string().min(1),
  eyebrow: z.string().optional(),
  iconName: z.string().optional(),
})

export const NatalPreviewSchema = z.object({
  meta: NatalMetaSchema,
  highlights: z.array(HighlightSchema),
  spheres: z.array(SphereScoreSchema),
  planets: z.array(PlanetScoreSchema),
  sectionTitles: z.array(NatalSectionTitleSchema),
  hasFullReport: z.boolean(),
  personalHook: z.string(),
  price: z.number(),
})

export const NatalGenerateResponseSchema = z.object({
  reportId: z.string(),
  status: z.enum(["processing", "answered", "failed"]),
  sectionsReady: z.array(z.string()),
  sectionsTotal: z.number(),
})

export type NatalSectionTitle = z.infer<typeof NatalSectionTitleSchema>
export type NatalPreview = z.infer<typeof NatalPreviewSchema>
export type NatalGenerateResponse = z.infer<typeof NatalGenerateResponseSchema>
```

### 5.3. API-фасад (`lib/api/natal.ts`)

```typescript
// Добавить к существующему:

export async function getNatalPreview(): Promise<NatalPreview> {
  const res = await fetch(`${API_BASE}/api/natal/preview`, { credentials: "include" })
  if (!res.ok) throw new Error("Failed to fetch natal preview")
  return res.json()
}

export async function generateNatalReport(): Promise<NatalGenerateResponse> {
  const res = await fetch(`${API_BASE}/api/natal/generate`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
  })
  if (res.status === 402) throw new Error("Payment required")
  if (!res.ok) throw new Error("Failed to generate natal report")
  return res.json()
}

export async function getNatalReport(): Promise<NatalReport | null> {
  const res = await fetch(`${API_BASE}/api/natal/report`, { credentials: "include" })
  if (res.status === 404) return null
  if (!res.ok) throw new Error("Failed to fetch natal report")
  return res.json()
}

export async function getNatalSection(sectionId: string): Promise<ReportSection | null> {
  const res = await fetch(`${API_BASE}/api/natal/report/${sectionId}`, { credentials: "include" })
  if (res.status === 404) return null
  if (!res.ok) throw new Error("Failed to fetch natal section")
  return res.json()
}
```

### 5.4. Компоненты

#### `natal-landing.tsx` — Главный экран

Состояния:
- `loading` — загрузка preview
- `preview` — лендинг с данными (бесплатный)
- `generating` — генерация разбора (оплачивающий)
- `ready` — полный разбор готов

Композиция: Hero + HighlightsStrip + SpheresWidget + PlanetsWidget + SectionList + PersonalHook + WhyBlock + CTA

#### `natal-hero.tsx`

- Имя из профиля
- Дата рождения, место
- ASC знак + градус
- Система домов

#### `natal-personal-hook.tsx`

Персонализированный продающий блок:
- Топ-сфера из scoring
- Самая сильная планета
- Контраст (сильная vs напряжённая)
- «Мы разберём почему»

#### `natal-why-block.tsx`

Статический продающий список:
- 300+ параметров
- Собственная модель скоринга
- Достоинства, сект, сжигание
- Мидпойнты и фиксированные звёзды
- Узлы, Парсы, Хирон, Лилит, Селена, Вертекс
- Конфигурации: стеллиумы, Т-квадраты, мистический прямоугольник
- 8 глав глубокого разбора

#### `natal-section-list.tsx`

Список глав с замками. Из `sectionTitles` из preview.
Если `hasFullReport === true` — замков нет.
Если `status === "generating"` — на готовых секциях замок снят, на генерируемых — спиннер.

#### `natal-cta-button.tsx`

- Если `hasFullReport === false` → «Открыть полный разбор — 999 ₽»
- Если `status === "processing"` → «Генерируем разбор...» + прогресс
- Если `hasFullReport === true` → «Читать полный разбор»

#### `planets-widget.tsx`

Список планет с composite/dignity барами:
- Цветовая кодировка: зелёный для сильных (composite > 3), красный для напряжённых (composite < 0)
- Каждая планета: имя, знак, дом, мини-бар composite
- Сортировка по composite (убывание)

### 5.5. Страницы

#### `/readings/natal` — page.tsx (существующий, обновлённый)

```tsx
"use client"
import { useEffect, useState } from "react"
import { NatalLanding } from "@/components/readings/natal/landing/natal-landing"
import { NatalToc } from "@/components/readings/natal/natal-toc"
import { getNatalPreview, getNatalReport } from "@/lib/api/natal"
import type { NatalPreview, NatalReport } from "@/lib/contracts/natal"

export default function NatalPage() {
  const [preview, setPreview] = useState<NatalPreview | null>(null)
  const [report, setReport] = useState<NatalReport | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([getNatalPreview(), getNatalReport()]).then(([p, r]) => {
      setPreview(p)
      setReport(r)
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [])

  if (loading) return <LoadingFallback />
  if (report) return <NatalToc report={report} />
  if (preview) return <NatalLanding preview={preview} />
  return <LockedFeatureCard title="Натальная карта" description="..." />
}
```

#### `/readings/natal/[id]` — page.tsx (существующий, без изменений)

---

## 6. Оплата

### 6.1. Модель

- Натальная карта стоит **999 ₽**
- Не списывает хорарные вопросы
- Не бесплатна для подписчиков (отдельный продукт)
- Однократная оплата: купил → сгенерировано → кешировано навсегда
- Повторная генерация (обновить narrative) — опционально, тоже 999₽

### 6.2. Процесс оплаты (MVP — заглушка)

При нажатии «Открыть полный разбор — 999 ₽»:
1. Если пользователь не авторизован → показать онбординг
2. Если авторизован → Sheet снизу с вариантами оплаты:
   - Telegram Stars (Telegram.WebApp.openInvoice)
   - ЮKassa (редирект на страницу оплаты) — на будущее
3. Пока — Sheet с текстом «Оплата будет доступна в ближайшее время» + кнопка «Диагностика» (бесплатный тест для dev)

### 6.3. Флаг оплаты

Добавить в `NatalReport` поле `paid: bool`. 
- `paid=False` → лендинг с замками
- `paid=True, status=processing` → лендинг + прогресс-бары на секциях
- `paid=True, status=answered` → полный разбор

---

## 7. Порядок реализации

| # | Файлы | Что |
|---|-------|-----|
| 1 | `apps/api/app/schemas/natal.py` | + NatalPreview, NatalSectionTitle, NatalGenerateRequest/Response, NatalReportRead |
| 2 | `apps/api/app/db/models.py` | + NatalReport модель |
| 3 | `apps/api/alembic/versions/0011_add_natal_report.py` | Миграция |
| 4 | `apps/api/app/services/natal_service.py` | Расширить: get_preview, generate_report, get_report, get_section, _generate_section, _build_personal_hook |
| 5 | `apps/api/app/services/scoring_service.py` | Расширить: добавить compute_planet_scores, compute_highlights, compute_section_titles |
| 6 | `apps/api/app/api/natal.py` | + GET /api/natal/preview, POST /api/natal/generate, GET /api/natal/report |
| 7 | `apps/api/app/main.py` | Роутер уже подключён |
| 8 | `pnpm contracts:generate` | Регенерация _generated.ts |
| 9 | `packages/contracts/natal.ts` | Shim-реэкспорт новых типов |
| 10 | `lib/contracts/natal.ts` | + NatalPreviewSchema, NatalGenerateResponseSchema |
| 11 | `lib/api/natal.ts` | + getNatalPreview, generateNatalReport, getNatalReport |
| 12 | `components/readings/natal/landing/natal-landing.tsx` | Главный лендинг |
| 13 | `components/readings/natal/landing/natal-hero.tsx` | Hero |
| 14 | `components/readings/natal/landing/natal-personal-hook.tsx` | Персонализированный продающий блок |
| 15 | `components/readings/natal/landing/natal-why-block.tsx` | «Почему наш разбор особый» |
| 16 | `components/readings/natal/landing/natal-section-list.tsx` | Список глав с замками |
| 17 | `components/readings/natal/landing/natal-cta-button.tsx` | Кнопка CTA |
| 18 | `components/readings/natal/widgets/planets-widget.tsx` | Таблица планет с барами |
| 19 | `app/(grace)/readings/natal/page.tsx` | Обновить: лендинг или TOC в зависимости от состояния |
| 20 | Тесты | API + компоненты |

---

## 8. Invariants

1. **Preview бесплатный и мгновенный**: `GET /api/natal/preview` не вызывает LLM, только движок + скоринг.
2. **Полный разбор платный**: 999₽, не списывает хорарные вопросы.
3. **Кеширование**: однажды сгенерированный отчёт хранится в `natal_reports.sections_json` навсегда.
4. **Генерация по секциям**: каждый вызов LLM = 1 секция. Строгий JSON. Retry: 2 попытки + fallback модель.
5. **Fallback при ошибке**: если секция не сгенерировалась — показываем `{type: "callout", tone: "neutral", text: "Эта секция будет обновлена позже"}`.
6. **Персонализация лендинга**: продающий блок формируется из реальных данных скоринга, не LLM.
7. **Блоковая система**: полный разбор использует `BlockSchema` из `lib/contracts/natal.ts`, тот же рендерер.
8. **Backend-first**: новые схемы в `apps/api/app/schemas/natal.py`, регенерация TS через `pnpm contracts:generate`.
9. **CamelCase on wire**: все новые поля через `CamelModel.alias_generator`.
10. **Секции определяются по данным**: список секций не хардкод, а формируется по скорингу (какие сферы сильные, какие планеты акцентные).

---

## 9. Non-goals (не делаем в этой волне)

- Реальная оплата через Telegram Stars / ЮKassa (заглушка)
- SSE/streaming генерации (polling каждые 3 сек)
- Редактирование или удаление наталки
- Обновление narrative (перегенерация) — на будущее
- Выбор формата (json vs markdown) — только json блоки
- Динамический подбор секций по интересу пользователя (показываем все 8)
- Перевод на другие языки (только русский)