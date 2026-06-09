# Addendum: W-NATAL-PREVIEW-MVP — mini landing sales layer

Date: 2026-06-09
Applies to: `docs/work/2026-06-09_natal_preview_mvp_TZ.md`
Status: ready for coder

## 1. Decision

`/readings/natal` must be implemented not as a technical preview table, but as a short premium mini landing for the future paid full natal report.

The screen still uses real calculated data and still works without payment and without LLM. But the first impression should sell the value:

> “Тут тонко и красиво видно, что это про меня. Хочу открыть полный разбор.”

## 2. Product goal

The natal preview has two jobs:

1. Build trust: show that SolarSage has already calculated a real personal chart.
2. Create desire for the future full report: 999 ₽.

It must feel soft, beautiful, feminine-friendly, and personal. Not like a table of planets.

## 3. Backend: calculation stats

Add `calculationStats` to `NatalPreviewRead`.

Recommended schema:

```python
class NatalCalculationStats(CamelModel):
    planets_count: int = 0
    houses_count: int = 0
    aspects_count: int = 0
    spheres_count: int = 0
    special_points_count: int = 0
    scoring_factors_count: int = 0
    dignity_factors_count: int = 0
    total_factors_count: int
    display_label: str
```

Add to preview response:

```python
class NatalPreviewRead(CamelModel):
    ...
    calculation_stats: NatalCalculationStats
    sales_bullets: list[str]
    full_report_price_kopecks: int = 99900
```

## 4. Honest counting rule

Do not hardcode “350+ factors”. Count what the current backend actually computes.

Recommended calculation:

- `planets_count` — actual planets/points returned as planets;
- `houses_count` — actual houses/cusps;
- `aspects_count` — actual computed aspects;
- `spheres_count` — actual scored life spheres;
- `special_points_count` — actual special points returned;
- `scoring_factors_count` — normalized/scoring factors actually used;
- `dignity_factors_count` — dignity/bonification factors if currently computed;
- `total_factors_count` — sum of real counted factors.

`display_label`:

- `>= 350` → `350+ факторов карты`
- `>= 300` → `300+ факторов карты`
- `>= 200` → `200+ факторов карты`
- otherwise exact: `187 факторов карты`

If aspects/special points/midpoints/fixed stars are not currently computed, do not mention them in copy.

## 5. Mini landing structure

Page order:

1. Emotional hero.
2. Personal badges: ASC, Moon, Sun, dominant sphere, strongest visible planet.
3. Calculation depth card.
4. Personal hook from real chart facts.
5. “What you will learn” sales bullets.
6. Spheres preview.
7. Planets preview.
8. Locked chapters.
9. CTA.

## 6. Suggested copy

Hero:

```text
Натальная карта

Тонкий разбор твоего характера, отношений, денег, энергии и внутренних сценариев — по точному времени и месту рождения.
```

Calculation depth card:

```text
Мы уже рассчитали:
✨ {calculationStats.displayLabel}
✨ {calculationStats.spheresCount} сфер жизни
✨ планеты, дома и сильные акценты карты
✨ где твоя сила, а где повторяющиеся сценарии
```

Rules:

- The first line must use backend `calculationStats.displayLabel`.
- The spheres line must use backend `spheresCount`.
- “аспекты”, “узлы”, “Лилит”, “Хирон”, “звёзды”, “мидпойнты” may appear only if backend stats/data prove they are actually computed.

Sales bullets:

```text
В полном разборе ты узнаешь:
— как ты проявляешься в жизни
— почему тебя тянет к определённым людям
— где твой ресурс, деньги и рост
— какие эмоции управляют решениями
— что мешает раскрыться
— на что опираться в ближайший период
```

CTA:

```text
Открыть полный разбор — 999 ₽
```

If payment is not implemented yet, CTA must be disabled or open a “скоро” sheet. It must not navigate to a broken route.

## 7. Visual style

Use the existing playful-feminine palette:

- primary CTA: `#A82F68`
- secondary: `#B7A7F6`
- warm accent: `#F4B17A`
- surface: `#FFF7FB`
- text: `#2C2430`

Visual requirements:

- mobile-first;
- soft cards;
- premium/magic feel;
- one clear CTA visible early;
- technical detail supports the sale, but does not dominate;
- no dense astrology table at the top.

## 8. Component additions

Add these expected components to the packet:

```text
components/readings/natal/landing/natal-calculation-stats.tsx
components/readings/natal/landing/natal-sales-bullets.tsx
```

If the active project path is `components/grace/readings/...`, use that convention instead and do not create duplicate component trees.

## 9. Tests to add

Backend:

1. `calculationStats.totalFactorsCount` is computed from real chart/scoring inputs.
2. `calculationStats.displayLabel` buckets exact / `200+` / `300+` / `350+` correctly.
3. If aspects or special points are absent, copy/stats do not claim them.
4. `fullReportPriceKopecks == 99900`.

Frontend:

1. Successful preview renders mini landing hero.
2. It renders calculation stats from backend `displayLabel`.
3. It renders sales bullets.
4. It renders CTA `Открыть полный разбор — 999 ₽`.
5. CTA does not open a broken payment route while payment is out of scope.
6. First screen is sales-oriented, not a dense planet table.

Guardrail if practical:

- no hardcoded `350+` in production frontend code unless it comes from fixture/test data or backend `displayLabel`.

## 10. Acceptance additions

Add to W-NATAL-PREVIEW-MVP acceptance criteria:

- `/readings/natal` reads like a short beautiful mini landing.
- Calculation depth is shown through backend-computed stats.
- The page creates desire for the future full report at 999 ₽.
- The page does not make unsupported claims about parameters that are not actually computed.
- The first screen is emotionally attractive and CTA-oriented, not a technical table.

## 11. Expected evidence additions

Coder must additionally provide:

1. Screenshot/DOM evidence of the mini landing first screen.
2. Evidence that calculation stats come from backend payload.
3. Evidence that hardcoded `350+` is not used as an unsupported static claim.
4. Screenshot/DOM evidence of CTA `Открыть полный разбор — 999 ₽`.
