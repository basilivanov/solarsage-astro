# 05_TZ: Синастрия — CityPicker с координатами в форме партнёра (срез E)

## 1. Packet title
Синастрия — замена текстового инпута города на переиспользованный CityPicker с автокомплитом, координатами и timezone. Срез E из 5 (добавлен по запросу владельца).

## 2. Phase / Wave
W-SYNASTRY-MVP, fix-wave: pipeline wiring.

## 3. Modules
- Frontend: `components/synastry/synastry-add-sheet.tsx`

## 4. Goal
Форма добавления партнёра получает координаты и timezone города рождения:
1. Текстовый инпут «Город рождения» (~строки 232-244) заменяется на переиспользованный `CityPicker` из `components/onboarding/city-picker.tsx` (`value: City | null`, `onChange(city | null)`; autocomplete `/api/geo/autocomplete`, timezone автоматически из `/api/geo/timezone`).
2. При сабмите в `createSynastryPartner` уходят: `birthCity` (имя города, можно с страной через formatCity), `birthLat`, `birthLon`, `birthTz` — поля уже есть в `PartnerCreatePayload` (`lib/api/synastry.ts:45-54`), клиент менять не нужно.
3. Город остаётся опциональным (как сейчас): не выбран → все четыре поля null. Тоггл «время неизвестно» и остальная логика формы не меняются.
4. UI semantic contract (AGENTS.md): у поля города сохраняются label/стабильный селектор, состояния формы не ломаются.

## 5. Exact write scope
- `components/synastry/synastry-add-sheet.tsx`
- `__tests__/synastry/synastry-add-sheet.test.tsx`

## 6. Frozen / Out of scope
- НЕ трогать `components/onboarding/city-picker.tsx` (если ему не хватает пропса — стоп, эскалация).
- НЕ трогать `lib/api/*`, backend, другие synastry-компоненты.

## 7. Must-preserve invariants
- CityPicker переиспользуется as-is, без копипасты его логики в форму.
- Поведение сабмита без города (null) сохраняется.
- Существующие тесты формы остаются зелёными; добавить кейс: выбор города → в payload уходят lat/lon/tz.

## 8. Verification commands
```bash
npx vitest run __tests__/synastry
```

## 9. Expected evidence
- `git diff --name-only` — ровно 2 файла из scope.
- Вывод vitest (зелёный).
- В отчёте: какие поля payload заполняются из City.

## 10. Escalation rule
Нужен пропс в CityPicker / изменение клиента / backend → стоп, доложить, новый packet.

## 11. No-commit rule
Ничего не коммить и не пушить — коммит делает ревьюер.
