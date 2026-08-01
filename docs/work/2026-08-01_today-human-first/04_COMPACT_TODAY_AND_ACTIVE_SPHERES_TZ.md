# Packet: compact desktop Today and explicit active spheres

## Phase / Wave

`W-TODAY-HUMAN-FIRST / P4-PRESENTATION`

## Modules

- `M-TODAY-CONVERGENCE-SCREEN`
- `M-TODAY-CONVERGENCE-SPHERE-NAVIGATOR`
- `M-TODAY-CONVERGENCE-HOW-CALCULATED`

## Goal

Today на desktop остаётся компактным продуктовым экраном, а не растянутой витриной; активная сфера объясняется видимой подписью, а calculation disclosure отвечает на пользовательский вопрос, не рассказывает внутреннюю реализацию.

## Exact Write Scope

- `components/today-convergence/today-screen.tsx`
- `components/today-convergence/main-event.tsx`
- `components/today-convergence/sphere-navigator.tsx`
- `components/today-convergence/sphere-drilldown.tsx`
- `components/today-convergence/how-calculated.tsx`
- `__tests__/components/today-convergence/today-screen.test.tsx`
- `__tests__/components/today-convergence/sphere-drilldown.test.tsx`

## Frozen / Out Of Scope

- Не менять API/contracts, impulse modal logic и period explanations.
- Не менять routes, bottom navigation, global shell или соседние экраны.
- Не менять e2e masks/PNG baselines до апрува владельца.
- Не использовать tone-color как единственный active marker.
- Не трогать unrelated/untracked files.

## Must Preserve Invariants

- Desktop content имеет ограниченную читаемую ширину и не создаёт огромную пустую двухколоночную витрину; mobile остаётся одноколоночным.
- Открытие impulse modal не меняет ширину/ряды основного экрана.
- Main event и full sphere evidence chain получают `payload.timezone` и показывают даты из абсолютных EventTime так же, как impulse cards.
- Для сферы с фактами Today видима короткая подпись: количество сигналов и при наличии обеих полярностей `поддержка + напряжение`; dot не является единственным признаком.
- Tile сохраняет `data-testid`, `data-has-today`, route/snapshot semantics и доступное имя, включающее active summary.
- Неактивные 12 сфер остаются компактными и не получают ложных labels.
- `HowCalculated` не содержит `Swiss Ephemeris`, `snapshot`, `LLM` и говорит продуктово: расчёт относительно натальной карты; пик — точный момент; окно — период заметного действия; возможное проявление — ориентир, не гарантия.
- Disclosure сохраняет `aria-expanded/aria-controls`; UI tests проверяют полезный copy и отсутствие внутренних терминов.

## Verification Command

```bash
cd /opt/solarsage-astro && npx vitest run __tests__/components/today-convergence/today-screen.test.tsx
```

## Expected Evidence

- Список файлов.
- DOM summary active/empty tiles и desktop classes.
- Targeted vitest output.
- Подтверждение отсутствия внутренних терминов и неизменности baselines.

## Escalation Rule

Если нужен global shell, route change, API или baseline update — остановиться и доложить архитектору; не расширять packet самостоятельно.

## No Commit Rule

Ничего не коммитить и не пушить — коммит делает ревьюер.
