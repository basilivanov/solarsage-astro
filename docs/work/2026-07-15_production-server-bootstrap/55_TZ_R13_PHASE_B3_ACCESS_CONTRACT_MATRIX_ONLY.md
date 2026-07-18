# R13 Phase B3 — только полный access contract matrix

## Цель прохода

Исправить только `scripts/tests/test-prod-github-access.sh` и минимальные defects в `scripts/prod-github-access.sh`, которые новый тест сначала воспроизводит красным. Не трогать wrapper/workflow/deploy harness, `51` handoff, R12 suite и другие production files.

Текущий access harness не изменился по существу после R2: 31 case покрывает лишь малую часть матрицы; `passphrase_key` генерируется, но не используется; output scan и реальная temp cleanup отсутствуют.

Production apply/deploy, real network/SSH/GitHub API/fetch/checkout/push, commit/push запрещены.

## 1. Архитектура fixture

1. Один `TEST_DIR`, trap `EXIT INT TERM HUP`.
2. Создать immutable baseline tree внутри `$TEST_DIR/baseline`:
   - `.ssh` и checkout keypair;
   - Actions public key и сохранённый safe expected type/base64 только для file construction, но не для вывода;
   - wrapper/template copies;
   - fake repo/`.git`;
   - origin state.
3. `reset_fixture` полностью удаляет live sandbox tree и восстанавливает его через `cp -a` из baseline. Он также заново создаёт path-substituted production-script copy и очищает audit/output/temp files. Никакой case не должен оставлять mutated script/keys/template следующему case.
4. PATH передавать только child invocation. Real local `ssh-keygen` разрешён при setup baseline и для sandbox paths; child получает fail-closed mock.
5. Сделать helpers:
   - `run_case expected_rc id label command...`;
   - `snapshot_mutable_state`;
   - `assert_mutable_state_unchanged` (existence + `cmp`, включая origin);
   - `assert_no_mutation_audit`;
   - `assert_no_forbidden_git`;
   - `assert_no_temp_files`;
   - `assert_output_safe`.
6. После каждого negative case выполнять appropriate snapshot/audit/temp/output assertions, а не только сравнивать rc.
7. В конце fail, если `CASE_COUNT < 75`. Это только нижний sanity threshold; acceptance всё равно определяется перечисленной ниже матрицей.

## 2. Fail-closed mocks

### `id`

Поддерживает только `-u` и `-un`; неизвестный argv — fail.

### `stat`

- Только sandbox paths.
- Real mode через `/usr/bin/stat`.
- Owner map по exact normalized path category.
- `MOCK_BAD_OWNER_PATH` портит только один selected path.
- Unknown format/path — fail.

### `chown`

- Exact allowed owner + sandbox target shapes.
- Audit без key material.
- Внешний/unknown target — fail.

### `mv`

- Validate source и destination внутри sandbox.
- Exact two-operand invocation.
- `MOCK_MV_FAIL_DEST` для каждого destination.
- `/usr/bin/mv` только после validation.

### `git`

Разрешить только exact argv:

- `-C <repo> remote get-url origin`;
- `-C <repo> remote set-url origin <canonical-alias-url>`;
- `-C <repo> ls-remote --exit-code origin refs/heads/main`.

Unknown args/subcommands, fetch, checkout, push — separate forbidden audit + non-zero. Missing-origin mode должен возвращать non-zero, не default URL.

### `curl`

Проверить exact semantic argv: silent/error, `/dev/null` body, `%{http_code}`, connect timeout 5, max time 10 и exact API URL. Никогда не сеть. Configurable rc/status; raw body не выводить.

### `timeout`

Поддержать exact `15s git ... ls-remote ...`. Normal mode вызывает sandbox mock git; timeout mode сразу возвращает `124`. Unknown invocation — fail.

### `ssh-keygen`

Разрешить production child только exact `-y -P '' -f <sandbox-private>` и `-l -f <sandbox-key>` shapes; делегировать real binary только после sandbox validation. Никаких real `/etc/solarsage` exceptions.

### `mktemp`/`python3.12`

Не подменять production validation semantics. Если нужны failure injection:

- `mktemp` mock поддерживает ожидаемые canonical prefixes внутри sandbox и configurable failure by prefix;
- `python3.12` можно вызывать real только с copied production inline helper и sandbox file args; либо wrapper validates that all path args are sandbox. Нельзя дать helper читать/писать real paths.

