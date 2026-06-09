# Отчёт: Production demo guard TZ

Дата: 2026-06-09
Статус: документ подготовлен
Связанный документ: `docs/work/2026-06-09_prod_demo_guard_TZ.md`

## Что сделано

Создано ТЗ для следующего coder-пакета:

`W-PROD-DEMO-GUARD — защита production от demo/mock режима`

Документ положен в:

`docs/work/2026-06-09_prod_demo_guard_TZ.md`

## Зачем это нужно

В проекте есть demo-mode через:

- `NEXT_PUBLIC_DEMO_MODE`;
- `lib/demo-mode.ts`;
- `lib/demo-data.ts`.

Это удобно для разработки, но опасно для production: можно случайно задеплоить приложение, где пользователь видит demo payloads вместо реальных данных из backend API.

Пакет должен закрыть этот риск до MVP/production запуска.

## Что должен сделать кодер

Кодер должен реализовать production safety guard:

1. Добавить централизованную проверку env.
2. Запретить `NEXT_PUBLIC_DEMO_MODE=true` в production.
3. Разрешить demo-mode в development.
4. Разрешить demo-mode в preview/staging только при явном override `ALLOW_DEMO_MODE_IN_PREVIEW=true`.
5. Запретить production fallback на demo data при ошибке API.
6. Обновить `.env.example` / env-документацию.
7. Добавить тесты на production guard.
8. Добавить CI-ready guardrail script, например `guardrails:prod`.

## Что не входит в этот пакет

Не трогать:

- оплату / YooKassa;
- paywall;
- natal frontend;
- Horary credit ledger;
- Today rewrite;
- backend astrology pipeline;
- generated contracts вручную;
- Pydantic schemas без необходимости.

## Acceptance summary

Пакет принимается, если:

- production падает при `NEXT_PUBLIC_DEMO_MODE=true`;
- development с demo-mode работает;
- preview/staging demo-mode требует явный override;
- API error в production не возвращает demo payload;
- tests/guardrails/build evidence приложены;
- env docs обновлены.

## Следующий пакет после этого

После prod guard логичный следующий пакет:

`W-NATAL-FRONTEND-MVP`

Причина: natal calculation уже есть, но полноценного frontend-представления нет.

Натал не нужно смешивать с production guard. Это отдельный coder packet.

## Рекомендация по очередности

1. `W-PROD-DEMO-GUARD`
2. `W-NATAL-FRONTEND-MVP`
3. Потом paywall/YooKassa или другой MVP blocker по приоритету владельца
