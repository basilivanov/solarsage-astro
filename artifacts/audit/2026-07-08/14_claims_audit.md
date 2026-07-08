# W0 Claims Audit: Basil, 2026-07-08

## LLM unsupported claims

| UI text area | Claim | Evidence result |
|---|---|---|
| Headline | "поддержку в глубоких чувствах и творческих порывах" | partial. Supportive status is proven; "deep feelings" is supported by Pluto/Moon/inner-background scores; "creative impulses" relies on static 5th-house/natal context rather than day-scored transit evidence. |
| Day summary | "Поддерживающий день", "День возможностей" | supported by `day_status=supportive`. |
| Day summary fact | "Луна оппозиция Плутон" | supported only as transit Moon opposite natal Pluto, not transit Pluto. UI label hides that distinction. |
| Reading | "Секспектиль Марса с Луной" | supported signal is `Transit_Mars sextile natal Moon`; text has typo and should be "секстиль". |
| Reading | "Солнце в твоем первом доме" | supported by final day chart and house oracle. |
| Notes | "финансы и отношения сейчас не так важны" | weak/partial. Money score is rank 5 with caution; relationships rank 8/avoid. "Not important" is not the same as "caution/avoid". |
| Why #4 | "длительные транзиты... дома 5 и 2" | unsupported as day evidence. Those houses come from static natal `planet_in_house` signals included in `all_signals`, not from day-scored transit house placements. |
| Why #7 | "5 дом творчества... 2 дом денег..." | unsupported as current-day manifestation for the same reason. |
| Why #9 | "Общайся с близкими для улучшения отношений" | unsupported/contradicts `relationships=avoid` with `Moon opposition Pluto`. |
