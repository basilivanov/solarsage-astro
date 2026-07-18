# Architecture decision — минимальный production path без собственного deploy-фреймворка

## Статус

Предложение к принятию после review пользователя. Это решение о сокращении scope, а не разрешение на production rollout.

## Решение

Остановить расширение самописного release/promotion фреймворка. Для первого стабильного запуска использовать готовые примитивы:

1. GitHub Actions `workflow_dispatch`/production environment — единственный ручной gate.
2. GitHub Container Registry (или другой явно выбранный OCI registry) — хранение неизменяемых образов, тегированных полным commit SHA и проверяемых digest.
3. Docker Compose v2 на VPS — один app stack с `healthcheck`, `depends_on: condition: service_healthy`, `docker compose config --quiet` и `docker compose up -d --wait`.
4. Nginx на хосте — существующая внешняя точка 80/443, прокси на канонические 8000/3002; PostgreSQL остаётся отдельным каноническим compose-проектом на 5433.
5. Один короткий root-owned orchestrator с командами `deploy <sha>`, `rollback <sha>`, `status`, `preflight`; без собственного symlink/GC/state-machine фреймворка.
6. Ежедневный `pg_dump -Fc` + `pg_restore --list` + checksum и offsite-копия через Restic; restore выполняется отдельной ручной командой в изолированную БД/maintenance window.
7. Секреты остаются вне Git: root-owned env/credential files (`0640`), передаваемые контейнерам как Compose secrets или через systemd credential bridge.

Immutable release в этом варианте — не каталог worktree, а образ, идентифицированный полным SHA/digest. Rollback — повторный `docker compose up -d --wait` с предыдущим SHA/digest. Docker daemon и root-owned orchestrator являются привилегированной границей; отдельная самописная Python authority для pointer/GC больше не нужна в runtime path.

## Почему это подходит текущему репозиторию

В рабочем дереве уже есть Dockerfiles для API, sidecar и web, а на хосте установлен Docker Compose `v2.39.4`. Текущий production runtime уже использует Docker для PostgreSQL. Значит, сокращается именно самописная orchestration-логика, а не вводится новый кластер или новый control plane.

## Обязательные адаптации перед первым запуском

Готовые примитивы не означают, что существующие compose-файлы уже production-ready. Перед rollout нужно закрыть только следующие конкретные несоответствия:

- `docker-compose.prod.yml` сейчас использует неканонические 8002/8003/5434 и не содержит рабочего Next.js frontend; не использовать его как production source of truth.
- `docker-compose.yml` остаётся dev-конфигурацией с 5432/8001/3000; не использовать его для production.
- `apps/web/Dockerfile` сейчас собирает Vite `dist`, тогда как текущий frontend — Next.js; нужен минимальный standalone Next image.
- API image не должен выполнять Alembic автоматически при каждом старте; migration — отдельный явный orchestrator step до смены app images.
- Каждый API/sidecar/frontend health endpoint должен отдавать `release_sha`, полученный из immutable image metadata; проверка сравнивает его с требуемым SHA, а не с текущим контейнером/прокси.
- Production compose должен иметь только канонические host bindings: API 127.0.0.1:8000, frontend 127.0.0.1:3002, sidecar 127.0.0.1:18091; DB остаётся 127.0.0.1:5433.
- Compose env interpolation не должна содержать секреты в YAML или образах; использовать root-owned files/Compose secrets и запретить `down -v` в orchestrator.

Это один миграционный slice, а не повод строить новый набор из десятков тестовых harnesses.

## Сравнение вариантов

| Вариант | Оценка | Причина |
|---|---:|---|
| OCI images + Docker Compose + один orchestrator | **Рекомендуется** | Уже есть Dockerfiles/Compose/Docker; минимальная новая поверхность, понятный ручной rollback и health gate. |
| Kamal 2 | Резерв | Даёт deploy/rollback поверх контейнеров, но добавляет Ruby/Kamal-конфигурацию, registry/proxy conventions и миграцию текущих сервисов. Не сокращает первый slice по сравнению с Compose. |
| Coolify/CapRover | Не рекомендуется | Добавляет постоянно работающую панель/control plane и новую privileged attack surface; ручной gate становится менее прозрачным. |
| Kubernetes/Nomad | Не рекомендуется | Несоразмерно одному VPS и текущему объёму продукта. |
| Продолжать текущий custom release authority | Остановить | Уже пять дней растёт код и exhaustive-тесты, а runnable deploy path ещё не принят. |

## Минимальная Definition of Done

Не требуются 100% mutation/exhaustive-проверок. Для первого запуска достаточно доказать из свежей sandbox/CI среды:

- manual workflow не стартует без явной команды/approval и принимает только `main` + полный SHA;
- `docker compose config --quiet` и image digest/SHA preflight проходят;
- deploy не выполняет build/package-manager на production host;
- отдельный migration step явно подтверждён и не запускается при failed preflight/backup;
- `docker compose up -d --wait` поднимает только канонические сервисы;
- три health endpoint возвращают ровно требуемый SHA и canonical ports доступны через Nginx;
- при health failure orchestrator возвращает предыдущий SHA и повторно проверяет health;
- backup pair + checksum создаются, restore drill в отдельную БД проходит;
- в логах/артефактах нет Telegram/API/DB secrets;
- один ручной `deploy` и один ручной `rollback` имеют понятный runbook и фиксированный exit code.

## Что паркуем

Незакоммиченные изменения R14 authority/promotion, включая текущую незавершённую TZ 171, не стирать и не выдавать за принятый production path. После успешной Compose-репетиции их можно удалить/перенести отдельным осознанным cleanup-коммитом. До этого они не должны расширяться новыми suites, matrix-слоями или состояниями.

## Запрещённые действия

Решение не разрешает установку/запуск в production, применение sudoers/systemd/nginx, миграцию/restore реальной БД, push/commit или изменение внешних сервисов. Сначала нужен source-only orchestrator slice и offline/test-host rehearsal, затем отдельная команда пользователя на rollout.

## Официальные примитивы

- Docker Compose `up --wait`: <https://docs.docker.com/reference/cli/docker/compose/up/>
- GitHub Actions environments/manual approvals: <https://docs.github.com/en/actions/deployment/targeting-different-environments/using-environments-for-deployment>
- systemd credentials: <https://www.freedesktop.org/software/systemd/man/latest/systemd.exec.html>