## 3. Обязательные cases и IDs

### CLI / user boundary

- `CLI01` no args — rc 2, no stat/git/curl/chown/mv.
- `CLI02` unknown flag — rc 2, no side effects.
- `CLI03` apply + preflight — rc 2.
- `CLI04` preflight + check — rc 2.
- `CLI05` duplicate same action — rc 2.
- `CLI06` expected-sha missing value — rc 2.
- `CLI07` expected-sha without check — rc 2.
- `CLI08` duplicate expected-sha — rc 2.
- `CLI09` short SHA — rc 2.
- `CLI10` long SHA — rc 2.
- `CLI11` uppercase SHA — rc 2.
- `CLI12` non-hex SHA — rc 2.
- `CLI13` non-root apply — rc 1, mutable state unchanged.
- `CLI14` preflight wrong user — rc 1.
- `CLI15` check wrong user — rc 1.

### Path/type/mode/owner boundary

Для каждого case: rc 1 до mutation; state unchanged.

`.ssh`:

- `PATH01` missing;
- `PATH02` symlink;
- `PATH03` regular file вместо directory;
- `PATH04` wrong mode;
- `PATH05` wrong owner.

Checkout private:

- `PATH06` missing;
- `PATH07` symlink;
- `PATH08` FIFO;
- `PATH09` directory;
- `PATH10` wrong mode;
- `PATH11` wrong owner.

Checkout public:

- `PATH12` missing;
- `PATH13` symlink;
- `PATH14` FIFO;
- `PATH15` directory;
- `PATH16` wrong mode;
- `PATH17` wrong owner.

Actions public:

- `PATH18` missing;
- `PATH19` symlink;
- `PATH20` FIFO;
- `PATH21` directory;
- `PATH22` wrong mode;
- `PATH23` wrong owner.

Wrapper:

- `PATH24` missing;
- `PATH25` symlink;
- `PATH26` directory;
- `PATH27` wrong mode;
- `PATH28` wrong owner;
- `PATH29` byte mismatch.

Known-hosts template:

- `PATH30` missing;
- `PATH31` symlink;
- `PATH32` directory;
- `PATH33` wrong mode;
- `PATH34` wrong owner;
- `PATH35` changed bytes.

Repo:

- `PATH36` repo missing;
- `PATH37` repo symlink;
- `PATH38` `.git` missing;
- `PATH39` `.git` symlink.

Installed-state checks after a successful apply:

- `PATH40` installed known-hosts changed;
- `PATH41` installed known-hosts symlink/wrong mode/wrong owner (may use three subcases and increment count);
- `PATH42` config symlink/wrong mode/wrong owner;
- `PATH43` authorized_keys symlink/wrong mode/wrong owner.

### Key validation

- `KEY01` matching no-passphrase checkout pair passes.
- `KEY02` checkout public mismatch fails.
- `KEY03` passphrase-protected checkout private fails. Реально заменить live pair на generated passphrase fixture; не просто генерировать unused file.
- `KEY04` malformed private fails.
- `KEY05` malformed public fails.
- `KEY06` output for all key failures is safe.

Actions public variants:

- `KEY07` exact valid ed25519 one LF line passes;
- `KEY08` empty;
- `KEY09` extra blank line;
- `KEY10` CRLF;
- `KEY11` two lines;
- `KEY12` options prefix;
- `KEY13` wrong key type;
- `KEY14` invalid base64;
- `KEY15` PEM/private material;
- `KEY16` no final LF.

Invalid cases rc 1, no mutation, safe output.

### Config contract

- `CFG01` absent -> first apply exact canonical block.
- `CFG02` unrelated bytes before/after block preserved via `cmp` against expected binary file.
- `CFG03` second apply byte-identical for config, authorized_keys, known_hosts and origin.
- `CFG04` duplicate BEGIN.
- `CFG05` duplicate END.
- `CFG06` unmatched BEGIN.
- `CFG07` unmatched END.
- `CFG08` END before BEGIN.
- `CFG09` exact alias outside managed block.
- `CFG10` lowercase `host github.com-solarsage-prod` outside block. SSH keywords case-insensitive; current production code вероятно должен быть минимально исправлен после красного теста.
- `CFG11` alias among multiple Host patterns outside block.
- `CFG12` modified/conflicting managed block.
- `CFG13` non-empty file without final LF.
- `CFG14` comment containing alias does not false-fail.

