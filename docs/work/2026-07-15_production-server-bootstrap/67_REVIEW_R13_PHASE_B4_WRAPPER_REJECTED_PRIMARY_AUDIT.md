# R13 Phase B4 — wrapper harness rejected after independent review

## Result

Phase B4 не принимается. Независимый запуск из свежего shell:

```text
bash -n ... -> rc 0
test-prod-github-wrapper.sh -> rc 0 (48 product cases)
повторный независимый запуск -> rc 0 (48 product cases)
git diff --check -> rc 0
```

Зелёный count не равен доказанному контракту. Production не запускался, сеть/SSH/GitHub/commit/push не использовались.

## Blocking findings

### 1. Primary audit не доказывает ровно один target invocation

Моки `scripts/tests/test-prod-github-wrapper.sh:93-117` открывают audit через `>`, а `run_case` проверяет только финальный файл. Если wrapper regression вызывает один target дважды, второй вызов перезапишет первый идентичным audit и valid/propagation case останется зелёным. Self-test 6 использует отдельный append mock, но не меняет primary mock и не прогоняет общий `run_case`; это не закрывает production contract.

Требование: primary audit должен append invocation records и byte-exact expected file должен содержать ровно одну запись. Любой второй вызов, пропущенный вызов или другой target — fail.

### 2. Safe output scan — no-op

Блок около `:749-759` объявляет `forbidden_found`, но никогда его не меняет и не завершает ошибкой. Он не проверяет stdout/stderr, raw `SSH_ORIGINAL_COMMAND`, injection sentinel или generic-only diagnostics. Сейчас wrapper может вывести hostile command и harness останется зелёным.

Требование: для reject cases stdout пуст; stderr соответствует одному из трёх generic сообщений и не содержит raw command/sentinel. Для valid cases stdout/stderr пусты. Ошибочные diagnostics harness не должны печатать содержимое файлов.

### 3. Hostile matrix заявлена шире фактической

- `DEP_N04`/`SRC_N04` добавляют `g` к уже 40-символьному SHA, то есть проверяют 41 bytes, а не ровно 40-char non-hex.
- Отдельного backtick case нет.
- Отдельного `&&` case нет: текущий label объединяет pipe/&&, но значение содержит только pipe.

Требование: исправить 40-char non-hex replacement и добавить симметричные backtick и `&&` cases для обоих verbs.

### 4. Fail-closed path substitution проверяет весь текст, не executable dispatch

Pre/post `grep -cF` может пройти, если canonical path находится в comment/contract, а executable `exec /bin/bash` уже указывает на другой absolute path. Тогда тест способен вызвать реальный target. Проверять нужно ровно runtime dispatch records: два canonical target occurrences в executable `exec /bin/bash` lines до замены, после — ровно два sandbox paths и ноль canonical executable paths; неизвестный/дополнительный executable target должен падать до valid cases.

### 5. GRACE function map неполный

Новый существенный harness содержит module contract, но не содержит `START_MODULE_MAP` и function contracts для публичных helpers, несмотря на AGENTS.md. Добавить структурную разметку, не переписывая production wrapper.

## Non-blocking observations

- Само наличие 9 self-tests полезно, но они должны быть дополнением к реальным assertions, а не заменой primary invocation checks.
- `LC_ALL=C` для ASCII lowercase regex допустим как отдельный hardening, но не смешивать с этой минимальной починкой без необходимости.
- Handoff `66_HANDOFF...` не является acceptance; он отражает coder evidence и должен быть дополнен/заменён только после нового независимого прогона.
