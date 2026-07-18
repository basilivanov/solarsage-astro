# R13 Phase B6 R1 — independent acceptance review: rejected

## Verdict

R1 **не принят**. Короткий harness действительно проходит два раза, но его зелёный результат не является доказательством production contract.

Independent baseline:

```text
bash -n scripts/prod-deploy.sh scripts/tests/test-prod-deploy-source-loader.sh  -> rc 0
timeout 240 bash scripts/tests/test-prod-deploy-source-loader.sh                -> rc 0
timeout 240 bash scripts/tests/test-prod-deploy-source-loader.sh                -> rc 0
All 56 test-prod-deploy-source-loader cases passed!
```

Это подтверждает воспроизводимость harness, но не его полноту.

## Independent adversarial evidence

Для каждого эксперимента создавалась свежая временная копия deploy script и harness; production checkout, network, SSH, DB, systemd, commit и push не использовались. В harness менялась только переменная `DEPLOY_SCRIPT`, поэтому результаты относятся к тем же 56 cases.

| Mutation в sandbox deploy copy | Что должна была поймать проверка | Фактический результат |
|---|---|---|
| Wrong-origin branch печатает `$current_origin` в stderr | origin secret-safe diagnostic / canary scan | `rc=0`, `All 56 ... passed` |
| Добавлен прямой `source .env.production` перед loader | loader structural bypass (direct source) | `rc=0`, `All 56 ... passed` |
| `FP_TRES` и `REPO_LAST` checks заменены на `if false` | repository fingerprint physical-record gate | `rc=0`, `All 56 ... passed` |
| Fingerprint mismatch diagnostic печатает `$APPLIED_FP $REPO_FP` | fingerprint values must never appear in diagnostics | `rc=0`, `All 56 ... passed` |
| Добавлен неизвестный `stat -c "%F"` call | exact mock argv / no delegation to real stat | `rc=0`, `All 56 ... passed` |

Эти пять независимых обходов доказывают, что `56/56` сейчас не означает fail-closed.

## P0 harness defects still present

### 1. Runtime output leakage is not scanned by normal cases

`run_case` сохраняет stdout/stderr, но не делает обязательный canary scan для normal cases. Diagnostic при assertion failure извлекает фрагмент raw `stderr` через `grep/head/sed`. Отдельный MUT11 сканирует свой искусственный canary, но этот scanner не подключён к обычным TRN02/FP10 paths.

Обязательно:

- передавать unique hostile-origin, env-secret и fingerprint canaries в normal cases;
- проверять stdout, stderr и audit после каждого relevant case;
- при наличии canary — fail closed;
- при assertion failure печатать только case ID, symbolic reason, rc/count; не печатать raw error/audit/output.

### 2. TRN04 audit сравнивается через command substitution

Сейчас:

```bash
SAVED_TRN04_AUDIT=$(cat "$AUDIT_LOG" ...)
```

Это удаляет trailing LF и позволяет дефектному audit record пройти после реконструкции через `echo`. Промежуточные `head -5`/`wc -l` файлы также остались dead/debug code.

Нужно:

- `cp -- "$AUDIT_LOG" "$TEST_DIR/trn04_actual.txt"`;
- expected записать как physical file;
- сравнить `cmp -s` byte-for-byte, включая финальный LF;
- не печатать raw audit при mismatch.

### 3. `stat` mock делегирует неизвестные argv real `/usr/bin/stat`

```bash
*) /usr/bin/stat "$p" ...
```

Это напрямую нарушает exact mock contract. Независимая mutation с дополнительным `stat -c "%F"` прошла зелёной.

Unknown format, option, path и extra argument должны писать только safe symbolic marker и завершаться non-zero. Никаких real command fallbacks.

### 4. Repository fingerprint output matrix отсутствует

Fingerprint mock всегда делает `echo`, поэтому harness не может корректно создать raw output без LF, CRLF, extra LF, multiline, spaces, short/long. Есть host-file variants, но нет соответствующей repository-command matrix.

Нужно отдавать raw fixture bytes из private file и добавить отдельные cases для каждого physical-record defect. Independent mutation отключения `FP_TRES`/`REPO_LAST` checks сейчас проходит, что это подтверждает.

