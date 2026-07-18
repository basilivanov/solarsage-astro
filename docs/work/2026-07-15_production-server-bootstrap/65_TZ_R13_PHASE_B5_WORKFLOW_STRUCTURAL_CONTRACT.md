# R13 Phase B5 — structural contract GitHub Actions workflows

## Статус

Текущий `scripts/tests/test-prod-source-readiness-workflow.sh` возвращает `11 passed`, но не принят: sandbox mutations доказали, что он остаётся зелёным при дополнительном trigger `issues:`, удалённом private conditional, неверном concurrency group, отсутствующем executable `permissions: {}`, команде `pnpm build` внутри multiline `run: |` и suffix `&& id` после remote command.

Задача выполняется только после приёмки Phase B4 wrapper. Production/server не запускать. Реальные Actions, SSH, GitHub API, сеть, deploy, commit и push запрещены.

## Scope

Разрешено менять только:

- `scripts/tests/test-prod-source-readiness-workflow.sh`;
- новый test-only `scripts/tests/lib/prod_workflow_validator.py`, если structural parser вынесен отдельно;
- `.github/workflows/deploy-production.yml` — добавить отсутствующий explicit `UserKnownHostsFile=~/.ssh/known_hosts` в SSH command;
- `.github/workflows/source-readiness.yml` — только если structural validator докажет конкретное отклонение от описанного ниже canonical contract.

Не менять secret names/values, production host, workflow triggers, forced-command verbs или application runtime. Не трогать frozen/unrelated paths.

## 1. Архитектура validator

Переписать validator как fail-closed structural extractor исполняемого YAML. Набор глобальных `grep` presence checks не является доказательством.

Допустимы Bash и `python3.12` standard library. Не добавлять PyYAML/yq/actionlint или новую production/test dependency только ради этой проверки. Рекомендуемая реализация — небольшой indentation/state parser, который:

- требует финальный LF;
- читает файл как UTF-8 и запрещает NUL, CR и tab indentation;
- запрещает YAML anchors, aliases, tags, merge keys, inline comments, folded blocks и flow-конструкции кроме exact `{}`;
- игнорирует blank/comment-only lines, но никогда не считает комментарий executable contract;
- распознаёт top-level blocks, jobs, job properties, ordered steps, step mappings и полные multiline `run: |` bodies;
- обнаруживает duplicate keys на одном structural level;
- при незнакомой/неоднозначной структуре завершается non-zero;
- возвращает canonical structural representation либо выполняет assertions непосредственно внутри Python;
- одинаково валидирует canonical files и mutation copies из `$TEST_DIR`.

Полный YAML parser реализовывать не нужно: намеренно поддержать только узкое canonical subset этих двух файлов (`mapping`, `- name:` sequence, `run: |` literal block, exact `{}`). Любая неподдержанная конструкция fail-closed. Key `on` хранить literal string и не преобразовывать по YAML 1.1 в boolean.

Если используется Bash extractor, он обязан иметь те же свойства и mutation proof. Нельзя проверять только строки `run:`/`uses:` без последующего тела блока.

## 2. Exact top-level contract для обоих workflows

Для каждого workflow доказать:

- top-level executable keys ровно `name`, `on`, `concurrency`, `jobs`;
- `on` содержит ровно один child `workflow_dispatch` без других событий; запрещён любой второй trigger, а не только заранее перечисленные `push/pull_request/...`;
- `concurrency` содержит exact group:
  - readiness: `production-source-readiness`;
  - deploy: `production-deploy`;
- `cancel-in-progress` exact boolean `false`;
- `jobs` содержит ровно один job:
  - readiness: `source-readiness`;
  - deploy: `deploy`;
- второй job, reusable call, matrix или executable top-level extension запрещены;
- job fields ровно ожидаемый набор: `runs-on`, `timeout-minutes`, `permissions`, `environment`, `steps`;
- `runs-on: ubuntu-latest`;
- `permissions` — executable empty mapping `{}`, а не слово в комментарии;
- `environment: production`;
- timeout — положительное целое; readiness `<= 10` (canonical `10`), deploy canonical `45`;
- ровно четыре steps в указанном ниже порядке; никаких дополнительных `uses:` или `run:` steps.

## 3. Step 1 — реальный fail-closed gate

