# Today: коррекция valence 12 сфер

Пакет артефактов до реализации:

| Артефакт | Назначение |
|---|---|
| [`00_TZ.md`](./00_TZ.md) | Нормативный контракт расчёта, API, cache identity, тестов и rollout |
| [`01_TECHNICAL_PREMORTEM.md`](./01_TECHNICAL_PREMORTEM.md) | Blast radius, риски, rollback и pre-flight gates |

Статус: **готово к реализации только после pre-flight решений из раздела 15
ТЗ; production activation запрещена до прохождения merge/rollout gates**.

Изменение не затрагивает астрономические расчёты sidecar. Оно исправляет
API-owned переход от силы фактора (`salience`) к его направлению (`valence`),
12 продуктовым сферам, общему статусу дня и tone трёх горизонтов.
