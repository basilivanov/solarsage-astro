# Review R5A — forced transport correctness corrections

Дата: 2026-07-15

R4/R5 implementation в целом принята, но перед commit исправить три точечных дефекта. Выполнять вместе с R6, не менять иной scope.

## Разрешённые файлы

```text
infra/production/solarsage-github-deploy
docs/PRODUCTION_RUNBOOK.md
```

Опционально разрешено поправить только неточный комментарий/invariant в `infra/production/solarsage-deploy.sudoers`, если он утверждает отсутствие любого `ALL`: sudoers синтаксис закономерно содержит host selector `astro ALL=(root)`, запрет относится к command wildcard и `NOPASSWD` на все команды. Сам policy contract не менять.

Commit/push/server mutations запрещены.

## 1. Wrapper обязан отвергать positional arguments

Текущий wrapper проверяет `SSH_ORIGINAL_COMMAND`, но локальный вызов:

```bash
infra/production/solarsage-github-deploy unexpected
```

игнорирует argument и запустит реальный deploy. Это нарушает R5 requirement «не принимать arguments» и опасно для тестирования.

До `exec` добавить fail-closed проверку `"$#" -ne 0`. При любом positional argument:

- вывести безопасную понятную ошибку в stderr;
- exit `126`;
- не запускать deploy script.

Не объединять argument с `SSH_ORIGINAL_COMMAND`, не использовать `eval` и не печатать argument value.

Обновить module contract/invariants, если нужно, чтобы они отражали обе проверки.

## 2. Исправить full sudoers validation command

В `docs/PRODUCTION_RUNBOOK.md` заменить ошибочную команду:

```bash
sudo visudo -cf
```

на:

```bash
sudo visudo -cf /etc/sudoers
```

Template validation с exact template path сохранить.

## 3. Убрать ложное срабатывание safety grep

Runbook сейчас буквально содержит старую небезопасную директиву, поэтому обязательная проверка на её отсутствие падает. Переформулировать текст без буквального написания этой sudoers-директивы, например:

```text
remove the temporary unrestricted passwordless bootstrap sudo rule
```

Указать известный bootstrap path `/etc/sudoers.d/90-astro-admin`, но не вставлять его прежнее содержимое.

Смысл сохранить: удалять bootstrap rule и выводить `astro` из группы `sudo` только после подтверждения root-key session; `astro` не должен быть в `docker` group.

## Проверки

```bash
bash -n infra/production/solarsage-github-deploy

set +e
SSH_ORIGINAL_COMMAND='echo forbidden' infra/production/solarsage-github-deploy >/tmp/forced-original.out 2>/tmp/forced-original.err
original_rc=$?
SSH_ORIGINAL_COMMAND='' infra/production/solarsage-github-deploy unexpected >/tmp/forced-arg.out 2>/tmp/forced-arg.err
arg_rc=$?
set -e

test "$original_rc" -eq 126
test "$arg_rc" -eq 126
test ! -s /tmp/forced-original.out
test ! -s /tmp/forced-arg.out
grep -F 'Remote commands are not permitted for this deploy key.' /tmp/forced-original.err
grep -F 'Arguments are not permitted for this deploy key.' /tmp/forced-arg.err

grep -F 'sudo visudo -cf /etc/sudoers' docs/PRODUCTION_RUNBOOK.md
! grep -R 'NOPASSWD:[[:space:]]*ALL' infra/production docs/PRODUCTION_RUNBOOK.md
visudo -cf infra/production/solarsage-deploy.sudoers
git diff --check
```

Важно: ни одна regression-команда не должна вызывать wrapper с одновременно пустым `SSH_ORIGINAL_COMMAND` и нулём arguments — такой вызов запускает настоящий deploy.

Вернуть результаты и остановиться без commit/push/server mutations.
