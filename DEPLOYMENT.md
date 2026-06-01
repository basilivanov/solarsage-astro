# SolarSage Astro Deployment Guide

## Production Mode (Current)

Production mode используется для Telegram Web App — без HMR, стабильный и быстрый.

### Статус

```bash
sudo systemctl status solarsage-frontend
```

### Логи

```bash
sudo journalctl -u solarsage-frontend -f
```

### Перезапуск

```bash
sudo systemctl restart solarsage-frontend
```

### Остановка

```bash
sudo systemctl stop solarsage-frontend
```

## Development Mode (для локальной разработки)

### Запуск dev server

```bash
# Остановить production
sudo systemctl stop solarsage-frontend

# Запустить dev
cd /opt/solarsage-astro
npm run dev
```

### Вернуться в production

```bash
# Остановить dev (Ctrl+C или)
pkill -f "next dev"

# Пересобрать (если были изменения)
cd /opt/solarsage-astro
npm run build

# Запустить production
sudo systemctl start solarsage-frontend
```

## Nginx Configuration

**Файл:** `/etc/nginx/sites-enabled/astro.conf`

Production mode не требует WebSocket HMR блока.

### Проверка конфигурации

```bash
sudo nginx -t
```

### Перезагрузка Nginx

```bash
sudo systemctl reload nginx
```

## Troubleshooting

### WebSocket HMR ошибки

Если видишь ошибки `upstream sent no valid HTTP/1.0 header` в `/var/log/nginx/error.log`:

1. Убедись, что используется production mode (не dev)
2. Проверь, что в Nginx нет блока `location /_next/webpack-hmr`
3. Перезагрузи Nginx: `sudo systemctl reload nginx`

### Production server не запускается

```bash
# Проверить логи
sudo journalctl -u solarsage-frontend -n 50

# Проверить, что порт 3002 свободен
sudo lsof -i :3002

# Убить процессы на порту 3002
sudo kill -9 $(sudo lsof -t -i:3002)

# Перезапустить
sudo systemctl restart solarsage-frontend
```

### Build ошибки

```bash
cd /opt/solarsage-astro
npm run build 2>&1 | tee /tmp/build.log
```

## Systemd Service

**Файл:** `/etc/systemd/system/solarsage-frontend.service`

```ini
[Unit]
Description=SolarSage Astro Frontend (Production)
After=network.target

[Service]
Type=simple
User=astro
WorkingDirectory=/opt/solarsage-astro
Environment="NODE_ENV=production"
Environment="PORT=3002"
ExecStart=/usr/bin/npm run start
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

### Обновление service

```bash
sudo systemctl daemon-reload
sudo systemctl restart solarsage-frontend
```

## URLs

- **Production:** https://dev.astro.vasiliy-ivanov.ru/
- **API:** https://dev.astro.vasiliy-ivanov.ru/api/
- **Local:** http://localhost:3002/

## Architecture

```
Telegram Web App
    ↓
Nginx (443) → dev.astro.vasiliy-ivanov.ru
    ↓
    ├─ /api/ → FastAPI (8000)
    └─ / → Next.js Production (3002)
```

## Performance

Production mode:
- ✅ Нет WebSocket HMR
- ✅ Оптимизированный bundle
- ✅ Static generation где возможно
- ✅ Быстрый старт (~168ms)
- ✅ Автоматический перезапуск при падении

Dev mode:
- ⚠️ HMR WebSocket (не работает через Nginx)
- ⚠️ Медленнее
- ⚠️ Больше памяти
- ✅ Hot reload для разработки
