# 01 — Расшифровка 12 продуктовых сфер (канон today_convergence.v1.yml + spheres.v1.yml)

Три слоя связи «полочка → астрология»:
1. `technical_to_product` — техническая сфера (дома/планеты) → продуктовые полочки;
2. `technical_alias_to_product` — алиасы (legal_affairs, travel_adventure…);
3. `planet_to_product` — планета → максимум 2 полочки (для fact-pack страницы сферы).

| Полочка | Техническая база (technical_to_product) | Дома | Планеты (planet_to_product) | Алиасы |
|---|---|---|---|---|
| Работа | work_status_achievement | 10, 6 | Солнце, Марс, Юпитер | career, public_image, technology |
| Деньги | money_security_resources + crisis_transformation_control | 2, 8 | Венера, Юпитер | finance_money |
| Документы | thinking_speech_learning **+ money_security_resources** ⚠️ | **3, 9 + 2, 8** ⚠️ | Меркурий, Сатурн | legal_affairs, partnerships_contracts |
| Отношения | relationships_partnership + home_family_roots | 7, 5, 4 | Венера, Луна | relationships, home_family, inheritance |
| Спорт | body_energy_health | 1, 6 | Марс | daily_routine, service_routine |
| Общение | thinking_speech_learning | 3, 9 | Меркурий | communication_learning, friendship_social |
| Здоровье | body_energy_health **+ inner_background_unconscious** | 1, 6 + 12, 8 | Луна, Нептун | spirituality_inner_growth, healing, hidden_matters |
| Решения | work_status_achievement + crisis_transformation_control | 10, 6, 8 | Сатурн, Плутон | career_ambition, crisis_transformation, philosophy |
| Поездки | **нет в technical_to_product** ⚠️ | **нет** ⚠️ | Уран | travel_adventure (только алиас) |
| Творчество | inner_background_unconscious ⚠️ | 12, 8 ⚠️ | Уран, Нептун | — |
| Учёба | thinking_speech_learning | 3, 9 | **нет прямых** ⚠️ | communication_learning |
| Покупки | money_security_resources | 2, 8 | **нет прямых** ⚠️ | — |

## Найденные аномалии (все влияют на качество текстов)

1. **Документы двоятся** (уже обсуждается в 58): дома 2/8 и аспекты с Венерой/Сатурном тянут тексты в «ценности/ресурсы».
2. **Поездки без базы**: нет записи в `technical_to_product` → нет домов; есть только Уран и алиас. Fact-pack страницы «Поездки» почти пустой → LLM вынужден фантазировать.
3. **Творчество = «бессознательное»**: привязано к домам 12/8 (скрытые процессы) вместо классического 5 дома (творчество, радость, романтика). 5 дом сейчас отдан только Отношениям [7,5].
4. **Учёба и Покупки без планет**: в `planet_to_product` им не досталось ни одной планеты → fact-pack только дома + score → тексты generic.
5. **Здоровье двоятся**: 1/6 (тело) + 12/8 (бессознательное) → тексты про здоровье могут уходить в «скрытые процессы, духовность».
6. **Дом 11 (друзья/комьюнити) не использован нигде**; дом 5 — только у Отношений.

## Вопросы владельцу (для решения по канону)

- Документы: только мысли/бумаги (3/9) или + юридические/имущественные темы (7/4/8)?
- Поездки: дать базу? (классика: 3 дом — ближние, 9 дом — дальние; но 3/9 уже у thinking_speech_learning — допустимо разделение по «ближние/дальние» или отдельный вес).
- Творчество: перенести на 5 дом (отняв его у Отношений или поделив 5/12)?
- Учёба/Покупки: назначить планеты (Учёба → Меркурий/Юпитер; Покупки → Венера)? Лимит max 2 полочки на планету придётся пересмотреть точечно.
- Здоровье: оставить ли 12/8 или ограничить 1/6?
