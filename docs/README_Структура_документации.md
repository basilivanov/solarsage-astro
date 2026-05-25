---
id: doc-readme-structure
status: active
wave: none
last_review: 2026-05-25
---
# Структура документации проекта

Документация разбита на самостоятельные блоки. Каждый файл можно отдать
дизайнеру, frontend-агенту, backend-агенту или LLM-агенту без лишнего
контекста.

## Правила, удерживающие документы от расползания

1. **Источник истины — один.** Если факт зафиксирован в коде или каноне, в
   `docs/` живёт только нарратив + ссылка. Дублировать поля Pydantic-схем
   или содержимое `grace/canon/*.xml` запрещено.
2. **Front-matter обязателен.** Каждый `*.md` начинается с YAML-блока
   `id / status / wave / last_review`. Проверяет
   `scripts/check_frontmatter.py`.
3. **Manifest = действительность.** `docs/MANIFEST.md` обязан перечислять
   все `*.md` в каталоге. Проверяет `scripts/check_docs_manifest.py`.
4. **Stale = провал гейта.** Документ со `status: active` и
   `last_review` старше 120 дней роняет CI. Либо обновляется, либо
   переводится в `stale` / `superseded`.
5. **Write-scope.** `docs/`, `grace/canon/` и `MANIFEST.md` защищены
   `.github/CODEOWNERS`. Без ревью владельца pull request не сольётся.

## Активные документы

- **00 Обзор продукта** — что строим, главная ценность, MVP, доступ,
  рефералка, технический принцип.
- **01 MVP экраны и навигация** — вкладки, routes, переходы, Today как
  экран выбранного дня.
- **02 Today screen** — структура главного экрана, верхние флаги,
  основной текст, why-блок, 7-дневная лента.
- **03 Почему так у меня** — правила раскрытия, астрологическое мясо,
  структура секций, эталонный пример.
- **04 SolarSage нормализация скоринг кеширование** — расчётные слои,
  AstroSignal, scoring, fallback, cache, versioning.
- **06 Натальная карта контракт и фронт** — versioned payload для
  натального разбора, sections/blocks, mobile-first навигация.
- **07 Backend architecture draft** — оркестратор, расчётный слой,
  структура каталогов, главные сущности БД.
- **08 Frontend current state and alignment** — состояние v0-фронта на
  момент последней сверки и расхождения с проектными документами.
- **09 Project transfer context** — общий контекст для переноса проекта
  в другой чат / нового агента.
- **10 GRACE Project Agent Guide** — onboarding для агента в новом чате.
- **GRACE_CANON** — methodology canon (transferable operating model).

## Запланированные ТЗ (binding waves)

- **11 SolarSage rewrite** — `W-SOLARSAGE-SVC`. Перевод CLI-скрипта в
  HTTP-сервис (инфра).
- **12 Microcopy dictionary** — `W-MICROCOPY`. Управляемый словарь
  коротких астрофраз.
- **13 Evening check-in** — `W-EVENING`. Продуктовая петля
  «вечером отметил → утром closure».
- **14 SolarSage scoring rewrite** — `W-SOLARSAGE-ALGO`. Activation
  Layer + Convergence Bonus + канонизация SPHERES / dignities /
  aspect-rules. Парный к 11 (алгоритм, не инфра).

## Замороженные / устаревшие

- **05 API contracts и TodayPayload** — `superseded` (W-1.1B). Шаблоны
  payload теперь в `apps/api/app/schemas/` и
  `packages/contracts/_generated.ts`.
- **DEPLOY** — `stale` (pre-W-1.0). Заменится на W-DEPLOY packet.

## Главный принцип

Каждый документ отвечает на один вопрос:

- что строим;
- как выглядит;
- как работает;
- как считаем;
- как отдаём;
- как пишем текст.

Если документ отвечает сразу на 5 вопросов — режем дальше.
