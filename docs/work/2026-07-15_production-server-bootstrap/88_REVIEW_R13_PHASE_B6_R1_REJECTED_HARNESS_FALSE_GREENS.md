# R13 Phase B6 R1 review — rejected: deploy harness still has false-green paths

## Verdict

`scripts/prod-deploy.sh` и `scripts/tests/test-prod-deploy-source-loader.sh` в текущем виде **не приняты**.

Production hardening движется в правильную сторону: origin diagnostic стал generic, fingerprint проверяется как physical record, появился единый temp cleanup. Но isolated harness пока не доказывает контракт `76_TZ...` и содержит несколько независимых false-green путей.

Production, network, SSH, DB, systemd, deploy, commit и push по-прежнему запрещены.

## P0 findings

### 1. Test seam добавлен прямо в sandbox copy deploy script

Harness вставляет в копию production script:

```bash
export AUDIT_LOG=...
echo "controlled-stop" >> "$AUDIT_LOG"
```

Это дополнительная runtime seam, которой нет в разрешённом списке substitutions. Она меняет поведение проверяемого script и способна скрыть ошибку production path.

Исправить:

- не вставлять `AUDIT_LOG`, `TEST_*`, `MOCK_*` или другие hooks в deploy copy;
- `AUDIT_LOG` передавать только дочерним mock-командам через environment вызова harness;
- controlled stop вставлять ровно один раз в разрешённый anchor как безусловный sandbox-only stop, без чтения test env;
- достижение controlled stop доказывать структурным marker/output harness либо exact отсутствием forbidden install/build calls;
- static scan должен подтверждать отсутствие test seam identifiers в production script и отсутствие лишних вставок в wrapper.

### 2. Substitution gate не exact

`pre_count_*` вычисляются, но не используются. После substitution проверяется только `>= 1`, поэтому source drift, двойная замена или лишний canonical occurrence могут пройти.

Исправить:

- зафиксировать exact expected count для каждого canonical anchor до замены;
- проверить exact count replacement после замены;
- default ephemeris fallback и controlled-stop anchor тоже проверять exact one;
- после substitutions проверить отсутствие всех canonical mutable paths;
- любое форматирование/source drift должно останавливать harness до первого case.

### 3. Mocks принимают лишние argv и делегируют real commands

Текущие примеры:

- `stat` делегирует неизвестный format в `/usr/bin/stat`;
- `git diff`, `git ls-files`, `git checkout --detach`, `git restore` принимают неполные или произвольные argv;
- checkout не требует exact target SHA;
- access mock проверяет строковый glob, а не exact argc/argv и same SHA.

Исправить:

- каждый mock принимает только перечисленные в `76_TZ...` exact argv;
- unknown option, missing/extra arg, wrong ref/path/SHA — symbolic fail marker и non-zero;
- `stat` никогда не делегирует real stat и принимает только sandbox paths plus exact `%a` / `%U:%G` shapes;
- owner/mode overrides должны быть path-specific для env и fingerprint отдельно;
- `git checkout --detach` принимает только configured exact target SHA;
- `git diff`, `ls-files`, `remote`, `fetch`, `rev-parse` проверяют полный argv tuple;
- every `remote set-url`, push и network shape пишет safe marker и fails.

### 4. Матрицы env/loader/fingerprint/source неполные

Обязательные отсутствующие cases:

- `.env.production`: directory, FIFO, additional invalid mode, wrong group;
- loader: directory, FIFO/non-regular, loader failure/no export/wrong export, exact source args;
- structural loader bypass: direct source, dot-source, `eval`, `set -a`, variable-indirect source;
- fingerprint host file: directory, FIFO, unreadable where test semantics permit, wrong owner, wrong group, wrong mode, nonhex, spaces, long record;
- repository fingerprint output: empty, short, long, uppercase, nonhex, spaces, no LF, CRLF, extra LF, two lines/multiline;
- transport: empty/credential/multiline hostile origin and canary absence, fetch failure, access exact argv failure, wrong fetch/ref/checkout argv, no-arg/current exact absence of prohibited transport calls;
- every early failure must prove no loader/build/backup/migration/restart.

Fingerprint mock должен отдавать **raw configured bytes**, например через sandbox fixture file. `echo` нельзя использовать как единственный output generator, потому что он всегда добавляет LF и не позволяет доказать no-LF/extra-LF contract.

### 5. Secret/output safety не доказана

Harness сохраняет stdout/stderr, но не выполняет обязательный canary scan для каждого relevant case. Некоторые debug/failure branches печатали raw stderr/audit.

Исправить:

- assertion failures печатают только case ID, symbolic reason, rc/count/path;
- никогда не `cat`, `head`, `diff` raw stdout/stderr/audit/env/remote/fingerprint data;
- credential-origin, multiline-origin, env secret и два разных fingerprint canary должны отсутствовать в stdout, stderr и audit;
- raw audit используется только для internal byte-exact compare, не выводится пользователю;
- forbidden log содержимое не печатать, проверять только expected symbolic markers/counts.

