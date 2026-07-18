# R8 — pinned manual deploy and source-tree hardening

Дата: 2026-07-15

Исполнитель: кодер в `tmux astro:0.0`.

Роль архитектора: постановка, review и live rollout. Кодер не подключается к production и не получает credentials.

## 1. Цель

Сделать production deployment строго ручным, воспроизводимым и привязанным к exact commit SHA выбранного `main`.

После этой волны:

- deployment запускается только вручную через `workflow_dispatch` либо прямой ручной запуск deploy script;
- простое/пустое SSH-подключение Actions-key ничего не запускает;
- GitHub workflow передаёт exact `GITHUB_SHA`;
- forced-command wrapper принимает только `deploy <40 lowercase hex>`;
- server deploy отказывается работать, если `origin/main` уже указывает на другой SHA;
- non-ignored untracked source запрещён до и после build;
- LLM provider key и ephemeris directory проверяются до backup/migration/restart;
- workflow и HTTP readiness checks имеют bounded timeouts.

Эта волна не устанавливает host infrastructure. Это будет отдельный R9.

## 2. Разрешённые файлы

Изменять только:

```text
scripts/prod-deploy.sh
infra/production/solarsage-github-deploy
.github/workflows/deploy-production.yml
docs/PRODUCTION_RUNBOOK.md
```

Task doc уже создан архитектором. Другие файлы, включая существующие R3–R7 changes, не менять и не откатывать.

Commit, push, server access, server mutations и настоящий deploy запрещены.

## 3. Deploy script: exact аргументы

Файл: `scripts/prod-deploy.sh`.

Поддержать ровно три формы запуска:

```bash
scripts/prod-deploy.sh
scripts/prod-deploy.sh --current
scripts/prod-deploy.sh --expected-sha <40 lowercase hexadecimal characters>
```

Семантика:

1. Без аргументов: routine manual deploy текущего `origin/main`; `MODE=git`, expected SHA отсутствует.
2. `--current`: bootstrap текущего clean worktree/HEAD; fetch/checkout не делать.
3. `--expected-sha <sha>`: `MODE=git`; после fetch exact `origin/main` обязан совпасть с `<sha>`.

Любая другая форма, uppercase SHA, сокращённый SHA, лишний аргумент или смешение modes -> usage в stderr и exit `2`.

Не использовать external regex tools для валидации SHA; Bash `[[ ... =~ ... ]]` допустим. Не печатать env/secrets.

## 4. Clean source contract

Вынести маленький helper с `START_FUNCTION_CONTRACT`, который fail-closed проверяет одновременно:

- unstaged tracked diff;
- staged diff;
- non-ignored untracked paths через `git ls-files --others --exclude-standard`.

Ignored paths (`.env.production`, `.next-prod`, `.venv`, `venv`, `node_modules` и прочее из ignore rules) не должны ломать gate.

Helper должен:

- вернуть 0 только для clean source tree;
- при failure вывести короткую ошибку и только status/path list, без diff contents;
- не удалять, не восстанавливать и не изменять файлы;
- не использовать `git clean`, `git reset`, broad checkout/restore или wildcard.

Применить helper:

1. в `--current` до фиксации `TARGET_SHA`;
2. в git mode до `git fetch`;
3. в git mode ещё раз после fetch и до checkout;
4. после разрешённого byte-exact cleanup `next-env.d.ts`.

Текущую единственную разрешённую restore-команду сохранить exact:

```bash
git restore --source=HEAD --worktree -- next-env.d.ts
```

### Expected SHA order

Git mode должен идти так:

1. clean-source check;
2. `git fetch --prune origin main`;
3. повторный clean-source check;
4. `TARGET_SHA=$(git rev-parse origin/main)`;
5. если expected SHA задан и `TARGET_SHA != EXPECTED_SHA`, завершиться non-zero на stage `git-checkout`, не делать checkout/build;
6. detached checkout exact `TARGET_SHA`.

Лог mismatch может печатать expected/actual commit SHA, потому что это не secret.

## 5. Production preflight additions

### 5.1 Ephemeris directory

