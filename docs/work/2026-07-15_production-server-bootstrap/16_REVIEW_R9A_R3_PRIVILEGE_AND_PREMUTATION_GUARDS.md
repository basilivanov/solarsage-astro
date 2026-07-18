# Review R9A-R3 — privilege boundary and pre-mutation guards

Дата: 2026-07-15

Исполнитель: кодер в `tmux astro:0.0`, модель `cliproxy/gemini-3-flash-agent`.

Статус: исправить до принятия R9A; commit/push/live apply запрещены.

## Цель

Закрыть найденные архитектором блокирующие края в `prod-host-prepare.sh`, не меняя ручную модель запуска production deploy и не запуская приложение. После исправления root-подготовка должна быть безопасной даже при обычном `astro`-владельце `.env.production`, а любая нехватка repository-owned шаблонов должна быть обнаружена до первой мутации хоста.

## Обязательные исправления

### 1. Не исполнять файл окружения пользователя от root

Сейчас общий env-контракт запускает `source /opt/solarsage-astro/.env.production` в root-owned shell. Файл принадлежит `astro`, поэтому это даёт пользователю `astro` возможность выполнить произвольные команды с root-привилегиями при следующем `sudo prod-host-prepare.sh --check|--apply`.

Измени проверку так, чтобы `.env.production` source/parse выполнялся через `runuser -u astro -- ...` (или эквивалентный непривилегированный процесс), с `env -i`, фиксированным `PATH`, без вывода значений и без импорта application-кода. Root должен получать только успешный/ошибочный статус и безопасный код ошибки. Не ослабляй проверки переменных.

Не делай `chmod`/смену владельца `.env.production` частью этой задачи. Не выводи секреты, строки env-файла, command output или `DATABASE_URL`.

### 2. Полный inventory шаблонов до первой мутации

В common preflight явно проверь, что каждый обязательный repository-owned файл существует как regular file. Отсутствующий файл должен увеличивать aggregate error и не должен быть тихо пропущен из-за конструкции `[ -f ] && check`.

Проверяемый inventory:

```text
infra/nginx/astro.vasiliy-ivanov.ru.conf
infra/production/docker-compose.yml
infra/production/solarsage-deploy.sudoers
infra/production/solarsage-github-deploy
infra/systemd/solarsage-db.service
infra/systemd/solarsage-sidecar.service
infra/systemd/solarsage-api.service
infra/systemd/solarsage-frontend.service
infra/systemd/solarsage-backup.service
infra/systemd/solarsage-backup.timer
scripts/prod-backup.sh
scripts/prod-deploy.sh
scripts/prod-host-prepare.sh
scripts/prod-infra-fingerprint.sh
```

После inventory проверки:

- `bash -n` должен выполняться для всех четырёх shell-скриптов в `scripts/` и для `infra/production/solarsage-github-deploy`;
- `visudo -cf` — только если `visudo` доступен, но отсутствие шаблона всё равно является отдельной preflight error;
- `systemd-analyze verify` — для всех шести unit-файлов, а отсутствие любого unit уже зафиксировано inventory;
- compose config остаётся guarded и не печатает rendered config;
- ни одна из этих проверок не должна запускать install/cp/mv/reload/start.

### 3. Точный rollback sudoers

Перед заменой `/etc/sudoers.d/90-solarsage-deploy` сохрани для существующего regular-файла:

- bytes;
- owner;
- group;
- mode.

При ошибке install или полной `visudo -cf /etc/sudoers` восстанови все четыре свойства. Если файла не было — удали candidate. Если обнаружен неожиданный тип (не regular file и не отсутствующий), не затирай его: завершися с ошибкой до замены либо сохрани/восстанови его тип безопасным способом. Временные root-only backup-файлы удалить и при success, и при failure.

### 4. Дополнительная защита bootstrap-препятствий

- Не сравнивай пустую/невалидную версию Node арифметически; malformed output должен стать понятной aggregate error.
- Убедись, что `mktemp` проверен до его первого вызова либо его отсутствие приводит к безопасному preflight error до мутаций.
- Сохрани exact modes: `0755` для двух scripts, `0644` для `infra/systemd/solarsage-db.service`.
- Не добавляй запуск/перезапуск/остановку `solarsage-api`, `solarsage-sidecar` или `solarsage-frontend`.

## Проверки перед handoff

Обязательно выполнить без live apply, сервера, commit или push:

```bash
bash -n scripts/prod-infra-fingerprint.sh scripts/prod-host-prepare.sh scripts/prod-deploy.sh infra/production/solarsage-github-deploy
systemd-analyze verify infra/systemd/solarsage-db.service infra/systemd/solarsage-api.service infra/systemd/solarsage-sidecar.service infra/systemd/solarsage-frontend.service infra/systemd/solarsage-backup.service infra/systemd/solarsage-backup.timer
visudo -cf infra/production/solarsage-deploy.sudoers
POSTGRES_USER=dummy POSTGRES_PASSWORD=dummy POSTGRES_DB=dummy docker compose -f infra/production/docker-compose.yml config >/dev/null
git diff --check
```

Добавь безопасный локальный harness, доказывающий, что строка-команда в `.env.production` не исполняется root-ом (запускать только в изолированном temp-копировании/сделать проверяемым статически; не менять настоящий `.env.production`). Повтори R8/R9A проверки аргументов, fingerprint и marker. В handoff перечисли фактически изменённые файлы и rc всех проверок.

## Запрещено

- commit/push;
- `git reset`, `git clean`, broad restore/checkout;
- `sudo prod-host-prepare.sh --apply` на любом сервере;
- запуск/перезапуск application services;
- изменение workflows, runtime API/frontend или production secrets в этой волне.