### 6. Exact order/manifest заменены частично или сортируются

TRN04 сначала делает промежуточный `head -5`, затем перезаписывает файл. Final manifest сортируется перед compare, поэтому reorder/duplicate-position defect может стать зелёным.

Исправить:

- построить полный dynamic expected audit file с sandbox paths and SHA;
- сохранить actual audit как physical file без command-substitution truncation;
- exact `cmp -s` expected vs actual, as written, without sorting;
- expected order обязан включать loader export exact sandbox ephemeris path и controlled stop;
- case manifest and self-test manifest сравнивать byte-exact в canonical order, не сортировать;
- duplicates, missing, extra and reorder должны иметь отдельные harness self-proofs или exact-manifest enforcement.

### 7. Lock/temp cleanup доказан недостаточно

Проверяется только `untracked.*`. Не проверяются fingerprint temp, stdout/stderr output temps, mutation copies, lock descriptors/process cleanup и signal path.

Исправить:

- per-case private directory либо exact per-case cleanup set;
- после каждого success/failure проверить отсутствие `untracked.*`, fingerprint/output temp и неожиданных leftovers;
- synthetic TERM/HUP/INT cases должны доказать cleanup fingerprint temp and child lock release;
- lock contention должен освобождаться trap-ом даже если assertion падает;
- canonical `/tmp/solarsage-deploy.lock` не должен создаваться ни в одном normal/mutation case.

### 8. Mutation self-proof сейчас семантически недостоверна

Текущий helper считает mutation пойманной по generic `rc=1`. Это false-green: syntax error, missing variable, wrong early gate или любой unrelated failure засчитываются как PASS.

Некоторые mutations удаляют отдельную строку из многострочного shell block и могут лишь ломать синтаксис. Anchor checks выполняются regex-ом, post-mutation exact count не проверяется.

Обязательная схема для каждой mutation:

1. fresh byte-exact wrapper copy;
2. exact fixed-string anchor count before = expected;
3. exact one intentional transformation;
4. expected anchor count after;
5. bytes changed via `cmp`, не hash как единственное proof;
6. `bash -n` mutated script обязан пройти;
7. tailored scenario, который активирует именно нарушенный invariant;
8. exact semantic observation: specific audit marker/order, forbidden reach, leftover или canary leak;
9. unrelated early failure не считается caught mutation;
10. mutation copy/temp cleanup.

Минимальные semantic scenarios:

- access removed: `MOCK_ACCESS_RC=1`, harness обязан заметить достижение fetch;
- origin gate removed: hostile credential/multiline origin, harness обязан заметить access/fetch reach;
- set-url allowed: exact forbidden `remote set-url` marker;
- SHA comparison disabled: mismatched origin/main, harness обязан заметить checkout/fingerprint reach;
- wrong fetch/ref/checkout: exact mock rejection marker, не просто rc;
- fingerprint gate bypassed: malformed physical record, harness обязан заметить loader reach;
- loader/default ephemeris bypass: no export + nonexistent fallback, harness обязан заметить controlled-stop/build reach;
- ephemeris validation deleted: invalid file/path, harness обязан заметить controlled-stop/build reach;
- lock substitution broken: canonical lock marker/path detection before execution touches it;
- temp cleanup removed: exact leftover path remains;
- raw origin print: canary scanner обязан увидеть утечку и сделать self-test red.

## Production script review requirements

Перед повторной сдачей сохранить:

- exact canonical origin compare and generic mismatch diagnostic;
- no `remote set-url`;
- fingerprint host file regular/non-symlink/readable and exact `root:root:644`;
- exact 65-byte record (`64 lowercase hex + LF`) for host and repository output;
- private `0600` repository-output temp;
- unified cleanup without replacing/removing existing EXIT failure handler;
- HUP/INT/TERM lead through the same cleanup;
- original `DEPLOYMENT FAILED`, `Old SHA`, `Target SHA` reporting remains;
- no fingerprint/origin values and no test seam identifiers in production script.

Удалить dead/debug code and ad-hoc artifacts before verification.

## Required verification before next handoff

```bash
bash -n scripts/prod-deploy.sh scripts/tests/test-prod-deploy-source-loader.sh
timeout 180 bash scripts/tests/test-prod-deploy-source-loader.sh
timeout 180 bash scripts/tests/test-prod-deploy-source-loader.sh
git diff --check
```

Handoff должен указать:

- exact ordered case manifest;
- exact ordered mutation manifest;
- count and rc of both full runs;
- proof that production/network/DB/SSH/systemd/deploy were not used;
- proof that `/tmp/solarsage-deploy-source-loader-test.*`, ad-hoc `/tmp/b6_*` and fingerprint temps отсутствуют;
- список изменённых файлов.

Повторная сдача не означает acceptance. Финальная приёмка только после независимых adversarial mutations архитектора.
