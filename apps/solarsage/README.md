# apps/solarsage — sidecar расчётов

FastAPI HTTP-сервис для астрологических расчётов на Swiss Ephemeris.
Слушает `127.0.0.1:18091` (только loopback).

## Структура

```
solarsage/
  app.py              # FastAPI application
  core/
    config.py         # Settings (ephemeris_path, port, etc)
    health.py         # Health check logic
  api/
    health.py         # /v1/health endpoint
  schemas/
    health.py         # Pydantic schemas
tests/
  test_health.py      # Health endpoint tests
```

## Установка

```bash
# Создать venv
python3 -m venv venv
source venv/bin/activate

# Установить зависимости
pip install -e ".[dev]"
```

## Запуск

```bash
# Development (с auto-reload)
uvicorn solarsage.app:app --host 127.0.0.1 --port 18091 --reload

# Production
uvicorn solarsage.app:app --host 127.0.0.1 --port 18091
```

## Конфигурация

Environment variables (префикс: `SOLARSAGE_`):

- `SOLARSAGE_EPHEMERIS_PATH` — путь к Swiss Ephemeris data (default: `/opt/sweph/ephe`)
- `SOLARSAGE_GIT_SHA` — Git commit SHA для версионирования (default: `dev`)
- `SOLARSAGE_CALCULATION_VERSION` — версия расчётов (default: `ss-1.0.0`)

## Endpoints

### GET /v1/health

Health check endpoint.

**Response (200 OK):**
```json
{
  "ok": true,
  "version": "dev",
  "ephemeris_path": "/opt/sweph/ephe",
  "calculation_version": "ss-1.0.0"
}
```

**Response (503 Service Unavailable):**
```json
{
  "detail": "Ephemeris path not found: /opt/sweph/ephe"
}
```

## Тестирование

```bash
pytest tests/ -v
```

## Systemd Service

```bash
# Скопировать service file
sudo cp /opt/solarsage-astro/infra/systemd/solarsage.service /etc/systemd/system/

# Включить и запустить
sudo systemctl daemon-reload
sudo systemctl enable solarsage
sudo systemctl start solarsage

# Проверить статус
sudo systemctl status solarsage
```

## Справочные файлы

- `collect_solarsage_western_deep.py` — reference collector для deep-натала
  (используется как образец payload для оркестратора)
- `sample_params.json` — пример входных данных
