# ТЗ: Подключение GRACE Orchestrator к solarsage-astro

**Версия:** 1.0  
**Дата:** 2026-06-06  
**Статус:** draft

---

## 1. Цель

Подключить GRACE Orchestrator (далее «оркестратор») — FastAPI-сервис управления пакетами разработки — к репозиторию solarsage-astro, чтобы задачи на хорар, натальный лендинг, чекин и будущие фичи можно было диспетчеризировать через контрольную плоскость: создавать пакеты → назначать воркера → запускать `opencode run` → верифицировать → принимать в main.

## 2. Контекст

### 2.1. GRACE Orchestrator

| Свойство | Значение |
|---|---|
| Репозиторий | `github.com/basilivanov/grace-orchestrator` |
| Текущая установка | `pip install -e /tmp/grace-orchestrator-export` (из временного worktree) |
| Язык | Python 3.12, FastAPI, SQLAlchemy, SQLite |
| API-порт | 8042 |
| Исполнители | `opencode run` (cli backend), mock |
| Жизненный цикл пакетов | DRAFT → READY → RUNNING → ACCEPTED → MERGED |

Оркестратор предоставляет:
- REST API для создания фич, волн, пакетов
- Worker loop: claim → execute → release
- Acceptance pipeline: T0 (scope guard) → T1 (unit tests) → T2 (e2e) → Evidence Verifier → Reviewer Gate
- Git worktree-изоляцию: каждый attempt получает свой worktree
- SQLite-базу для состояния

### 2.2. solarsage-astro

| Свойство | Значение |
|---|---|
| Репозиторий | `github.com/basilivanov/solarsage-astro` |
| Стек | Next.js 14 App Router + FastAPI (apps/api/) |
| БД | SQLite (astro_dev.db), алиасы через aiosqlite |
| Пакетный менеджер | pnpm |
| Контракты | Pydantic → `pnpm contracts:generate` → Zod/TS |
| Тесты | `pnpm test`, `pnpm lint` |
| Git | основная ветка `main` |

### 2.3. Текущее состояние интеграции

В solarsage-astro есть `grace/orchestrator/` — **лёгкий адаптер без БД и без API**:
- `core.py` — парсит `development-plan.xml` в список Wave-объектов
- `validator.py` — проверяет markdown-секции в пакетах
- `cli.py` — click-команда `status`/`next`/`complete`/`validate`

Этот адаптер **не связан** с контрольной плоскостью оркестратора. Он работает локально, хранит состояние только в памяти. Пакеты в `grace/packets/` — markdown-файлы, не записи в БД.

**Цель ТЗ** — дать оркестратору полный доступ к solarsage-astro как к целевому репозиторию, чтобы он мог создавать worktree, запускать агентов, верифицировать изменения и мержить в main.

---

## 3. Архитектура подключения

```
┌─────────────────────────────────────────────────────┐
│                  GRACE Control Plane                 │
│              (FastAPI :8042, SQLite)                 │
│                                                      │
│  ┌──────────┐  ┌──────────┐  ┌────────────────────┐  │
│  │  API      │  │  Worker   │  │ Acceptance Pipeline│  │
│  │  routers  │  │  loop    │  │ T0→T1→T2→EV→RG    │  │
│  └────┬─────┘  └────┬─────┘  └────────┬───────────┘  │
│       │              │                  │             │
└───────┼──────────────┼──────────────────┼─────────────┘
        │              │                  │
        │    ┌─────────▼─────────┐        │
        │    │  UniversalCli      │        │
        │    │  AgentBackend      │        │
        │    │  (opencode run)    │        │
        │    └─────────┬─────────┘        │
        │              │                  │
        │    ┌─────────▼──────────────────▼──────┐
        │    │     git worktree                    │
        │    │     .grace/worktrees/               │
        │    │         pkt-xxx-attempt-0001/        │
        │    │         ├── apps/api/                │
        │    │         ├── components/               │
        │    │         └── ...                       │
        │    └────────────────┬────────────────────┘
        │                     │
        │    ┌────────────────▼────────────────────┐
        │    │     solarsage-astro (main branch)    │
        │    │     /opt/solarsage-astro              │
        │    └──────────────────────────────────────┘
        │
   ┌────▼─────────────────────────────────┐
   │  .grace/config.yaml                   │   ← конфиг оркестратора
   │  .grace/state/                        │   ← runtime state
   │  .grace/worktrees/                    │   ← git worktrees
   │  grace/orchestrator/project.yml       │   ← роли, профили
   │  grace/packets/                       │   ← markdown-пакеты (справка)
   └───────────────────────────────────────┘
```

