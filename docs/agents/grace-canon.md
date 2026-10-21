# GRACE Canon: разметка, структурные логи, навигация по коду

> Часть operative canon репозитория (вместе с AGENTS.md и `docs/agents/*`).
> Извлечено из AGENTS.md 2026-10-22; AGENTS.md содержит резюме и ссылку на этот файл.
> Обращаться сюда за: шаблонами GRACE-маркеров для новых файлов/функций,
> правилами структурного логирования, навигацией по кодовой базе через маркеры.
> `docs/GRACE_CANON.md` — policy baseline канона; AGENTS.md + этот документ —
> operative canon этого репозитория; при расхождении действует operative canon.

Новые кодовые файлы и существенные изменения в существующих файлах должны сохранять GRACE-разметку: `AI_HEADER`, `START_MODULE_CONTRACT`, `START_MODULE_MAP`, а для нетривиальных публичных функций/классов — `START_FUNCTION_CONTRACT` и `START_BLOCK`. Старые файлы не переписывать ради формата отдельно от задачи.

## Шаблон файла

Использовать синтаксис комментариев языка файла (`#` для Python, `//` для TypeScript/TSX):

```ts
// ############################################################################
// AI_HEADER: MODULE_NAME — one-line description of what this module does
// ROLE: Detailed role. Who calls it, what it provides.
// ############################################################################

// START_MODULE_CONTRACT: M-MODULE-NAME
// purpose: What this module does. Who calls it, what it returns/provides.
// owns:
//   - path/to/file.ts
// inputs: List of inputs, parameters, or dependencies.
// outputs: What this module returns or provides.
// dependencies: Local modules, services, external APIs.
// side_effects: File writes, DB inserts, network calls, subprocess spawns.
// emitted_logs: Exact event names emitted by this module, or "none".
// invariants: Conditions this module must preserve.
// failure_policy: What errors are raised, returned, logged, or swallowed.
// END_MODULE_CONTRACT: M-MODULE-NAME

// START_MODULE_MAP: M-MODULE-NAME
// public_entrypoints:
//   - exportedFunction
//   - ClassName.methodName
// semantic_blocks:
//   - BLOCK_NAME: what this block owns
// owned_tests:
//   - __tests__/...
// END_MODULE_MAP: M-MODULE-NAME
```

`owned_tests` в MODULE_MAP обязателен (кроме тривиальных файлов без тестов — тогда писать `owned_tests: none`): это быстрый указатель «какой тест гонять для этого файла». Срезовая/UC-приёмка описывается отдельно в `grace/verification-matrix.md`.

Для функций:

```ts
// START_BLOCK: BLOCK_NAME
export async function runThing(input: string): Promise<Result> {
  // START_FUNCTION_CONTRACT: F-M-MODULE-NAME.runThing
  // purpose: What this function does.
  // inputs: input — description.
  // returns: Result — meaning.
  // side_effects: Network calls, DB writes, log events.
  // emitted_logs: ui.fetch_started, ui.fetch_succeeded, ui.fetch_failed.
  // error_behavior: Throws/returns on specific failures.
  // END_FUNCTION_CONTRACT: F-M-MODULE-NAME.runThing
}
// END_BLOCK: BLOCK_NAME
```

## Адаптация логов под этот репозиторий

Не импортировать `grace_control.core.structured_logger.GraceLogger`: такого runtime в SolarSage Astro нет. Использовать существующие механизмы:

- Frontend/browser: `logEvent`, `logStart`, `logSuccess`, `logFailure` из `lib/log/index.ts`. Для старого кода допустим существующий `logger.*`, но новые важные бизнес-события лучше писать через typed `logEvent`.
- Frontend server/RSC/route handlers: если файл уже использует GRACE stdout envelope, использовать `lib/grace/log.ts`; не смешивать два логгера в одном модуле без причины.
- Backend FastAPI: `log_event`, `bind_log_context`, `log_block` из `apps/api/app/core/logging.py`.
- Список допустимых событий берётся из `lib/log/events.gen.ts` и `apps/api/app/core/logging_events.py`. Новое событие сначала добавить в registry/contract, затем использовать в коде.
- В `emitted_logs` в contract указывать реальные event names (`ui.fetch_started`, `day.viewed`, `system.error`), а не произвольные фразы.
- Каждый структурный log должен иметь `slice`, `module`, `block`, `event`, `correlation_id`; frontend logger заполняет defaults, но для нового feature-кода передавать точные `slice/module/block` в `meta`.
- В логах запрещены raw Telegram initData, bot token, session cookies, email/phone и точные персональные данные без редакции. Использовать существующий redactor.
- Логгер не должен ломать пользовательский flow: ошибки логирования swallowing/handled, бизнес-ошибки логируются и возвращаются по контракту.

## Навигация по коду через GRACE-маркеры

Не всасывать файлы целиком «на всякий случай»: кодовая база размечена machine-grepable якорями, и ими нужно пользоваться.

1. Найти модуль по ответственности: `rg -n "purpose:" <dir>` или по имени `rg -n "M-API-PROMO"`.
2. Сначала читать только `MODULE_CONTRACT` (purpose/owns/inputs/outputs/side_effects/invariants) и `MODULE_MAP` (public_entrypoints, semantic_blocks, owned_tests) — интерфейс и покрытие видны без реализации.
3. Реализацию читать по блокам: `rg -n "START_BLOCK: REDEEM"` → читать до соответствующего `END_BLOCK`, а не весь файл.
4. Поведение функции — через `START_FUNCTION_CONTRACT` прямо над ней; какой тест гонять для файла — через `owned_tests` в MODULE_MAP.
5. Трассировка событий — по точным именам из `emitted_logs` (`rg -n "promo.redemption_succeeded"`), не по свободному тексту.
6. Рабочие слайсы — `docs/work/YYYY-MM-DD_<slug>/`: сначала master/00_TZ, затем только нужный `NN_..._TZ.md`, не весь каталог.
7. Чем доказывать корректность — `grace/verification-matrix.md`: фича маппится на slice gates и UC-строку (модули на happy path → gates → scenarios S1..Sn); матрица индексируется по срезам/UC с зонтичными module-ID, per-file тесты — через `owned_tests`.

Ограничение: маркеры — комментарии; `scripts/grace/check-markers.sh` проверяет их наличие и парность, но не истинность. Для навигации им доверять можно; перед правкой читать сам код блока и его callers.
