# Oracle Audit Rework Report: Wave 11 — `/day` Parity Audit

**Date**: 2026-07-08  
**Branch**: `main` (No commit)  
**Oracle Port**: `3001`  
**Candidate Port**: `7777`  

---

## 1. Audit Decision

This rework audit is **highly reliable** and ready to guide implementation. 

By resolving the anchor selector issue (using text/layout anchors instead of candidate-specific testids for port 3001), we successfully captured the true state of both the 3001 oracle and the 7777 candidate. The visual evidence (10 PNG screenshots) and `summary-v2.json` prove that there are several material visual and structural gaps between the candidate and the oracle.

---

## 2. 3001 Oracle Inventory

### Section Order & Layout Notes
1.  **Date Header**: Displays `"ДЕНЬ"`, `"5 июля"` in bold Russian text.
2.  **Access/Trial Banner**: Displays `"14 дней бесплатного доступа"`, `"Осталось 0 дней"`, and `"Подписка"`.
3.  **Selected Date & Weekday**: `"5 ИЮЛ · ВОСКРЕСЕНЬЕ"`.
4.  **Day Summary Card**: Renders the daily status `"Ровный день"` with icon `🌊` and advice `"без взлётов — занимайся рутиной"`. Below this, it lists 5 compact daily facts:
    *   `☉` тема дня — проявись
    *   `🌖` Убывающая 76% → подводи итоги
    *   `☉` Солнце управитель → день самовыражения
    *   `♂` час Марс → действуй быстро
    *   `🟡` Луна без курса → не подписывай и не начинай
5.  **Concrete Today (КОНКРЕТНО СЕГОДНЯ)**:
    *   Sub-header counts: `"4 благоприятно"`, `"6 осторожно"`.
    *   Expand/collapse CTA: `"все 12 сфер"` / `"свернуть"`.
    *   Rows: Renders exactly 12 rows when expanded.
    *   Short Russian labels: `Работа`, `Деньги`, `Документы`, `Отношения`, `Спорт`, `Общение`, `Здоровье`, `Решения`, `Поездки`, `Творчество`, `Учёба`, `Покупки`.
    *   Scores: **No numeric scores are rendered.**
6.  **Day Chart (КАРТА ДНЯ)**:
    *   Displays an SVG wheel with zodiac signs, house boundaries, house numbers, planet markers, and aspect lines.
    *   Aspect legend: Static list of aspect types with colors: `соединение`, `оппозиция`, `тригон`, `квадратура`, `секстиль`.
    *   Planet count: 7 visible planet markers.
    *   Click interaction: Clicking a planet marker shows a detail popover inside the card.
    *   Popover content (e.g. for Saturn):
        ```
        ♄
        Сатурн
        ♑ Козерог · 4 дом
        дисциплина, ответственность, ограничения. Сегодня акцент через 4 дом — дом и семья.
        ```
7.  **Day Reading (РАЗБОР ДНЯ)**:
    *   Renders three paragraphs of text with proper line heights.
8.  **Why Expanded (ГЛУБЖЕ / Почему так у меня)**:
    *   Expandable accordion for transits.
9.  **Week Strip (Неделя)**:
    *   Displays the weekly horizontal calendar strip.
10. **History Widget (БЛИЖАЙШИЕ ДНИ)**:
    *   Header: `"БЛИЖАЙШИЕ ДНИ"`.
    *   Contains exactly one curated educational historical space card: `1997 · МИССИЯ · «Марс Пасфайндер» на Марсе`.
11. **Disclaimer**:
    *   `"Данные показаны для ознакомления. Перед принятием важных решений проверяйте информацию."`

---

## 3. Candidate Inventory (Port 7777)

### Section Order & Layout Notes
1.  **Date Header**: Identical.
2.  **Access/Trial Banner**: Identical.
3.  **Selected Date & Weekday**: Identical.
4.  **Day Summary Card**: Renders the daily status `"Поддерживающий день"` (mismatch) and has a different structure/fewer compact facts.
5.  **Concrete Today**:
    *   Sub-header counts: `"0 благоприятно"`, `"4 осторожно"` (mismatch).
    *   Leaked raw English keys: `"Crisis Transformation Control"`, `"Inner Background Unconscious"`.
    *   Expand/collapse: Exists.
6.  **Day Chart**:
    *   Planet count: 10 planet markers.
    *   No aspect type legend (renders raw aspect pairs text like `☉ trine ☉` instead).
    *   Click interaction: Shows detail popover, but text is unformatted and in English:
        ```
        ☉
        Солнце
        Знак: Cancer
        Дом: 1
        Движение: прямое
        ```
7.  **Day Reading**: Identical.
8.  **Why Expanded**: Identical.
9.  **Week Strip**: Identical.
10. **History Widget**:
    *   Header: `"В этот день"` (mismatch).
    *   Layout: Multiple compact list rows with a duplicated `1997 · миссия` (mismatch).
11. **Disclaimer**: Identical.

---

## 4. Gap Matrix

