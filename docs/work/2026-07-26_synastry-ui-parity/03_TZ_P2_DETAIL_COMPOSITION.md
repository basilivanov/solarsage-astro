# 03_TZ (P2): Синастрия UI parity — детальный экран пары (Этап 2)

## 1. Packet title
Synastry UI parity, срез P2: композиция детального экрана — pair hero, score panel, список аспектов, house overlays, translations (+ aspectId contract), spheres, feedback. Без SVG wheel (срез P3).

## 2. Phase / Wave
W-SYNASTRY-MVP, parity wave. Master TZ: `docs/work/2026-07-26_synastry-ui-parity/00_TZ_REACT_PARITY.md` (§3.4, §3.6, §6, §8, §9, §10, §11, §16-19 — читать обязательно). Reference: `proto-detail.png` (эталон) / `impl-detail.png`, prototype CSS — `prototype/detail.css`, `base.html`. Зависит от принятого P1 (tone helper, --syn-* переменные).

## 3. Modules
- Frontend: `components/synastry/synastry-detail-screen.tsx` + новые подкомпоненты (§16 master)
- API micro-extension: translation contract (aspectId)

## 4. Goal
Detail-экран перестаёт быть «семь одинаковых белых карточек» (критерии §21 «Detail», кроме строк про SVG wheel):

1. **Topbar §6.1**: квадратная icon button «‹» (aria-label «Назад»), по центру «Совместимость», справа share icon disabled; h ~58px; pill-кнопку «← Назад» убрать.
2. **Pair hero §6.2**: НЕ карточка; центрировано: 2 overlapping avatar (rounded-квадрат 16-18px), eyebrow relation по-русски, H1 «Ты + {name}» (32-34px serif), meta-строка рождения обоих (owner — из `useProfile`/`hooks/use-profile.ts`; формат `14 мая 1981 · 9 сентября 1987 · 08:15 · Москва`, degrades gracefully при отсутствии полей), approximate → precision badge §6.2.
3. **Score panel §6.3**: отдельная крупная карточка: score в лавандовом квадрате 78×78 serif 34px+, справа verdict(status headline) + summary; снизу 3 tone-блока counters (--syn-* фоны). Использовать heroTitle/heroDescription из API по §6.4 с fallback chain и дедупликацией (не выводить 3 одинаковых абзаца).
4. **Секция «Карта взаимодействия»**: eyebrow + H2 «Где между вами ток» + пояснение (§7.1); карточка-контейнер со светлой gradient surface и placeholder-зоной под wheel (комментарием `WHEEL: P3`); ниже — список аспектов §8: цветной square с символом аспекта (□△☍⚹⚹ по aspectType), локализованные названия §8.2 (соединение/тригон/секстиль/квадрат/оппозиция/квиконс; НЕ sun_trine_moon), orb справа, human short title, hint «Нажми — подробное значение и примеры»; первые 3 по impact (weight desc, orb asc), «Показать все аспекты ↓»/«Скрыть второстепенные аспекты ↑»; click по строке открывает drilldown по aspect.id; строка-кнопка с aria-expanded, keyboard accessible.
5. **House overlays §9**: заголовок+copy §9.1; lavender mini-cards §9.2 (tech 11px plum semibold, human 12-13px, radius 17, без тяжёлой рамки); approximate → специальная карточка §9.3 (никогда не пустой блок).
6. **Translations §10**: заголовок §10.1; карточка §10.2: tone dot, H3 Inter 15/700, tech-подпись справа (dotted underline), текст, scene — отдельная мягкая подложка (НЕ italic-цитата через border-top). «Что значит?» открывает drilldown ТОЛЬКО при наличии aspectId (§10.3: нет aspectId — кнопку не показывать, tech как ID не слать).
7. **Translation contract (backend)**: в pipeline (`run_report_pipeline`, после LLM) каждому translation из narrative сопоставить `aspectId`: нормализованное сравнение translation.tech с aspect.tech_signature из det payload (trim/lower/убрать пробелы; не совпало → null). Типизировать в `apps/api/app/schemas/synastry.py` — заменить `translations: list[dict]` на typed `SynastryTranslation` (tone/title/aspectId/tech/text/scene по §10.3, все optional кроме title). Обновить маппинг в `get_synastry_report`.
8. **Spheres §11**: заголовок §11.1; accordion: tone dot + title + score serif крупно справа + chevron; раскрытие — human description; порядок из API; ПЕРВАЯ открыта по умолчанию (§11.4 — сейчас баг: openSpheres пуст).
9. **Feedback**: визуально по макету (спокойный финальный блок; активная кнопка тёмная ink, не plum).
10. Декомпозиция §16: detail-screen не монолит 400+ строк — подкомпоненты pair-hero/score-panel/aspect-row/house-overlays/translations/spheres/feedback.

## 5. Exact write scope
- `components/synastry/synastry-detail-screen.tsx` (сlim-down, композиция)
- Новые: `synastry-pair-hero.tsx`, `synastry-score-panel.tsx`, `synastry-aspect-row.tsx`, `synastry-house-overlays.tsx`, `synastry-translations.tsx`, `synastry-spheres.tsx`, `synastry-feedback.tsx` (в `components/synastry/`)
- `apps/api/app/services/synastry_service.py` (только translation→aspectId post-processing в pipeline)
- `apps/api/app/schemas/synastry.py` (SynastryTranslation + маппинг в ответе)
- `apps/api/app/api/synastry.py` (только get_synastry_report маппинг translations)
- `__tests__/synastry/synastry-detail-screen.test.tsx` (+ при необходимости новые подкомпонентные)
- `apps/api/tests/test_synastry_service.py`, `apps/api/tests/test_synastry_api.py` (aspectId кейсы)
- `lib/api/synastry.ts` (тип SynastryTranslation; больше ничего)

## 6. Frozen / Out of scope
- SVG wheel — срез P3 (НЕ делать, только placeholder-зона в секции).
- Drilldown sheet переработка — срез P4 (текущий sheet остаётся, открывается по aspect.id).
- List screen (принят в P1), add sheet (P5), backend models/migrations.
- Глобальные шрифты/тема/AppShell/TabBar — не трогать.

## 7. Must-preserve invariants
- data-testid: `synastry-detail-screen` (data-state loading/ready/error), `synastry-hero`, `synastry-score`, `synastry-wheel`, `synastry-aspect` — сохранить; новые testid для секций.
- aria-expanded/aria-controls на раскрываемых строках; icon buttons с aria-label; ≥44px touch targets.
- Цвет не единственный носитель смысла (tone dot + text).
- approximate: дома не выдумываются (§9.3), precision badge в hero.
- Все существующие тесты зелёные; GRACE-разметка; grace_lint PASS.
- Старые репорты (narrative без aspectId) не ломаются: aspectId=null → кнопки «Что значит?» нет.

## 8. Verification commands
```bash
npx vitest run __tests__/synastry
cd apps/api && source .venv/bin/activate && python -m pytest tests/test_synastry_service.py tests/test_synastry_api.py -q
python3 scripts/grace_lint.py apps/api/app
```

## 9. Expected evidence
- `git diff --name-only` — только файлы из scope.
- Вывод проверок (зелёные). В отчёте: как сделан translation→aspectId matching.

## 10. Escalation rule
Нужен wheel/drilldown контракт/models/глобальные стили → стоп, доложить.

## 11. No-commit rule
Ничего не коммить и не пушить — коммит делает ревьюер.
