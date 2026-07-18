# R13 Phase B6 R2 — architect review: rejected, matrix is incomplete

## Verdict

R2 **не принят**. Текущий зелёный результат `65/65` означает только, что реализованные 65 сценариев воспроизводимо проходят. Он не закрывает обязательный контракт из `76_TZ...` и независимые false-green из `89_REVIEW...`.

Кодер сам остановился с незавершёнными todo:

- host fingerprint owner/mode/type matrix;
- env/loader directory/FIFO/failure/export matrix;
- transport empty/credential/multiline/current/no-arg matrix;
- semantic mutation proofs.

Останавливаться и писать handoff до закрытия всех пунктов ниже запрещено.

## Scope

Разрешённые файлы остаются прежними:

- `scripts/tests/test-prod-deploy-source-loader.sh`;
- `scripts/prod-deploy.sh` — только если независимая проверка выявит defect production origin/fingerprint/temp contract;
- следующий coder handoff/review doc в этой папке.

Не менять workflow, frontend, backend, systemd, nginx, DB и остальные scripts. Не запускать production/network/SSH/DB/systemd/deploy. Не делать commit/push.

## 1. Исправить фундамент harness до добавления cases

### 1.1 Signal-safe cleanup

Текущий harness использует один trap для `EXIT INT TERM HUP`, который только удаляет каталог. Сделать явный cleanup и signal handlers с соответствующим non-zero exit, чтобы signal не мог продолжить harness после удаления `TEST_DIR`. Учитывать и завершать background lock-holder, если он уже запущен. Cleanup должен быть idempotent.

### 1.2 Exact controlled-stop insertion

До `sed` проверить, что install/build anchor встречается ровно один раз. Вставить ровно один sandbox marker, который:

1. пишет безопасное событие `controlled-stop` в audit;
2. завершает wrapper с rc 0.

После вставки проверить exact count marker = 1 и anchor = 1. Любой source drift должен завершать harness до первого case.

### 1.3 Exact mock records

Не писать audit через неоднозначный `echo "$*"`. Для `git`, access, loader, fingerprint, stat и mktemp:

- проверять exact argc/argv;
- unknown option/extra arg/path — non-zero и safe symbolic rejection marker;
- audit record формировать через `printf` и `%q` либо другой однозначный byte-stable формат;
- никогда не делегировать unknown call реальной команде;
- не писать secret values в audit.

Access mock сейчас проверяет glob по `$*`; заменить на exact `argc == 3`, `$1 == --check`, `$2 == --expected-sha`, `$3 == expected SHA`.

`stat` mock должен принимать только exact shape `stat -c <allowed-format> <exact-sandbox-path>`. Любые перестановки, дополнительные аргументы и неизвестный format обязаны падать.

### 1.4 Per-case fail-closed checks

После **каждого** `run_case`, включая expected failures:

- forbidden log пуст;
- нет safe rejection marker, если этот case не тестирует его явно;
- нет sandbox temps (`untracked.*`, fingerprint temp и другие временные файлы wrapper);
- stdout/stderr/audit не содержат origin credential canary, env secret canary и fingerprint values/canaries;
- assertion при ошибке печатает только case ID, expected/actual rc и symbolic reason — не raw stdout/stderr/audit.

Canaries должны реально участвовать в scenario. Строка `FP_CANARY`, которой нет в fingerprint records, ничего не доказывает. Использовать две разные валидные 64-hex строки как host/repository canaries и проверять отсутствие обеих в diagnostics. Env file должен содержать synthetic secret canary, но нормальный loader не должен его читать/логировать.

## 2. Полная env/loader matrix

Добавить отдельные manifest IDs, setup и exact stage/audit assertions:

### `.env.production`

- directory — fail до loader;
- FIFO — fail без блокировки (FIFO не открывать; только file-type gate);
- mode `000`, `400`, `600`, `640`, `644`, `660`, `777`;
- owner `astro:astro` success, wrong user, wrong group, `root:root` fail;
- valid 600 and 640 remain success;
- missing/symlink remain.

У `stat` должны быть отдельные path-specific env owner/mode overrides, не global variables, которые случайно меняют fingerprint answers.

### Loader path/runtime

- missing;
- symlink;
- directory;
- FIFO;
- unreadable regular file;
- valid regular readable file;
- `prod_env_load` returns non-zero;
- loader returns 0 but does not export ephemeris;
- loader exports wrong/nonexistent path;
- loader receives wrong env path or wrong domain — mock rejects exact argv.

После каждого loader failure: no controlled-stop, no forbidden install/build.

### Structural loader boundary

Добавить общий static validator, запускаемый на baseline и на mutation copies. Он должен fail closed при появлении в deploy script обходов loader, минимум:

- `source .env.production`;
- `. .env.production`;
- `set -a` + direct source;
- `eval` для env loading;
- variable-indirect source/dot-source `.env.production`.

Не делать проверку одной хрупкой literal-строкой. Она должна анализировать executable lines, не принимать комментарий как доказательство. Независимая mutation из `89_REVIEW...` с direct source обязана сделать весь harness non-zero.

## 3. Полная host/repository fingerprint matrix

### Host file

Добавить cases:

- directory;
- FIFO;
- unreadable regular file;
- wrong owner;
- wrong group;
- modes 600, 640, 660, 777 и любой leading-zero mock response, кроме exact accepted `644`;
- nonhex exact-length;
- spaces exact/near length;
- long value;
- уже имеющиеся missing/symlink/empty/short/uppercase/no-LF/CRLF/extra-LF/multiline.

