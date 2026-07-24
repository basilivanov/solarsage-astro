# Slice 01 — privacy hardening error capture

## Цель

Закрыть privacy/fingerprint замечания ревью только в error normalization. Это
самостоятельный кусок; network wrapper, shipper, boundaries и API clients сейчас
не менять.

## Разрешённые файлы

- `lib/log/capture-error.ts`
- `__tests__/lib/capture-error.test.ts`

## Что сделать

1. Любые полученные извне structural strings (`error.name/kind/code`, stack
   function/file и context fields) sanitise + cap. Raw arbitrary `name`, `kind`
   или `code` не должен оказаться ни в envelope, ни в fingerprint input.
   Необычный/небезопасный kind заменять безопасным fallback; code без
   ограниченного constant-like формата опускать.
2. Stack file никогда не должен сохранять origin, query/hash, абсолютный host
   path или пользовательский path segment. Для известных frontend roots
   (`app/`, `components/`, `lib/`, `.next/`, `node_modules/`) оставить безопасный
   relative tail; иначе только безопасный basename/fallback. Function name
   sanitise/cap либо omit. Максимум 8 frames.
3. Route перед payload sanitise: убрать query/hash; UUID, числовые/date/длинные
   opaque path segments заменить стабильными placeholders (`:id`, `:date`).
   Статические route segments сохранить.
4. Dedup tracker должен разделять один и тот же stack fingerprint для разных
   безопасных `operation`/`boundary`/sanitised route, чтобы три HTTP ошибки одного
   wrapper stack не заглушили все остальные операции. Сам error fingerprint в
   envelope остаётся детерминированным и не содержит raw context.
5. Logger/capture по-прежнему никогда не бросает. Сохранить public API и
   существующее force/reset bypass поведение.

## Тесты

Расширить только `__tests__/lib/capture-error.test.ts`:

- malicious/raw `name`, `kind`, `code` с email/token не попадают в envelope и
  fingerprint source/output;
- absolute path + origin + query/hash sanitised; function sanitised;
- максимум 8 frames;
- dynamic route segments не попадают в payload;
- одинаковый Error в разных operations имеет независимый лимит dedup;
- primitive/object rejection не протаскивает raw values.

Проверка:

```bash
npx vitest run __tests__/lib/capture-error.test.ts
```

Не менять никакие другие файлы. Ничего не коммить и не пушить — коммит делает
ревьюер. В конце дать короткий отчёт и результат одной указанной проверки.