Step name: `Verify branch and SHA`.

Exact env mapping:

```text
GITHUB_REF -> ${{ github.ref }}
GITHUB_SHA -> ${{ github.sha }}
IS_PRIVATE -> ${{ github.event.repository.private }}
```

Полное executable `run` body должно структурно доказывать три отдельных guards до любого SSH/config step:

1. `GITHUB_REF` exact `refs/heads/main`, mismatch приводит к `exit 1`;
2. `GITHUB_SHA` exact regex `^[0-9a-f]{40}$`, mismatch приводит к `exit 1`;
3. `IS_PRIVATE` exact string `true`, mismatch приводит к `exit 1`.

Наличие `${{ github.event.repository.private }}` в `env` не считается private gate. Удаление conditional, `exit 0`, `:`, `true`, warning-only или перенос gate после Configure SSH обязаны делать validator красным.

Сообщения `echo` могут изменяться, но нельзя считать их guards. Разрешённые shell statements шага должны быть ограничены guard-логикой и безопасными generic diagnostics; extra command запрещён.

## 4. Step 2 — Configure SSH и secret boundary

Step name: `Configure SSH`.

Exact env mapping содержит только:

```text
PROD_SSH_PRIVATE_KEY -> ${{ secrets.PROD_SSH_PRIVATE_KEY }}
PROD_KNOWN_HOSTS     -> ${{ secrets.PROD_KNOWN_HOSTS }}
```

Исполняемый body должен быть exact allowlist без дополнительных команд:

- `mkdir -p ~/.ssh`;
- `chmod 700 ~/.ssh`;
- создание ephemeral key как regular file mode `600`;
- запись `$PROD_SSH_PRIVATE_KEY` только в `~/.ssh/solarsage_prod_deploy`, с обязательным redirect; raw value не попадает в stdout/stderr;
- запись `$PROD_KNOWN_HOSTS` только в `~/.ssh/known_hosts`, с обязательным redirect;
- known_hosts mode exact `644`;
- никаких `set -x`, `env`, `printenv`, unredirected `echo/cat/printf`, `tee`, artifact upload или второго destination.

Текущая безопасная canonical pipeline `printf ... | tr -d '\r' > file` допустима. Validator должен отличать её от того же `printf` без redirect или с suffix-командой.

## 5. Step 3 — exact SSH invocation

Step names:

- readiness: `Trigger source-check forced-command on production server`;
- deploy: `Trigger deploy forced-command on production server`.

Exact env mapping:

```text
PROD_USER  -> ${{ secrets.PROD_USER }}
PROD_HOST  -> ${{ secrets.PROD_HOST }}
GITHUB_SHA -> ${{ github.sha }}
```

`run` содержит ровно один logical `ssh` command и ничего до/после. Проверить exact argv/option set:

- `ssh`;
- `-T`;
- `-i ~/.ssh/solarsage_prod_deploy`;
- `-o IdentitiesOnly=yes`;
- `-o BatchMode=yes`;
- `-o StrictHostKeyChecking=yes`;
- `-o ConnectTimeout=15`;
- `-o ServerAliveInterval=30`;
- `-o ServerAliveCountMax=3`;
- `-o UserKnownHostsFile=~/.ssh/known_hosts` — обязательно в **обоих** workflows;
- destination exact `"$PROD_USER@$PROD_HOST"`;
- последний и единственный remote-command argument:
  - readiness: `"source-check $GITHUB_SHA"`;
  - deploy: `"deploy $GITHUB_SHA"`.

Substring presence недостаточен. Запрещены `&&`, `;`, pipe, prefix/suffix, вторая command line, дополнительный remote argv или remote shell reconstruction.

