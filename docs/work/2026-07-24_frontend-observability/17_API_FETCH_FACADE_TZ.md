# Slice 17 — apiFetch compatibility facade hardening

## Цель

Сохранить старый `apiFetch` API поверх `instrumentedFetch`, не протаскивая
служебные options в native RequestInit и корректно нормализуя route labels.

## Разрешённые файлы

- `lib/api-fetch.ts`
- `__tests__/lib/api-fetch.test.ts` (новый)

## Требования

1. Из `options` явно отделить custom `timeout`; в `init` передавать остальные
   RequestInit поля. Ключ `timeout` никогда не попадает в `init`.
2. `timeoutMs` = переданный timeout или 30000 по умолчанию.
3. Если routeLabel уже начинается с любого стандартного метода
   `GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS` + пробел (case-insensitive), не
   добавлять второй method; prefix нормализовать в upper-case.
4. Иначе prefix брать из `options.method || GET`, upper-case.
5. URL, headers/body/credentials/signal и operation label сохранить. Не
   мутировать input options.
6. Убрать дублирующие legacy module-map fragments, оформить канонические
   `AI_HEADER`, named module contract/map, function block/contract и реальные
   emitted events.

## Tests

- mock `instrumentedFetch` boundary;
- default GET route + timeout 30000;
- custom PATCH without duplicated prefix;
- lowercase pre-prefixed delete normalizes to `DELETE ...`;
- custom timeout не находится в init;
- headers/body/credentials/signal preserved;
- input options не мутирован;
- rejection/Response возвращаются прозрачно.

Проверка:

```bash
npx vitest run __tests__/lib/api-fetch.test.ts __tests__/lib/instrumented-fetch.test.ts && npx tsc --noEmit
```

Другие файлы не менять. Ничего не коммить и не пушить — коммит делает ревьюер.