Оркестратор работает как **sidecar-процесс** рядом с solarsage-astro — он не встраивается в FastAPI-приложение соларсаджа, а управляет им через git и subprocess.

---

## 4. Требования

### 4.1. Функциональные требования

| ID | Требование | Приоритет |
|----|-----------|-----------|
| F-1 | Оркестратор запускается как отдельный процесс (uvicorn :8042) и управляет solarsage-astro через git worktree | P0 |
| F-2 | Worker оркестратора подключается к API, забирает пакеты из очереди, запускает `opencode run` в worktree | P0 |
| F-3 | Acceptance pipeline проверяет изменения: scope guard, линтер, тесты | P0 |
| F-4 | Принятые пакеты мержатся в `main` через git merge | P0 |
| F-5 | Конфигурация оркестратора через `.grace/config.yaml` в корне solarsage-astro | P0 |
| F-6 | Agent profiles адаптированы под стек solarsage (pnpm, Next.js, FastAPI) | P0 |
| F-7 | Verification profiles адаптированы: `pnpm lint`, `pnpm test`, `pnpm contracts:generate` | P0 |
| F-8 | Фичи и пакеты для хорара, натал-лендинга и чекина регистрируются через API оркестратора | P1 |
| F-9 | (Опционально) solarsage FastAPI отдаёт GRACE status через `/api/grace/status` | P2 |

### 4.2. Нефункциональные требования

| ID | Требование |
|----|-----------|
| NF-1 | Оркестратор не трогает БД соларсаджа (astro_dev.db) — у него своя SQLite (grace.db) |
| NF-2 | Worktree-изоляция: каждый attempt работает в отдельной директории, не в рабочем дереве разработчика |
| NF-3 | Оркестратор не зависит от состояния соларсадж-сервера (может работать даже когда Next.js/FastAPI не запущены) |
| NF-4 | Откат: неудачные attempt'ы удаляют worktree и ветку, не оставляя мусора |
| NF-5 | Логирование: StructuredLogger оркестратора пишет в stdout, логируем packet_id/worker_id/trace_id |

---

## 5. Пошаговый план подключения

### Этап 1: Установка и конфигурация (30 мин)

#### 1.1. Стабильная установка grace-orchestrator

Текущая установка из временного worktree — нестабильна. Установить из GitHub:

```bash
pip install git+https://github.com/basilivanov/grace-orchestrator.git
```

Или локально из стабильного клона:

```bash
cd /tmp
git clone https://github.com/basilivanov/grace-orchestrator.git
cd grace-orchestrator
pip install -e .
```

**Критерий приёмки:** `python -c "from grace_control.config.settings import settings; print(settings.api_port)"` → `8042`

#### 1.2. Создать `.grace/config.yaml` в корне solarsage-astro

```yaml
project:
  name: solarsage-astro
  key: solarsage

api:
  host: 127.0.0.1
  port: 8042

database:
  url: sqlite:///./grace.db

git:
  remote: origin
  base_branch: main
  target_branch: main

execution:
  backend: cli
  state_root: .grace/state
  worktree_root: .grace/worktrees
  timeout_seconds: 900

safety:
  sandbox_mode: danger-full-access
```

#### 1.3. Добавить `.grace/` и `grace.db` в `.gitignore`

```
.grace/state/
.grace/worktrees/
grace.db
```

**Примечание:** `.grace/config.yaml` — **коммитится** в репо (это конфиг проекта). Не коммитятся `state/`, `worktrees/` и `grace.db`.

