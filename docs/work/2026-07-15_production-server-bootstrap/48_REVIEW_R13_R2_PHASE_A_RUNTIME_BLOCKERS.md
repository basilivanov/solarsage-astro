# R13 review R2 — Phase A runtime blockers

Статус: **Phase A не принята**. Текущий diff сохранить. Production, GitHub visibility, ключи, systemd app units, commit и push не трогать.

Перед исправлениями полностью перечитать `45_TZ_R13_PRIVATE_GITHUB_TRANSPORT_AND_SOURCE_READINESS.md` и `47_REVIEW_R13_R1_TESTABILITY_AND_RUNTIME_SAFETY.md`. В этом раунде исправить только перечисленные ниже production/runtime блокеры и снова остановиться до переписывания test harnesses.

## 1. `scripts/prod-deploy.sh`: реальный top-level runtime crash

На текущей строке около 246 осталось:

```bash
local current_origin
```

Это находится вне функции и при git deploy даст `local: can only be used in a function`. Удалить `local` либо вынести git resolution в функцию. После исправления статически доказать, что все `local` в `prod-deploy.sh` находятся только внутри функций/subshell-functions.

Одновременно:

- `.env.production` проверять как existing regular non-symlink file; текущий `[ -f ]` принимает symlink;
- `scripts/lib/prod-env-loader.sh` проверять как existing regular non-symlink file до `source`;
- exact origin проверять до любого `fetch`, не исправлять origin внутри deploy;
- сохранить `--current` без source-readiness network call;
- не возвращать старый `set -a` self-check или direct source/eval `.env.production`.

## 2. CLI contract: invalid arguments должны давать rc 2

Независимый факт:

```text
prod-github-access.sh --check --expected-sha <uppercase-40-hex> -> rc 1
```

По R13 любой invalid argument/combination обязан вернуть rc 2 до privilege/filesystem checks. Сделать отдельный `usage_error`/`die_usage` с rc 2 и использовать для:

- invalid/missing SHA;
- duplicate actions;
- `--expected-sha` без `--check`;
- unknown option;
- отсутствующего action;
- лишних positional args.

Runtime/readiness/security failures остаются rc 1.

## 3. HTTP status handling сейчас допускает ложный preflight

Текущий `preflight_action` использует arithmetic `-ne` с результатом `curl ... || true`. При timeout/ошибке `curl` status может быть пустым; `[ "" -ne 200 ]` возвращает diagnostic/rc 2 внутри conditional и способен не вызвать `err`. Кроме того repo visibility 403/5xx сейчас только предупреждается, после чего SSH success может дать общий rc 0.

Исправить одной безопасной helper-функцией:

1. Запускать bounded `curl` с body в `/dev/null`, capture rc отдельно.
2. При curl rc != 0 — fail с безопасным сообщением без body/URL credentials.
3. Принимать только status regex `^[0-9]{3}$`.
4. `--preflight`:
   - root API reachability: ожидаемый доступный status (200; допустимый rate-limit status только если это явно обосновано и visibility check всё равно fail-closed);
   - repo API 200 → явный PUBLIC warning, preflight может продолжить;
   - repo API 404 → non-public/not-found indication, затем SSH proof;
   - 403/429/5xx/000/прочие → fail, не warning-green.
5. `--check`: только 404 + exact successful SSH proof; 200 public fail; всё остальное fail.

Не использовать arithmetic comparison над непроверенной/пустой строкой.

## 4. `ls-remote` обязан проверять всю строку, не только SHA

Сейчас код принимает первый field SHA и не проверяет второй field. Требуется ровно одна строка exact shape:

```text
<40 lowercase hex><TAB>refs/heads/main
```

Проверить count без `echo`, который превращает empty string в одну пустую строку. Использовать NUL-safe/temp/readarray либо точный Bash regex над непустой строкой. Reject:

- empty output;
- multiple lines;
- correct SHA + другой ref;
- extra fields/whitespace;
- uppercase/short SHA;
- timeout/nonzero.

Одинаковая helper-функция должна использоваться в `--preflight` и `--check`.

