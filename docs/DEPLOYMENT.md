# AI_HEADER
# module: M-DEPLOY-DOCS
# wave: W-DEPLOY
# purpose: Deployment documentation

# Deployment Guide

## Prerequisites

- Docker 20.10+
- Docker Compose 2.0+
- Domain with SSL certificate (production)

## Quick Start

1. **Clone repository**
   ```bash
   git clone https://github.com/your-org/solarsage-astro.git
   cd solarsage-astro
   ```

2. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your values
   ```

3. **Deploy**
   ```bash
   chmod +x scripts/deploy.sh
   ./scripts/deploy.sh
   ```

## Services

- **Frontend**: http://localhost:3000
- **API**: http://localhost:8000
- **SolarSage**: http://localhost:8001
- **Database**: localhost:5432

## Production Deployment

### 1. SSL Certificate

Use Let's Encrypt with Certbot:

```bash
certbot certonly --standalone -d astro.example.com
```

### 2. Update docker-compose.yml

Add Nginx reverse proxy with SSL:

```yaml
nginx:
  image: nginx:alpine
  ports:
    - "80:80"
    - "443:443"
  volumes:
    - ./nginx-prod.conf:/etc/nginx/nginx.conf
    - /etc/letsencrypt:/etc/letsencrypt
```

### 3. Deploy

```bash
./scripts/deploy.sh
```

## Monitoring

- **Logs**: `docker-compose logs -f`
- **Health checks**: 
  - API: `curl http://localhost:8000/api/health`
  - SolarSage: `curl http://localhost:8001/v1/health`

## Backup

```bash
# Database backup
docker-compose exec db pg_dump -U astro astro > backup.sql

# Restore
docker-compose exec -T db psql -U astro astro < backup.sql
```

## Troubleshooting

### API not starting

Check logs:
```bash
docker-compose logs api
```

Common issues:
- Database not ready → wait for health check
- Missing environment variables → check .env
- Migration failed → check alembic logs

### Database connection failed

```bash
docker-compose exec db psql -U astro -d astro
```

## Scaling

### Horizontal scaling (multiple API instances)

```yaml
api:
  deploy:
    replicas: 3
```

### Load balancer

Add Nginx upstream:

```nginx
upstream api_backend {
    server api:8000;
    server api:8000;
    server api:8000;
}
```

## Environment Variables

See `.env.example` for full list. Required variables:

- `DB_PASSWORD` — PostgreSQL password
- `APP_DOMAIN` — Production domain
- `TELEGRAM_BOT_TOKEN` — Telegram bot token
- `OPENAI_API_KEY` — OpenAI API key
- `JWT_SECRET` — JWT signing secret
- `GRACE_USER_SALT` — User ID hashing salt (32+ bytes)

## Security

- Change all default passwords in `.env`
- Use strong `JWT_SECRET` and `GRACE_USER_SALT`
- Enable HTTPS in production
- Restrict database port (5432) to internal network
- Rotate secrets regularly

## Updates

```bash
# Pull latest code
git pull

# Rebuild and restart
./scripts/deploy.sh
```

## Rollback

```bash
# Stop services
docker-compose down

# Checkout previous version
git checkout <previous-commit>

# Deploy
./scripts/deploy.sh
```
