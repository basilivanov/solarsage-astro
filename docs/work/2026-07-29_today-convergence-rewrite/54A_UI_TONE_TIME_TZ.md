# 54A — UI POLISH: TONE TOKENS + TIME FORMAT TZ — Today Convergence Rewrite

Controller packet по coder-loop §10.7. Архитектор: main agent. Кодер: codex CLI
(первый), cwd `/tmp/solarsage-convergence-impl`, ветка `work/today-convergence-2`.

ВАЖНО: ты и есть coder. Skill coder-loop использовать НЕЛЬЗЯ — задачу
выполняешь сам и отчитываешься здесь ревьюеру. Параллельный кодер (54B)
работает над layout/иконками в ДРУГОМ worktree — твои файлы строго по §6.

## 1. Packet title

P7-POLISH-A — цветовая система tone из 03 §3, hero accent рамка, polarity
метки с цветом, честный формат overnight-окон EventTime.

## 2. Phase / Wave

W-TODAY-CONVERGENCE-REWRITE / P7 polish (визуальная приёмка владельца).

## 3. Modules

- `M-WEB-GLOBALS-CSS` — app/globals.css (additive tone tokens)
- `M-TODAY-CONVERGENCE-FORMATTERS` — components/today-convergence/today-formatters.ts
- Hero/impulses/main-event компоненты (тонкие правки классов)

## 4. Goal

Экран перестаёт быть чёрно-белым: polarity имеет цвет по 03 §3 (янтарный
tense, шалфейный supportive, тауп mixed, steady без акцента), hero имеет
рамку 1.5px `--accent` и тон по dayTone, overnight-окна не выглядят
инверсией. Всё — без изменения DOM-контракта (data-testid/атрибуты те же).

## 5. Норматив (прочитать перед кодированием)

- `docs/work/2026-07-29_today-convergence-rewrite/03_W7_FRONTEND_DESIGN_TZ.md`
  §3 (цвета, :34-46), §4 (типографика — проверить hero serif размеры),
  §10 (форматы времени exact/bucket/unknown, :250-256).
- Live-баг overnight: на dev сейчас `пик 10:06, окно 22:42–21:21` (инверсия
  при переносе через полночь UTC→local). Проверено: данные корректны, пик
  внутри окна по абсолютному времени; сломан только формат.
- Текущее: hero `border-primary/40` (components/today-convergence/
  convergence-hero.tsx:88), polarity `text-muted-foreground`
  (impulses-list.tsx:65, main-event.tsx:53), токены tone отсутствуют
  в app/globals.css.

## 6. Exact write scope

- `app/globals.css` — additive :root токены (НЕ менять существующие)
- `components/today-convergence/today-formatters.ts`
- `components/today-convergence/convergence-hero.tsx`
- `components/today-convergence/impulses-list.tsx`
- `components/today-convergence/main-event.tsx`
- `__tests__/components/today-convergence/today-screen.test.tsx` — только
  если атрибуты/классы потребуют синхронизации (DOM-контракт не ломать)

## 7. Frozen / Out of scope

- Layout (рейл, сетка тайлов, иконки) — packet 54B, НЕ трогать:
  today-screen.tsx, sphere-navigator.tsx, sphere-drilldown.tsx,
  sphere-page.tsx, checkin, calendar.
- Backend, contracts, e2e.

## 8. Функциональные требования

### 8.1 Tone tokens (globals.css, additive)

```css
:root {
  --tone-supportive-bg: <мягкий шалфейный зелёный, AA на бумаге>;
  --tone-supportive-fg: <тёмный зелёный>;
  --tone-tense-bg: <мягкий янтарный, AA на бумаге — обязательная
    проверка контраста янтарного fg на бумаге (03 §12)>;
  --tone-tense-fg: <тёмный янтарный/коричневый>;
  --tone-mixed-bg: <нейтральный тауп bg>;
  --tone-mixed-fg: <нейтральный тауп fg>;
}
```

- Конкретные oklch/hex значения подобрать под существующую бумагу;
  красный запрещён (03 §3). Steady — без токена (нет акцента).
- Контраст fg на бумаге ≥ 4.5:1 для текстовых меток (проверить расчётом
  или инструментом, указать значения в отчёте).

### 8.2 Polarity/tone применение

- Метка polarity в impulses/main-event/convergence: класс
  `text-(--tone-{polarity}-fg)` + опционально мягкий фон
  `bg-(--tone-{polarity}-bg)` на метке-чипе. Текст метки остаётся всегда
  (цвет — дополнение, 03 §3). steady: без класса (дефолтный muted).
- Hero (convergence-hero): `border-[1.5px] border-(--accent)` вместо
  border-primary/40; тон hero-блока по dayTone (лёгкий фон
  `--tone-{dayTone}-bg` ТОЛЬКО внутри hero, если dayTone != steady;
  supportive/tense/mixed). Слово «сошлось» остаётся только в hero.
- Никакой заливки тайлов навигатора, календарных чипов, страниц сфер
  (03 §3 запрет).

### 8.3 Overnight EventTime формат (today-formatters)

Правило (дополнение к 03 §10, нормативно зафиксировано архитектором):

- Окно в пределах суток: `окно 13:00–18:00` (как сейчас).
- Окно пересекает полночь: `окно 22:42 → 21:21` (стрелка вместо тире) +
  peak как обычно. Для partofday/date режимов — без изменений.
- Пик НЕ клиппется и НЕ переписывается; если по абсолютному времени пик
  вне окна (не должно случаться) — показывать как есть (не скрывать).
- Реализовать в существующей функции форматирования EventTime;
  unit-тесты: overnight (start > end), same-day, граница ровно 00:00.

### 8.4 Типографика hero (проверка §4)

- Hero заголовок serif 28/34, имя сферы serif 20/26, подписи sans 13/18
  caps-muted, тело sans 15/22, время sans 15 tabular-nums. Если текущие
  классы отличаются — выровнять.

## 9. Must-preserve invariants

- DOM-контракт неизменен (все data-testid/data-* атрибуты).
- `npx vitest run` зелёный; `npx tsc --noEmit` чист; grace_front_lint PASS.
- Axe-разметка (role/aria) не меняется.

## 10. Verification

```bash
cd /tmp/solarsage-convergence-impl
npx vitest run __tests__/components/today-convergence 2>&1 | tail -2
npx vitest run 2>&1 | grep -E "Test Files|Tests "
npx tsc --noEmit 2>&1 | tail -2
python3 scripts/grace_front_lint.py 2>&1 | tail -1
```

## 11. Expected evidence

- Токены + фактические контрасты (числа); diff по файлам; unit-тесты
  overnight; подтверждение неизменности DOM-контракта (grep data-testid
  до/после).

## 12. Escalation rule

Нужно менять layout-файлы 54B или DOM-контракт → СТОП, доложить.

## 13. No-commit rule

Ничего не коммить и не пушить — коммит делает ревьюер.