### 5. Host fingerprint owner/mode matrix не доказана

`stat` mock всегда возвращает `root:root` и `644` для `fingerprint_file`, поэтому нет cases wrong owner, wrong group, mode 600/640/other, unreadable, directory, FIFO.

Сделать path-specific configurable owner/mode/type/permission cases; не менять global default так, чтобы fingerprint special-case скрывал дефект.

### 6. Env/loader matrix неполна

Нет обязательных cases для `.env.production` directory/FIFO/other invalid modes/group, loader directory/FIFO/non-regular/unreadable/failure/no-export/wrong export. Нет structural scan, который ловит direct source, dot-source, `eval`, `set -a` и variable-indirect source.

Independent direct `source .env.production` mutation проходит зелёной.

### 7. Transport matrix неполна

Нет normal cases для fetch failure, empty/credential/multiline hostile origin, current-mode exact absence of origin/access/fetch/checkout, no-arg exact unpinned semantics, wrong argv tuples. Existing checks используют `grep` audit text, а не byte-exact symbolic event records.

Добавить per-case exact audit manifest and secret-canary absence.

### 8. Mutation helper всё ещё generic для MUT01–MUT08

`mutate_and_check_tailored` проверяет anchor, `bash -n`, rc и forbidden log, но не проверяет semantic audit outcome для большинства mutations. Например:

- MUT03 может быть просто неправильным `git remote` argv с rc1, а не доказательством `remote set-url` rejection;
- MUT05 любой ранний rc1 считается caught, без exact bad-fetch marker;
- MUT07 любой early failure считается proof;
- MUT08 не проверяет, что invalid exported path действительно дошёл до controlled stop;
- MUT10 раньше не проверял rc/forbidden; leftover уже проверяется, но нужно доказать, что run дошёл до controlled stop;
- MUT09 только сам печатает `PASS` после grep canonical path — общий static validator mutation не запускается.

Для каждой mutation нужны exact semantic observations, перечисленные в `88_REVIEW...`; generic non-zero/zero запрещён.

### 9. Mutation helper dead code и unsafe implementation details

Осталась неиспользуемая старая `mutate_and_check()` с generic `rc` и md5-only byte proof. Её нужно удалить. В helper использовать fixed-string anchor counts before/after и `cmp`, затем `bash -n`.

`MUT10_RC` и `MUT11_RC` сохраняются, но не участвуют в assertions. Лишние промежуточные assignments/debug artifacts удалить.

### 10. Substitution/controlled-stop proof needs exactness

Pre-count map есть, но controlled-stop insertion не имеет отдельного exact before/after count. Loader substitution counts частично включают comments/error strings. Зафиксировать intended runtime occurrence groups и убедиться, что source drift делает harness red до cases.

## Production script observations

Положительные изменения R1:

- origin mismatch diagnostic generic и без raw origin;
- host fingerprint checks regular/non-symlink/readable + `root:root:644`;
- physical 65-byte checks for host and repository record;
- private `0600` temp and unified failure cleanup;
- HUP/INT/TERM routed through EXIT cleanup;
- original `Old SHA` / `Target SHA` failure report preserved.

Остаётся проверить в R2:

- fingerprint temp cleanup on every malformed/command-failure/mismatch/signal path;
- no test-only env/seam identifiers in production script;
- no out-of-scope behavioral changes;
- generic diagnostics never include fingerprint/origin values.

## Required R2 verification

После исправлений кодер обязан выполнить:

```bash
bash -n scripts/prod-deploy.sh scripts/tests/test-prod-deploy-source-loader.sh
timeout 240 bash scripts/tests/test-prod-deploy-source-loader.sh
timeout 240 bash scripts/tests/test-prod-deploy-source-loader.sh
git diff --check
```

Архитектор повторно запускает независимые mutations минимум для:

1. raw origin diagnostic;
2. direct env source;
3. repository no-LF/extra-LF output;
4. raw fingerprint mismatch diagnostic;
5. unknown stat argv;
6. order/audit extra line and trailing-LF defects;
7. current-mode transport call;
8. loader/ephemeris bypass.

До этого R1 остаётся rejected, несмотря на два зелёных полных прогона.
