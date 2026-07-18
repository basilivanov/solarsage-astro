# Review R5 — make the GitHub forced-command transport reproducible

Дата: 2026-07-15

## Контекст

Production GitHub environment и SSH transport уже настроены на сервере. Живой сервер использует:

- отдельный Actions SSH key;
- `authorized_keys` option `restrict`;
- forced command `/usr/local/sbin/solarsage-github-deploy`;
- root-owned wrapper;
- sudoers allowlist только для restart трёх SolarSage services;
- отсутствие `NOPASSWD: ALL` и отсутствие пользователя `astro` в группе `sudo`.

Workflow `.github/workflows/deploy-production.yml` зависит от этого контракта, но wrapper и sudoers allowlist пока существуют только на живом сервере. Чистый bootstrap нельзя оставлять зависимым от ручного воспроизведения по памяти.

## Разрешённые файлы

Создать:

```text
infra/production/solarsage-github-deploy
infra/production/solarsage-deploy.sudoers
```

Изменить:

```text
docs/PRODUCTION_RUNBOOK.md
```

Другие файлы не менять. Commit/push/server mutations запрещены. Секреты, private/public key material и реальные credentials не добавлять.

## 1. Root-owned forced-command wrapper

Создать executable-файл `infra/production/solarsage-github-deploy`.

Требования:

- shebang `#!/bin/bash`;
- `set -euo pipefail`;
- GRACE `AI_HEADER`, module contract и module map, адаптированные к bash;
- если `SSH_ORIGINAL_COMMAND` непустой, вывести безопасную ошибку в stderr и завершиться с кодом `126`;
- при пустом `SSH_ORIGINAL_COMMAND` выполнить только:

```bash
exec /bin/bash /opt/solarsage-astro/scripts/prod-deploy.sh
```

- не принимать arguments;
- не использовать `eval`, shell interpolation входной команды, `sudo`, `su`, network calls или секреты;
- Git file mode должен быть executable (`100755`).

Wrapper устанавливается как `/usr/local/sbin/solarsage-github-deploy`, owner `root:root`, mode `0755`. GitHub Actions подключается без remote command, а OpenSSH запускает wrapper через forced-command option.

## 2. Минимальный sudoers allowlist

Создать `infra/production/solarsage-deploy.sudoers` с комментариями и ровно таким capability contract:

```sudoers
Cmnd_Alias SOLARSAGE_DEPLOY_RESTART = /usr/bin/systemctl restart solarsage-sidecar.service, /usr/bin/systemctl restart solarsage-api.service, /usr/bin/systemctl restart solarsage-frontend.service
astro ALL=(root) NOPASSWD: SOLARSAGE_DEPLOY_RESTART
```

Требования:

- никаких wildcard;
- никаких `ALL` в command allowlist;
- никакого `NOPASSWD: ALL`;
- не разрешать start/stop/enable/disable/edit/cat, shell, Docker, package manager, nginx, certbot или произвольный `systemctl`;
- не добавлять `SETENV`;
- файл должен проходить `visudo -cf`.

## 3. Дополнить production runbook

В `docs/PRODUCTION_RUNBOOK.md` добавить отдельный раздел установки deploy transport. Он должен быть пошаговым и не содержать реальных ключей.

Обязательно описать:

1. Сначала проверить root SSH key в отдельной сессии; не снимать bootstrap sudo до этой проверки.
2. Установить wrapper:

```bash
sudo install -o root -g root -m 0755 \
  /opt/solarsage-astro/infra/production/solarsage-github-deploy \
  /usr/local/sbin/solarsage-github-deploy
```

3. До установки проверить sudoers template и затем установить его mode `0440` в `/etc/sudoers.d/90-solarsage-deploy`; после установки проверить полный `/etc/sudoers` через `visudo -cf`.
4. Удалить временный bootstrap-файл с `NOPASSWD: ALL` и убрать `astro` из группы `sudo` только после подтверждения root-key доступа. Указать, что `astro` не должен состоять в группе `docker`.
5. Добавить Actions public key в `/home/astro/.ssh/authorized_keys` в форме:

```text
restrict,command="/usr/local/sbin/solarsage-github-deploy" ssh-ed25519 <ACTIONS_PUBLIC_KEY> solarsage-github-actions-prod
```

Указать permissions `~/.ssh=0700`, `authorized_keys=0600`, owner `astro:astro`.

6. Для server-to-GitHub checkout использовать другой read-only deploy key и pinned GitHub `known_hosts`; не переиспользовать Actions-to-server key и не давать checkout key write access.
7. GitHub environment `production` использует только secret names `PROD_HOST`, `PROD_USER`, `PROD_SSH_PRIVATE_KEY`, `PROD_KNOWN_HOSTS`, а deployment branch policy разрешает только `main`.
8. Безопасная transport-проверка должна отправлять непустую remote command и ожидать отказ `126`; пустое SSH-подключение запускает настоящий deploy и не должно использоваться как безобидный connectivity test.

Не писать пример с `StrictHostKeyChecking=no` и не вставлять настоящее содержимое ключей.

## Проверки

Из корня:

```bash
bash -n infra/production/solarsage-github-deploy
visudo -cf infra/production/solarsage-deploy.sudoers
set +e
SSH_ORIGINAL_COMMAND='echo forbidden' infra/production/solarsage-github-deploy >/tmp/forced-command.out 2>/tmp/forced-command.err
rc=$?
set -e
test "$rc" -eq 126
test ! -s /tmp/forced-command.out
grep -F 'Remote commands are not permitted for this deploy key.' /tmp/forced-command.err
test "$(git ls-files -s infra/production/solarsage-github-deploy | awk '{print $1}')" = "100755"
! grep -R 'NOPASSWD:[[:space:]]*ALL' infra/production docs/PRODUCTION_RUNBOOK.md
git diff --check
git status --short
```

Проверить, что tracked scope R5 содержит только два новых infra-файла и runbook. Учитывать, что в worktree уже могут присутствовать принятые R3/R4 изменения — не откатывать и не переписывать их.

## Handoff

Вернуть:

- exact список созданных/изменённых R5 файлов;
- результаты проверок;
- подтверждение executable mode wrapper;
- подтверждение отсутствия commit/push/server mutations и key material.

После handoff остановиться.