Malformed cases rc 1 before mutation, original bytes identical.

### `authorized_keys` contract

- `AK01` absent -> first apply creates exactly one canonical forced line.
- `AK02` unrelated lines with spaces/comments preserved byte-for-byte.
- `AK03` second apply byte-identical.
- `AK04` one canonical quoted forced line passes.
- `AK05` unquoted command variant fails.
- `AK06` same key unrestricted fails.
- `AK07` duplicate exact canonical line fails.
- `AK08` same key in two forms fails.
- `AK09` canonical comment with different key fails.
- `AK10` non-empty no-final-LF fails unchanged.
- `AK11` hostile comment/glob characters do not expand paths and unrelated line bytes remain unchanged.

### Origin contract

- `ORIGIN01` HTTPS expected repo normalizes once.
- `ORIGIN02` old `git@github.com:` form normalizes once.
- `ORIGIN03` already alias form remains exact; no redundant set-url if implementation promises that, otherwise at most one exact set-url.
- `ORIGIN04` wrong owner fails, zero set-url/mutation.
- `ORIGIN05` wrong repo fails.
- `ORIGIN06` credential-bearing HTTPS URL fails without printing credentials.
- `ORIGIN07` unknown scheme/host fails.
- `ORIGIN08` missing origin/get-url nonzero fails.

### API and remote proof

Prepare canonical installed state once per case. Read-only audit must show no chown/mv/set-url/fetch/checkout/push.

- `NET01` preflight API 200 + valid remote -> rc 0, exact PUBLIC and not-production-ready wording.
- `NET02` preflight API 404 + valid remote -> rc 0.
- `NET03` preflight API 403.
- `NET04` preflight API 429.
- `NET05` preflight API 500.
- `NET06` preflight API 503.
- `NET07` invalid status.
- `NET08` curl nonzero/timeout.
- `NET09` ls-remote nonzero.
- `NET10` timeout 124.
- `NET11` empty output.
- `NET12` two output lines.
- `NET13` wrong ref.
- `NET14` spaces вместо TAB.
- `NET15` uppercase SHA.
- `NET16` short SHA.
- `NET17` long SHA.
- `NET18` exact remote line passes.
- `NET19` check API 200 fails.
- `NET20` check API 404 + exact remote passes.
- `NET21` check 403/429/5xx/invalid/curl failure each fails (separate subcases).
- `NET22` expected SHA match passes.
- `NET23` expected SHA mismatch fails.

### Failure injection / recovery

- `FAIL01-03` mktemp failure for known-hosts/config/authorized prefixes.
- `FAIL04` config helper/write failure.
- `FAIL05` authorized helper/write failure.
- `FAIL06` mv known-hosts failure.
- `FAIL07` mv config failure after known-hosts rename.
- `FAIL08` mv authorized_keys failure after earlier renames.
- `FAIL09` origin set-url failure.

Для каждого:

- non-zero;
- no success message;
- no truncated destination: each destination equals complete old or complete expected-new bytes;
- no temp files;
- audit reflects only allowed calls;
- повторный apply без injection приводит к exact canonical installed state.

Не утверждать all-file rollback, если production его не реализует.

## 4. Global output scan

Сканировать объединённые stdout/stderr всех cases. Fail, если встречается:

- `BEGIN ... PRIVATE KEY`/PEM body;
- checkout или Actions base64 token;
- Actions key comment;
- credential-bearing origin fixture;
- API body sentinel;
- malformed remote output sentinel;
- `.env` sentinel.

Fingerprint допустим.

## 5. Этот проход завершить без общего handoff

После реализации выполнить только:

```bash
bash -n scripts/prod-github-access.sh scripts/tests/test-prod-github-access.sh
timeout 240 bash scripts/tests/test-prod-github-access.sh
git diff --check -- scripts/prod-github-access.sh scripts/tests/test-prod-github-access.sh
```

Создать `56_HANDOFF_R13_PHASE_B3_ACCESS_ONLY.md` с:

- exact case IDs/section counts;
- exact command rc;
- перечислением minimal production defects, выявленных красным тестом и исправленных;
- подтверждением no production/real network/commit/push.

После этого остановиться. `51` не редактировать.