До dependency/build/migration mutation, после load env, проверить:

```text
${SOLARSAGE_EPHEMERIS_PATH:-/opt/sweph/ephe}
```

Directory обязан существовать и быть traversable/readable текущим пользователем. Не требовать наличия `.se1` files: текущий runtime допускает встроенный Moshier fallback, а health contract требует существование пути.

При failure завершиться до backup/migrations/restarts. Не создавать directory в deploy script — это обязанность будущего host prepare R9.

### 5.2 LLM provider/key

В существующем Python production preflight после `build_runtime_security_policy` добавить fail-closed contract:

- `settings.llm_provider == "openrouter"` -> `settings.openrouter_api_key` non-empty;
- `settings.llm_provider == "anthropic"` -> `settings.anthropic_api_key` non-empty;
- любой другой provider -> explicit failure.

Ошибка не должна содержать key value. В runbook добавить имена `OPENROUTER_API_KEY` и `ANTHROPIC_API_KEY` как provider-specific, взаимоисключающие по активному provider.

## 6. Bounded local health checks

Во всех трёх restart loops (`sidecar`, `api`, `frontend`) добавить curl:

```text
--connect-timeout 2 --max-time 5
```

Body не печатать. Сохранить 30 attempts и 1-second sleep. Не ослаблять public HTTPS smoke R3.

## 7. Forced-command wrapper contract

Файл: `infra/production/solarsage-github-deploy`.

Wrapper больше не должен запускать deploy при пустом `SSH_ORIGINAL_COMMAND`.

Runtime rules:

1. Любые positional arguments (`$# != 0`) -> stderr, exit `126`.
2. `SSH_ORIGINAL_COMMAND` должен exact соответствовать:

```text
deploy <40 lowercase hexadecimal characters>
```

3. При exact match извлечь SHA без `eval`, shell re-execution и word-splitting входной команды и выполнить только:

```bash
exec /bin/bash /opt/solarsage-astro/scripts/prod-deploy.sh --expected-sha "$sha"
```

4. Пустая, malformed, uppercase, extra-token или любая другая remote command -> безопасная generic ошибка в stderr и exit `126`.

Не печатать rejected command. Не использовать `eval`, `bash -c "$SSH_ORIGINAL_COMMAND"`, `sudo`, `su`, network calls или env-overridable executable path.

Обновить module contract/map/invariants фактическим поведением.

## 8. Manual GitHub workflow

Файл: `.github/workflows/deploy-production.yml`.

Сохранить единственный trigger:

```yaml
on:
  workflow_dispatch:
```

Никаких `push`, `pull_request`, schedule или workflow_run.

Изменения:

- job `deploy` имеет `timeout-minutes: 45`;
- permissions exact empty: `permissions: {}` — checkout/content token workflow не использует;
- environment остаётся `production`;
- до SSH fail-closed проверить `GITHUB_REF == refs/heads/main`; другой ref -> exit 1;
- secrets передавать в shell через step-level `env`, а не вставлять expressions прямо в shell source;
- configure step использует env names `PROD_SSH_PRIVATE_KEY`, `PROD_KNOWN_HOSTS`;
- SSH step использует `PROD_USER`, `PROD_HOST` и отправляет единственную remote command:

```text
deploy ${GITHUB_SHA}
```

В shell это должно быть quoted безопасно. `GITHUB_SHA` должен пройти локальную exact lowercase-40 check до ssh.

Сохранить:

- strict pinned known_hosts;
- `IdentitiesOnly`, `BatchMode`, `StrictHostKeyChecking=yes`;
- connect/keepalive options;
- always cleanup private key/known_hosts;
- concurrency `cancel-in-progress: false`.

## 9. Runbook

Обновить `docs/PRODUCTION_RUNBOOK.md`:

- deployment остаётся manual-only;
- normal production launch — выбрать branch `main` в Actions и вручную запустить `Deploy Production`;
- workflow передаёт exact selected `GITHUB_SHA`, server сверяет его с fetched `origin/main`;
- пустое SSH connection теперь безопасно отвергается и не запускает deploy;
- safe transport test: empty connection или `echo forbidden` ожидаемо получают `126`; ни один не должен запускать deploy;
- direct operator fallback: `scripts/prod-deploy.sh --expected-sha <full-main-sha>` либо no-arg latest main;
- non-ignored untracked source запрещён;
- cache policy: Today/Calendar cache versioned by calculation/scoring/content/canon identity, поэтому deploy не делает blanket delete; Alembic `upgrade head` остаётся автоматическим, schema-affecting cache transformations принадлежат migrations;
- provider-specific LLM key names.

Не вставлять реальные keys, host secrets или credentials.

## 10. Обязательные regression checks

### Syntax/static

```bash
bash -n scripts/prod-deploy.sh
bash -n infra/production/solarsage-github-deploy
python3 - <<'PY'
from pathlib import Path
import yaml
yaml.safe_load(Path('.github/workflows/deploy-production.yml').read_text())
PY
git diff --check
```

Static assertions:

```bash
grep -F -- '--expected-sha' scripts/prod-deploy.sh
grep -F 'git ls-files --others --exclude-standard' scripts/prod-deploy.sh
grep -F 'timeout-minutes: 45' .github/workflows/deploy-production.yml
grep -F 'permissions: {}' .github/workflows/deploy-production.yml
grep -F 'workflow_dispatch:' .github/workflows/deploy-production.yml
! grep -E '^[[:space:]]+(push|pull_request|schedule|workflow_run):' .github/workflows/deploy-production.yml
! grep -E 'eval|bash -c.*SSH_ORIGINAL_COMMAND' infra/production/solarsage-github-deploy
```

### Deploy argument parser

Без запуска полного script доказать parser scenarios через безопасный extracted function/harness либо controlled prefix extraction:

1. no args -> accepted git mode;
2. `--current` -> accepted current mode;
3. `--expected-sha` + 40 lowercase hex -> accepted and exact value retained;
4. short SHA -> exit 2;
5. uppercase SHA -> exit 2;
6. missing SHA -> exit 2;
7. extra arg -> exit 2.

Не читать `.env.production`, не доходить до lock/fetch/deploy.

### Clean-source gate

В temporary git repo доказать:

1. clean tracked + ignored untracked -> pass;
2. unstaged tracked -> fail, content preserved;
3. staged tracked -> fail, content/index preserved;
4. non-ignored untracked -> fail, file preserved;
5. after adding matching ignore rule same untracked path -> pass.

### Wrapper

Без настоящего deploy доказать в temporary copy/harness:

1. positional arg -> 126;
2. empty `SSH_ORIGINAL_COMMAND` -> 126;
3. `echo forbidden` -> 126;
4. `deploy short` -> 126;
5. `deploy <UPPERCASE40>` -> 126;
6. `deploy <lowercase40> extra` -> 126;
7. exact `deploy <lowercase40>` reaches only expected exec argv `prod-deploy.sh --expected-sha <same sha>`.

Для valid scenario запрещено вызывать repository wrapper напрямую, потому что это запустит deploy. Использовать temporary copy с exact заменой final exec на inert argv recorder; проверять, что остальная parsing logic не менялась.

### Existing R7 regressions

Повторить пять byte-exact `next-env.d.ts` cleanup scenarios и обе invalid wrapper safety regressions в их обновлённой семантике.

### Existing production gates

```bash
python3 scripts/check_logging_guardrails.py
bash scripts/check_prod_guard.sh
systemd-analyze verify infra/systemd/solarsage-api.service infra/systemd/solarsage-sidecar.service infra/systemd/solarsage-frontend.service infra/systemd/solarsage-backup.service infra/systemd/solarsage-backup.timer
visudo -cf infra/production/solarsage-deploy.sudoers
```

## 11. Handoff

Вернуть:

- exact список изменённых файлов;
- краткое описание поведения;
- результаты всех parser/clean/wrapper/R7 scenarios;
- syntax/YAML/guardrails/systemd/visudo/diff checks;
- подтверждение, что workflow trigger manual-only;
- подтверждение отсутствия commit/push/server access/server mutations/real deploy.

После handoff остановиться.
