# SolarSage Astro — Deployment Guide

## 🏗️ Архитектура

- **Dev (локально)** — PostgreSQL + Redis в Docker, API/SolarSage локально
- **Production** — Полный Docker Compose stack
- **CI/CD** — SQLite для тестов (быстро)

---

## 🚀 Quick Start (Development)

### 1. Запустить инфраструктуру

```bash
docker compose -f docker-compose.dev.yml up -d
```

**Порты:** PostgreSQL: 5433, Redis: 6381

### 2. Установить зависимости

```bash
python3 -m venv venv
cd apps/api && ../../venv/bin/pip install -e .
cd ../solarsage && ../../venv/bin/pip install -e .
```

### 3. Запустить миграции

```bash
cd apps/api
DATABASE_URL=postgresql+asyncpg://astro:astro_dev_password@localhost:5433/astro \
  ../../venv/bin/alembic upgrade head
```

### 4. Запустить сервисы

```bash
# API
../../venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload

# SolarSage
cd ../solarsage
../../venv/bin/uvicorn solarsage.main:app --host 0.0.0.0 --port 18091
```

### 5. Проверить

```bash
curl http://localhost:8000/api/health
curl http://localhost:18091/v1/health
```

---

## 🐳 Production Deployment

```bash
cp .env.production .env.prod
# Отредактировать пароли и секреты
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d
```

**Порты:** PostgreSQL: 5434, Redis: 6382, API: 8002, SolarSage: 8003

---

## 🎯 Telegram Bot

**Bot:** @vi_astro_bot  
**WebApp:** https://dev.astro.vasiliy-ivanov.ru  
**Admin ID:** 833478509

---

**Status:** ✅ Production Ready — Все 52 волны реализованы