#### 1.4. Обновить `grace/orchestrator/project.yml`

Текущий `project.yml` частично корректен. Обновить:

```yaml
version: 1
project_id: solarsage-astro
repo_root: .
default_branch: main
packet_dir: grace/packets
roles_dir: grace/orchestrator/roles
packet_schema: grace/orchestrator/packet.schema.json
verification_profiles: grace/orchestrator/verification_profiles.yml
runtime_state_dir: .grace/state
artifact_dir: artifacts/grace
worktree_dir: .grace/worktrees
workflow_runtime: local
agent_executor: opencode-cli
agent_command_default: opencode
agent_model_default: deepseek/deepseek-v4-flash
agent_sandbox_default: danger-full-access
agent_approval_default: bypass
packet_policy: strict_new_warn_legacy
allowed_scope_guard: required
verification_evidence: required
reviewer_verdict: required
```

Ключевые изменения:
- `workflow_runtime: local` (вместо `prefect` — не используем Prefect, worker — встроенный asyncio loop)
- `agent_executor: opencode-cli` (вместо `codex-cli`)
- `agent_command_default: opencode`
- `agent_model_default: deepseek/deepseek-v4-flash`

#### 1.5. Адаптировать agent profiles

Создать файл `grace/orchestrator/agent_profiles.yaml` (путь указывается через `GRACE_AGENT_PROFILES_PATH`):

```yaml
version: 2
default_provider: openai

codex:
  binary: opencode
  workdir: /opt/solarsage-astro
  executors:
    - executor_id: coder-flash
      kind: opencode
      command: opencode
      model: deepseek/deepseek-v4-flash
      roles:
        - coder
      priority: 100
      reasoning: medium
      metadata:
        complexity: simple
        provider: deepseek

    - executor_id: coder-sonnet
      kind: opencode
      command: opencode
      model: cliproxy/claude-sonnet-4-6
      roles:
        - coder
      priority: 90
      reasoning: max
      metadata:
        complexity: medium
        provider: anthropic

    - executor_id: architect-premium
      kind: opencode
      command: opencode
      model: deepseek/deepseek-v4-pro
      roles:
        - architect
        - reviewer
      priority: 10
      reasoning: max
      metadata:
        complexity: complex
        provider: deepseek

agents:
  coder_opencode:
    backend: cli
    command:
      - opencode
      - run
      - "--model"
      - "{model}"
      - "--effort"
      - "{effort}"
    model: "deepseek/deepseek-v4-flash"
    effort: "high"
    cwd: "{worktree_path}"
    timeout_seconds: 900
    env:
      OPENAI_API_KEY: "${OPENAI_API_KEY}"
      OPENAI_BASE_URL: "${OPENAI_BASE_URL:-https://openrouter.ai/api/v1}"
    input:
      mode: stdin
      template: "{packet_markdown}"
    output:
      collect_stdout: true
      collect_stderr: true
      artifacts:
        - "."

  architect_opencode:
    backend: cli
    command:
      - opencode
      - run
      - "--model"
      - "{model}"
    model: "deepseek/deepseek-v4-pro"
    effort: "max"
    cwd: "{worktree_path}"
    timeout_seconds: 1200
    input:
      mode: stdin
      template: "{packet_markdown}"
    output:
      collect_stdout: true
      collect_stderr: true
      artifacts:
        - "."
```

#### 1.6. Адаптировать verification profiles

Обновить `grace/orchestrator/verification_profiles.yml`:

```yaml
version: 1

profile.docs: pnpm guardrails:docs
profile.secrets: pnpm guardrails:secrets
profile.orchestrator: pnpm guardrails:orchestrator
profile.contracts: pnpm contracts:generate
profile.backend: cd apps/api && python -m pytest tests/ -q --tb=short
profile.backend_grace: pnpm guardrails:backend-grace
profile.frontend: pnpm test -- --passWithNoTests
profile.vercel: pnpm build
profile.full: pnpm lint && pnpm contracts:generate && pnpm test -- --passWithNoTests
profile.strict: pnpm lint && pnpm contracts:generate && cd apps/api && python -m pytest tests/ -q --tb=short

default.packet: profile.full
default.spec_only: profile.docs
default.frontend_packet: profile.frontend
default.backend_packet: profile.backend
default.canon_sync_packet: profile.strict
```

