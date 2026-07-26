# P1_TZ: починить кликабельность HTML-макета синастрии

## 1. Packet title
Prototype fix: все модалки и ссылки макета синастрии кликаются без console errors.

## 2. Scope
Ветка `prototype/synastry-html`, worktree `/tmp/synastry-html-fix`, файлы ТОЛЬКО `public/prototypes/synastry/`.

## 3. Дефекты (проверено ревьюером)

1. **`ReferenceError: planetGlyph is not defined`** — `aspect-drilldown.js:128-129` использует `planetGlyph[a.a]/[a.b]`, переменная нигде не определена (в `base.html:62` есть похожий глобальный `glyph`). Ломает ВСЕ пути к модалке аспекта: клик по строке аспекта, по линии колеса, по translation-ссылке.
2. **`renderTranslations` мертва** — `aspect-drilldown.js:65` присваивает функцию, но её никто не вызывает. base.html `openPerson` рендерит переводы inline БЕЗ кнопки «· что значит?». Итог: в макете нет drill-down из «Человеческого перевода».

## 4. Goal (минимальные правки)

1. В `aspect-drilldown.js` определить `planetGlyph` (alias существующего глобального `glyph` из base.html: `const planetGlyph = typeof glyph !== 'undefined' ? glyph : {Солнце:'☉',Луна:'☽',Меркурий:'☿',Венера:'♀',Марс:'♂',Юпитер:'♃',Сатурн:'♄',Уран:'♅',Нептун:'♆',Плутон:'♇',ASC:'AC'};`).
2. Обернуть `openPerson` так же, как обёрнут `renderWheel`: после базового рендера вызывать `renderTranslations()`, чтобы techline-кнопки «{tech} · что значит?» появлялись в каждом переводе.
3. Проверить `partner-time.js`: тоггл «Точное время неизвестно» должен работать без ошибок (precision-линия меняется, поле времени disabled/restore). Если падает — починить тем же минимальным образом.
4. НЕ менять визуал, CSS, тексты. Только JS-починка кликабельности.

## 5. Verification
```bash
cd /tmp/synastry-html-fix/public/prototypes/synastry && python3 -m http.server 8899
# playwright/script: пройти все клики, собрать console errors
```
Обязательные сценарии (все без console errors):
- список → фильтры → карточка Максим (detail)
- клик по строке аспекта (первые 3 и из «Показать все») → модалка открывается, контент (планеты со glyph, сцены, repairs, not-means)
- клик по линии колеса → модалка
- клик по translation-ссылке «Луна △ Венера · что значит?» → модалка; по combined «Марс ☍ Марс + Меркурий □ Меркурий · что значит?» (Денис) → модалка первого аспекта
- «Показать все аспекты ↓» ↔ «Скрыть второстепенные ↑»
- add sheet: открыть, тоггл unknown time, закрыть ×, overlay, Escape
- модалка аспекта: закрыть ×, overlay, Escape, «Понятно»
- сферы: accordion открывается/закрывается

## 6. Evidence
- `git diff` только в `public/prototypes/synastry/`
- список console errors = пусто по всем сценариям
- скриншоты: detail, модалка аспекта (топ и низ), add sheet, combined-tech модалка Дениса

## 7. No-commit rule
Ничего не коммить и не пушить — коммит и пуш в ветку делает ревьюер.