| Section / Behavior | 3001 Oracle | Current Main/Candidate | Status | Gap | Required Implementation |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **App Shell / Layout** | Standard container. | Standard container. | `MATCH` | None. | None. |
| **Date Header** | `"ДЕНЬ"`, `"5 июля"`. | Same. | `MATCH` | None. | None. |
| **Trial Banner** | `"14 дней бесплатного доступа"`. | Same. | `MATCH` | None. | None. |
| **Day Summary Card** | `Ровный день` with 5 compact facts. | Different text and fewer facts. | `ALLOWED_DATA_DIFF` | Differences are due to real backend data. | None. |
| **Concrete Today Headers** | Counts and `"все 12 сфер"`. | Same. | `MATCH` | None. | None. |
| **Concrete Today Labels** | Short Russian labels (`Работа`, `Деньги`, etc.). | Raw English technical labels. | `PRESENTATION_GAP` | Leaks raw keys like `"Crisis Transformation Control"`. | Map all backend keys to the 12 short Russian product labels. |
| **Concrete Today Scores** | No numeric scores. | No numeric scores. | `MATCH` | None. | None. |
| **Day Chart Visuals** | SVG wheel with aspect lines. | SVG wheel with aspect lines. | `MATCH` | None. | None. |
| **Day Chart Legend** | Color legend for aspect types. | List of aspect pairs (e.g. `☉ trine ☉`). | `PRESENTATION_GAP` | Aspect legend mismatch. | Replace aspect pairs list with the static colored dot legend. |
| **Day Chart Interaction** | Clicking planet shows formatted popover. | Clicking planet shows unformatted English popover. | `INTERACTION_GAP` | Popover text is unformatted and contains raw English. | Translate sign names (`Cancer` -> `Рак`) and format details in Russian. |
| **`Сегодня важно`** | Hidden. | Hidden. | `MATCH` | None. | None. |
| **Day Reading** | Renders paragraphs. | Same. | `MATCH` | None. | None. |
| **Why Expanded** | `"Почему так у меня"`. | Same. | `MATCH` | None. | None. |
| **Week Strip** | Horizontal calendar. | Same. | `MATCH` | None. | None. |
| **History Block Header** | `"БЛИЖАЙШИЕ ДНИ"`. | `"В этот день"`. | `PRESENTATION_GAP` | Mismatched header. | Change header to `"БЛИЖАЙШИЕ ДНИ"`. |
| **History Block Layout** | Curated card layout. | Multiple compact rows. | `PRESENTATION_GAP` | Candidate shows incorrect list style. | Change layout to render single curated history card. |
| **Disclaimer** | Text at bottom. | Same. | `MATCH` | None. | None. |

---

## 5. Implementation Contract Draft

### Required Frontend Changes

1.  **`components/today/concrete-day-advice.tsx`**:
    *   Ensure all potential backend keys (including `crisis_transformation_control`, `inner_background_unconscious`, `money_security_resources`, `thinking_speech_learning`, `meaning_expansion_vector`) map cleanly to one of the 12 product labels in `SPHERE_PRODUCT_MAP`.
    *   No fallback to raw snake_case or English names.

2.  **`components/today/day-chart.tsx`**:
    *   Replace the raw aspect list (`chart.aspects.slice(0, 5).map(...)`) with a static visual legend of aspect types (`соединение`, `оппозиция`, `тригон`, `квадратура`, `секстиль`) with matching color dots.
    *   Translate the selected planet popover text to Russian:
        *   Zodiac signs (e.g., `Cancer` -> `Рак`, `Aries` -> `Овен`).
        *   Format: `[Sign symbol] [Russian sign name] · [House number] дом`.
        *   Clean up any extra spacing or raw English properties.

3.  **`components/today/astro-history-widget.tsx`**:
    *   Update the header to `"БЛИЖАЙШИЕ ДНИ"`.
    *   Change the visual layout from multiple compact list rows to a single curated historical space card showing the year, category, title, and description.

---

## 6. Evidence Links

*   **Rework Summary**: [summary-v2.json](./artifacts/audit-rework-01/summary-v2.json)
*   **Screenshots (Oracle vs Candidate)**:
    *   Full scroll stitched: [3001-00-full-scroll.png](./artifacts/audit-rework-01/3001-00-full-scroll.png) | [candidate-00-full-scroll.png](./artifacts/audit-rework-01/candidate-00-full-scroll.png)
    *   Top viewport: [3001-01-top.png](./artifacts/audit-rework-01/3001-01-top.png) | [candidate-01-top.png](./artifacts/audit-rework-01/candidate-01-top.png)
    *   Concrete Today: [3001-02-concrete-today.png](./artifacts/audit-rework-01/3001-02-concrete-today.png) | [candidate-02-concrete-today.png](./artifacts/audit-rework-01/candidate-02-concrete-today.png)
    *   Chart before click: [3001-03-chart-before.png](./artifacts/audit-rework-01/3001-03-chart-before.png) | [candidate-03-chart-before.png](./artifacts/audit-rework-01/candidate-03-chart-before.png)
    *   Chart after click: [3001-04-chart-after-click.png](./artifacts/audit-rework-01/3001-04-chart-after-click.png) | [candidate-04-chart-after-click.png](./artifacts/audit-rework-01/candidate-04-chart-after-click.png)
    *   Reading/Why/Week/History: [3001-05-reading-why-week-history.png](./artifacts/audit-rework-01/3001-05-reading-why-week-history.png) | [candidate-05-reading-why-week-history.png](./artifacts/audit-rework-01/candidate-05-reading-why-week-history.png)