### Этап 2: Запуск контрольной плоскости (10 мин)

#### 2.1. Запустить API-сервер

```bash
cd /opt/solarsage-astro

GRACE_TARGET_REPO_ROOT=/opt/solarsage-astro \
GRACE_AGENT_PROFILES_PATH=/opt/solarsage-astro/grace/orchestrator/agent_profiles.yaml \
python -m grace_control.api.main
```

**Критерий приёмки:** `curl http://127.0.0.1:8042/api/health` → `{"status": "ok"}`

#### 2.2. Запустить Worker

В отдельном терминале:

```bash
cd /opt/solarsage-astro

GRACE_TARGET_REPO_ROOT=/opt/solarsage-astro \
GRACE_API_URL=http://127.0.0.1:8042 \
python -m grace_control.worker.worker
```

**Критерий приёмки:** В логах worker'а: `worker_registered`, `worker_id=worker-...`

#### 2.3. Проверить связку

```bash
# Создать тестовую фичу
curl -X POST http://127.0.0.1:8042/api/features \
  -H "Content-Type: application/json" \
  -d '{"slug": "test-integration", "title": "Integration Test", "description": "Verify GRACE <-> solarsage connection"}'

# Проверить
curl http://127.0.0.1:8042/api/features
```

### Этап 3: Smoke-тест полного цикла (30 мин)

#### 3.1. Создать тестовый пакет через API

```bash
# Зная feature_id из предыдущего шага, создаем волну и пакет
curl -X POST http://127.0.0.1:8042/api/architect/plan \
  -H "Content-Type: application/json" \
  -d '{
    "feature_slug": "test-integration",
    "description": "Add a /api/grace/health endpoint to solarsage FastAPI",
    "waves": [
      {
        "slug": "w-integration-smoke",
        "title": "GRACE integration smoke test",
        "packets": [
          {
            "slug": "pkt-smoke-health-endpoint",
            "title": "Add /api/grace/health endpoint",
            "spec": {
              "allowed_write_scope": ["apps/api/app/api/", "apps/api/app/main.py"],
              "frozen_scope": ["apps/api/app/schemas/", "apps/api/app/db/"],
              "verification": ["profile.backend"],
              "acceptance_profile": "FAST"
            }
          }
        ]
      }
    ]
  }'
```

#### 3.2. Перевести пакет в READY

```bash
curl -X POST http://127.0.0.1:8042/api/packets/{packet_id}/ready
```

#### 3.3. Worker автоматически заберёт пакет

Worker в цикле опрашивает `POST /api/packets/claim`. Когда найдёт READY-пакет, он:
1. Создаст git worktree
2. Сгенерирует `EXECUTION_PACKET.md` из spec_json
3. Запустит `opencode run --model deepseek/deepseek-v4-flash` с packet markdown через stdin
4. Дождётся выполнения
5. Запустит acceptance pipeline (T0: scope guard)
6. Отправит результат через `POST /api/packets/{packet_id}/release`

#### 3.4. Проверить результат

```bash
# Статус пакета
curl http://127.0.0.1:8042/api/packets/{packet_id}

# События
curl http://127.0.0.1:8042/api/events?entity_id={packet_id}
```

**Критерий приёмки:** Пакет перешёл в `ACCEPTED` или `REJECTED` с понятной причиной. В solarsage-astro появился коммит с новым endpoint'ом (если ACCEPTED).

### Этап 4: Регистрация реальных фич (15 мин)

После успешного smoke-теста регистрируем три фичи:

```bash
# 1. Horary Questions
curl -X POST http://127.0.0.1:8042/api/features \
  -H "Content-Type: application/json" \
  -d '{
    "slug": "horary-questions",
    "title": "Horary Questions",
    "description": "Хорарные вопросы: AstroCalculator → scoring → verdict_card/timing блоки → оплата через квоту"
  }'

# 2. Natal Landing & Generation
curl -X POST http://127.0.0.1:8042/api/features \
  -H "Content-Type: application/json" \
  -d '{
    "slug": "natal-landing",
    "title": "Natal Landing & Generation",
    "description": "Натальная карта: бесплатный preview из scoring pipeline, полный отчёт за 999₽, персонализированный лендинг"
  }'

# 3. Evening Check-in v2
curl -X POST http://127.0.0.1:8042/api/features \
  -H "Content-Type: application/json" \
  -d '{
    "slug": "evening-checkin-v2",
    "title": "Evening Check-in v2",
    "description": "Чекин: mood 1-5, accuracy (miss/partial/hit), streak, yesterdayEcho, контекстный пуш, Telegram inline"
  }'
```

Далее — создать волны и пакеты для каждой фичи, соответсвующие TZ из `docs/16_`, `docs/17_`, `docs/13_`.

### Этап 5: (Опционально) Интеграция статуса в solarsage API (P2)

Добавить в `apps/api/app/api/` роутер `grace.py`:

```python
# apps/api/app/api/grace.py
from fastapi import APIRouter
import httpx

router = APIRouter(prefix="/api/grace", tags=["grace"])

GRACE_URL = "http://127.0.0.1:8042"

@router.get("/status")
async def grace_status():
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{GRACE_URL}/api/health")
        return resp.json()

@router.get("/features")
async def grace_features():
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{GRACE_URL}/api/features")
        return resp.json()

@router.get("/packets")
async def grace_packets():
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{GRACE_URL}/api/packets")
        return resp.json()
```

---

## 6. Структура файлов после подключения

```
/opt/solarsage-astro/
├── .grace/
│   ├── config.yaml          ← НОВЫЙ: конфиг оркестратора (коммитится)
│   ├── state/                ← НОВЫЙ: runtime state (gitignore)
│   └── worktrees/            ← НОВЫЙ: git worktrees (gitignore)
├── grace/
│   ├── packets/              ← СУЩЕСТВУЕТ: markdown-пакеты (справка)
│   ├── canon/                ← СУЩЕСТВУЕТ: YAML-канон
│   ├── orchestrator/
│   │   ├── project.yml       ← ОБНОВЛЁН: agent_executor, model
│   │   ├── agent_profiles.yaml ← НОВЫЙ: профили агентов для solarsage
│   │   ├── verification_profiles.yml ← ОБНОВЛЁН: pnpm-команды
│   │   ├── packet.schema.json
│   │   ├── roles/
│   │   │   ├── coder.md
│   │   │   ├── architect.md
│   │   │   ├── planner.md
│   │   │   ├── reviewer.md
│   │   │   ├── verifier.md
│   │   │   └── orchestrator.md
│   │   ├── core.py           ← СУЩЕСТВУЕТ: лёгкий адаптер (не удаляем)
│   │   ├── validator.py      ← СУЩЕСТВУЕТ: markdown-валидатор (не удаляем)
│   │   └── cli.py            ← СУЩЕСТВУЕТ: click CLI (не удаляем)
│   └── ...
├── apps/api/                 ← СУЩЕСТВУЕТ: FastAPI соларсаджа
│   └── app/
│       ├── main.py           ← (P2) добавить grace-роутер
│       └── api/
│           └── grace.py      ← НОВЫЙ (P2): прокси к GRACE API
└── grace.db                  ← НОВЫЙ: SQLite БД оркестратора (gitignore)
```

---

## 7. Переменные окружения