## 5. Exact one-line key contract

`grep -c '[^[:space:]]'` принимает файл с одной key line и дополнительными blank lines. Это не «ровно одна строка».

Для checkout `.pub` и Actions `.pub` требовать exact one physical LF-terminated line без CR, blank prefix/suffix или дополнительных строк. Затем:

- нормализовать только type+base64 для derived-key comparison;
- Actions type только `ssh-ed25519`;
- ключ валиден по `ssh-keygen -lf`;
- не печатать key text.

## 6. Byte-exact preservation config/authorized_keys

Python writer сейчас добавляет newline к последней unrelated line, если исходный файл не имел final newline. Это меняет unrelated bytes и нарушает контракт.

Выбрать один fail-closed вариант:

- если non-empty existing config/authorized_keys не заканчивается LF, отказать до mutation; либо
- построить output так, чтобы unrelated byte regions были неизменны, добавляя разделитель без изменения существующего byte region (при этом файл должен оставаться валидным).

Предпочтительно: prevalidation reject malformed no-final-LF, затем binary replacement. Использовать `python3.12`, который является канонической зависимостью host bootstrap, а не незафиксированный `python3`. Добавить `python3.12` и `timeout` в dependency/required-command inventory, если их ещё нет в конкретном contract.

## 7. `prod-host-prepare --apply` сейчас создаёт циклическую зависимость

Текущая последовательность:

1. `prod-host-prepare --apply` устанавливает forced wrapper.
2. Его финальный `verify_host_state 1 --preflight` требует `/home/astro/.ssh/known_hosts.github`.
3. Но `known_hosts.github` устанавливает отдельный `prod-github-access --apply`.
4. `prod-github-access --apply` до host-prepare невозможен, потому что требует уже установленный root-owned forced wrapper.

Устранить цикл явно:

- `prod-host-prepare --apply` должен успешно завершаться и записывать fingerprint до GitHub-access apply, проверяя repository template и wrapper, но не требуя live user GitHub files;
- отдельный `prod-github-access --apply` затем устанавливает/валидирует live known_hosts/config/authorized_keys/origin;
- `prod-host-prepare --check` в полной readiness-проверке может требовать live GitHub files только если documented sequence уже предполагает выполненный GitHub access apply. Лучше вынести source transport readiness исключительно в `prod-github-access --preflight/--check`, чтобы host-prep не смешивал operator-owned SSH state с OS/systemd transaction;
- runbook должен дать нециклический exact порядок: host prepare → operator key inputs → GitHub access apply → preflight → private transition → source readiness.

Не устанавливать checkout private key или Actions public key из host-prepare.

## 8. Atomic failure semantics

Все три temp-файла готовятся до rename — это хорошо, но последовательные `mv` могут оставить частично обновлённое состояние. Для этого раунда минимум:

- prevalidate все semantic conflicts до первого rename;
- cleanup temps на любой signal/error;
- если второй/третий rename fail, вернуть nonzero и не заявлять success;
- тест Phase B обязан инъецировать write/rename failure и фиксировать фактическую гарантию. Если требование «все originals unchanged» сохраняется, использовать существующий transactional helper/backup+rollback, а не заявлять multi-file atomicity без реализации.

В module contract не писать более сильную гарантию, чем реально реализована.

## 9. Повторная Phase A acceptance

После исправлений кодер должен выполнить только безопасные проверки:

```bash
bash -n scripts/prod-github-access.sh \
  scripts/prod-deploy.sh \
  infra/production/solarsage-github-deploy \
  scripts/prod-host-prepare.sh \
  scripts/prod-infra-fingerprint.sh
scripts/prod-github-access.sh --invalid  # ожидается rc 2
scripts/prod-github-access.sh --check --expected-sha ABCDEF0123456789012345678901234567890123  # ожидается rc 2
scripts/prod-infra-fingerprint.sh
git diff --check
```

Не запускать apply/preflight/check с реальной сетью и не запускать production deploy. Не менять tests в этом раунде. Остановиться с перечнем исправленных line-level blockers и exact exit codes.