Fingerprint `stat` responses сейчас hardcoded `root:root`/`644`, поэтому negative owner/mode cases невозможны. Сделать отдельные configurable fingerprint overrides.

### Repository command output

Сохранить raw fixture delivery через `cat`, добавить недостающие:

- empty output;
- long single line;
- exact 64 nonhex + LF;
- valid record distinct from host для mismatch;
- command failure with partial output, чтобы partial bytes не попали в diagnostic;
- current no-LF/CRLF/extra-LF/short/uppercase/spaces/multiline.

Для каждого fingerprint failure доказать: loader и controlled-stop не достигнуты; оба 64-hex canary values отсутствуют в stdout/stderr/audit; fingerprint temp удалён.

## 4. Полная transport/mode matrix

Добавить exact physical audit manifests без сортировки для трёх success paths:

### `--current`

Разрешены HEAD + clean-source + fingerprint + loader + ephemeris + controlled-stop. Запрещены `remote get-url`, access, fetch, `origin/main`, checkout.

### no-arg git mode

Разрешены origin check, exact fetch and checkout flow. Access call запрещён, потому что SHA не pinned. Audit/вывод не должен утверждать, что pinned access proof выполнен.

### `--expected-sha`

Exact order:

1. HEAD / clean-source-before;
2. origin get-url;
3. access exact expected SHA;
4. fetch `--prune origin main`;
5. clean-source-after;
6. rev-parse `origin/main`;
7. checkout `--detach` exact target;
8. fingerprint command;
9. loader exact args/export path marker;
10. controlled-stop.

Добавить failures:

- empty origin;
- credential-like origin with unique canary;
- multiline origin with unique canary;
- wrong origin;
- access failure;
- fetch failure;
- post-fetch SHA mismatch;
- wrong fetch argv;
- wrong ref argv;
- wrong checkout argv.

На origin mismatch не должно быть access/fetch/set-url/checkout/fingerprint/loader. Raw hostile origin отсутствует в stdout/stderr/audit.

Invalid CLI cases должны отдельно доказывать пустой audit: no env stat, git, access, fingerprint or loader before rc 2.

## 5. Ephemeris proof

Добавить loader modes и exact assertions:

- valid exported existing readable/traversable directory reaches controlled-stop;
- no export uses substituted guaranteed-nonexistent default and fails;
- nonexistent path fails;
- regular file fails;
- non-readable/non-traversable directory fails where effective test-user permissions make this meaningful;
- loader failure fails before ephemeris marker;
- audit records only safe symbolic exported path identity, not env values.

`MUT08` сейчас не является proof: mutation удаляет validation, но scenario оставляет valid ephemeris, поэтому rc 0 был бы и без mutation. Для MUT08 обязательно передать nonexistent/file path и доказать, что mutated wrapper reaches `controlled-stop`, тогда как baseline scenario fails.

## 6. Mutation engine — без tautological PASS

Общий mutation runner обязан:

- брать fresh byte-exact baseline wrapper;
- fixed-string/precise anchor pre-count exact 1;
- mutation post-count exact expected;
- доказать изменение через `cmp`, не md5;
- `bash -n`;
- запустить тот же validator/common runner, который защищает normal cases;
- проверить exact semantic audit, rc и forbidden/temp/canary contract;
- mutation считается PASS только когда общий guard становится red по ожидаемой причине.

Исправить конкретно:

- MUT03: вставить реальный `git remote set-url origin <safe-sentinel>` либо exact equivalent, а не превращать `get-url` в бессмысленный набор аргументов;
- MUT06: мутировать конкретные host/repository physical-record gates, а не удалять весь fingerprint section;
- MUT07: доказать fingerprint reached, loader call absent, default nonexistent и controlled-stop absent;
- MUT08: invalid exported path + controlled-stop reached только после удаления ephemeris validation;
- MUT09: прогнать mutation через общий substitution/static validator; текущий `grep canonical path -> PASS` тавтологичен;
- MUT10: assert rc, exact reached-controlled-stop marker, forbidden empty, затем exact leftover; `MUT10_RC` нельзя оставлять unused;
- MUT11: прогнать raw-origin diagnostic mutation через общий canary scanner и ожидать rejection; `MUT11_RC` нельзя оставлять unused.

Убрать duplicate `leftovers=` и duplicate comments/debug remnants.

## 7. Production script checks before handoff

Проверить, не меняя production behavior без доказанного defect:

- fingerprint temp cleanup на command failure, malformed output, mismatch и signal;
- cleanup failure не маскирует исходный deploy rc (`rm ... || true` внутри failure cleanup, если требуется);
- no raw origin/fingerprint values in diagnostics;
- no test-only seams/env identifiers;
- direct env loading отсутствует;
- existing `Old SHA` / `Target SHA` failure reporting сохранено.

## 8. Required completion evidence

После **последнего** изменения выполнить:

```bash
bash -n scripts/prod-deploy.sh scripts/tests/test-prod-deploy-source-loader.sh
timeout 300 bash scripts/tests/test-prod-deploy-source-loader.sh
timeout 300 bash scripts/tests/test-prod-deploy-source-loader.sh
git diff --check
```

Case count обязан существенно вырасти выше 65 и exact manifest должен перечислять каждый новый ID. Число само по себе не acceptance criterion.

В handoff указать:

- полный ordered manifest по группам;
- два независимых полных прогона с exact rc/count;
- результат каждой из 11 semantic mutations;
- temp/forbidden/canary cleanup proof;
- список изменённых файлов;
- explicit statement: production/network/DB/SSH/systemd/deploy/commit/push не выполнялись.

До выполнения всего документа не останавливаться и не писать «выполнено».