| Переменная | Значение по умолчанию | Описание |
|---|---|---|
| `GRACE_TARGET_REPO_ROOT` | `/opt/solarsage-astro` | Путь к целевому репозиторию |
| `GRACE_STATE_ROOT` | `.grace/state` | Директория runtime-состояния |
| `GRACE_WORKTREE_ROOT` | `.grace/worktrees` | Директория git worktrees |
| `GRACE_API_PORT` | `8042` | API-порт оркестратора |
| `GRACE_DATABASE_URL` | `sqlite:///./grace.db` | SQLite БД оркесратора |
| `GRACE_EXECUTION_BACKEND` | `cli` | Backend: `cli` \| `api` \| `mock` |
| `GRACE_AGENT_PROFILES_PATH` | `<встроенный>` | Путь к agent_profiles.yaml |
| `OPENAI_API_KEY` | — | Ключ для LLM (через OpenRouter) |
| `OPENAI_BASE_URL` | `https://openrouter.ai/api/v1` | Базовый URL для LLM |

---

## 8. Риски и митигации

| Риск | Вероятность | Влияние | Митигация |
|---|---|---|---|
| `opencode run` не работает в неинтерактивном режиме (stdin) | Средняя | Блокировка | Протестировать `echo "task" \| opencode run --model ...` до интеграции |
| Git worktree конфликтует с незакоммиченными изменениями в основном дереве | Средняя | Блокировка | Коммитить или стешать изменения перед запуском worker'а |
| Acceptance pipeline отклоняет валидные изменения из-за падающих тестов | Высокая | Ложные rejection'ы | Начать с `acceptance_profile: FAST`, добавить T1/T2 после стабилизации |
| `pnpm lint` или `pnpm test` падают на текущем main | Средняя | Блокировка | Исправить перед подключением |
| Worker зависает на длинных задачах | Низкая | Таймаут | `timeout_seconds: 900` (15 мин) + heartbeat |
| `/tmp/grace-orchestrator-export/` удалён при перезагрузке | Средняя | Потеря установки | Установить из GitHub (этап 1.1) |

---

## 9. Критерии приёмки

### Обязательные (P0)

- [ ] GRACE API запускается и отвечает на `/api/health`
- [ ] Worker подключается к API, регистрируется, забирает пакеты
- [ ] Тестовый пакет (smoke test) проходит полный цикл: DRAFT → READY → RUNNING → ACCEPTED/REJECTED
- [ ] В результате ACCEPTED-пакета в `main` появляется коммит
- [ ] В результате REJECTED-пакета worktree и ветка удаляются
- [ ] `.grace/config.yaml` закоммичен в репозиторий

### Желательные (P1)

- [ ] Фичи horary-questions, natal-landing, evening-checkin-v2 зарегистрированы в GRACE
- [ ] Пакеты для каждой фичи созданы через API
- [ ] Worker успешно выполняет хотя бы один реальный пакет (например, добавление horary-схемы)

### Опциональные (P2)

- [ ] solarsage FastAPI отдаёт GRACE status через `/api/grace/status`
- [ ] Prefect/Docker Compose для автоматического перезапуска API + Worker

---

## 10. Что НЕ входит в это ТЗ

- Реализация конкретных фич (хорар, натал, чекин) — это отдельные ТЗ
- Настройка CI/CD для GRACE (автоматический запуск worker'а)
- Модификация соларсадж-сервера для приёма задач от GRACE (API соларсаджа не меняется)
- Удаление существующего лёгкого адаптера `grace/orchestrator/` — он остаётся для локальной валидации пакетов

---

## 11. Команды для быстрого старта

```bash
# 1. Установить оркестратор (из GitHub)
pip install git+https://github.com/basilivanov/grace-orchestrator.git

# 2. Перейти в репозиторий
cd /opt/solarsage-astro

# 3. Создать .grace/config.yaml (шаг 1.2)
# Создать .gitignore записи (шаг 1.3)

# 4. Запустить API
GRACE_TARGET_REPO_ROOT=/opt/solarsage-astro \
GRACE_AGENT_PROFILES_PATH=$(pwd)/grace/orchestrator/agent_profiles.yaml \
python -m grace_control.api.main

# 5. В другом терминале: запустить Worker
GRACE_TARGET_REPO_ROOT=/opt/solarsage-astro \
GRACE_API_URL=http://127.0.0.1:8042 \
python -m grace_control.worker.worker

# 6. Проверить
curl http://127.0.0.1:8042/api/health
```