Рекомендуемый разбор logical command: склеить только строки с trailing `\`, затем `shlex` из Python stdlib с `punctuation_chars=";&|<>"`; shell operators запрещены. Для `-o` собрать exact map, запретить duplicate/extra options. `ConnectTimeout`, `ServerAliveInterval`, `ServerAliveCountMax` проверить как положительные integers в bounds `<=15`, `<=30`, `<=3` соответственно. Raw form отдельно должна подтверждать двойные кавычки host и remote argument, потому что `shlex` удаляет quoting.

## 6. Step 4 — cleanup

Step name: `Cleanup SSH Key`.

Доказать как единый step contract:

- exact `if: always()`;
- нет secrets/env mapping;
- body содержит только `rm -f ~/.ssh/solarsage_prod_deploy ~/.ssh/known_hosts`;
- оба пути присутствуют ровно один раз;
- нет suffix/prefix command, wildcard, второго destination или вывода содержимого.

Cleanup должен идти после SSH step. Его name/comment вне реального step mapping не является доказательством.

## 7. Exact secret-reference contract

По parsed executable nodes, не по комментариям, global exact set secret references равен:

```text
PROD_HOST
PROD_USER
PROD_SSH_PRIVATE_KEY
PROD_KNOWN_HOSTS
```

Каждый secret разрешён только в описанном step/env key. Missing, extra, dynamic secret expression, дублированный secret в другом step или secret в `run` literal должны падать.

## 8. Mutation/self-test matrix

Все mutations создаются только в `$TEST_DIR` и проходят через тот же `validate_workflow`. Каждая обязана дать non-zero. Использовать стабильные case IDs и manifest с exact equality actual/expected.

Validator должен возвращать стабильный symbolic error code (`E_TRIGGER_SET`, `E_GATE_PRIVATE`, `E_SSH_OPTION_SET`, `E_PARSE_DUPLICATE_KEY` и т.п.) без вывода body/secret values. Mutation case проверяет ожидаемый semantic code; случайная parse error не считается успешным доказательством semantic mutation. Exact replace helper обязан требовать ровно одно совпадение anchor.

Минимум проверить:

1. `push:` trigger;
2. неизвестный второй trigger `issues:`;
3. второй job с `run: id`;
4. wrong concurrency group;
5. `cancel-in-progress: true`;
6. удалить executable `permissions: {}`, оставив такое слово в comment;
7. readiness timeout `11`;
8. удалить real branch conditional;
9. расширить SHA regex до uppercase либо short SHA;
10. удалить real private conditional, оставив env reference;
11. заменить private failure на `exit 0`;
12. перенести gate step после Configure SSH;
13. добавить `secrets.EXTRA_SECRET`;
14. удалить один required secret;
15. удалить private-key redirect;
16. удалить known-hosts redirect;
17. изменить key mode/known_hosts mode;
18. добавить unredirected secret output;
19. удалить `-T`;
20. удалить `-i`;
21. по отдельности удалить каждый `-o`, включая keepalive и `UserKnownHostsFile`;
22. deploy без `UserKnownHostsFile`;
23. remote command внутри quotes `source-check $GITHUB_SHA; id`;
24. suffix после quotes `"source-check $GITHUB_SHA" && id`;
25. вторая command line после ssh;
26. cleanup без `if: always()`;
27. cleanup удаляет только один файл;
28. cleanup имеет suffix command;
29. readiness extra inline `run: pnpm build`;
30. readiness extra multiline `run: |` с `pnpm build`/`systemctl`;
31. extra `uses: actions/checkout@...`;
32. duplicate YAML key на одном structural level;
33. comment decoys для permission/gate/SSH option не должны спасать broken executable contract.

Mutation helper обязан доказать, что mutation реально произошла ровно один раз; zero-match mutation — ошибка harness, а не PASS.

## 9. Harness safety и GRACE

- `TEST_DIR=$(mktemp -d /tmp/solarsage-r13-workflow-test.XXXXXX)`;
- cleanup trap: `EXIT INT TERM HUP`;
- никакого запуска workflow/SSH/network;
- ошибки показывают case ID и безопасную structural reason, но не secret values;
- для новых нетривиальных функций добавить `START_FUNCTION_CONTRACT` по AGENTS.md;
- после каждого mutation удалять/пересоздавать copy; отсутствие temp dirs после exit проверить внешним независимым запуском;
- не менять `51_REVIEW...` и не заявлять independent acceptance.

## 10. Проверка кодером

После реализации:

```bash
bash -n scripts/tests/test-prod-source-readiness-workflow.sh
timeout 120 bash scripts/tests/test-prod-source-readiness-workflow.sh
git diff --check
```

Кодер сообщает изменённые файлы, exact case count/manifest result, rc и подтверждает отсутствие Actions/SSH/network/production/commit/push. Затем останавливается для независимого review архитектора.
