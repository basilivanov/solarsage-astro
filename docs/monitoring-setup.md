# Production Monitoring Setup - W-2.7

## Overview

Production monitoring system for SolarSage Astro with health checks, metrics, and alerting capabilities.

## Components

### 1. Backend Monitoring Endpoints

#### `/api/health` - Basic Health Check
Returns basic API status and version information.

**Response:**
```json
{
  "status": "ok",
  "version": "0.1.0",
  "git_sha": "1a51c64"
}
```

#### `/api/health/extended` - Extended Health Check
Checks all critical dependencies and services.

**Response:**
```json
{
  "status": "healthy",
  "checks": {
    "api": "ok",
    "database": "ok",
    "llm": "ok",
    "geonames": "not configured"
  }
}
```

**Status Values:**
- `healthy` - All critical services operational
- `degraded` - Some services have issues

**Check Values:**
- `ok` - Service is operational
- `not configured` - Optional service not configured (acceptable)
- `error: <message>` - Service has an error

#### `/api/metrics` - Production Metrics
Returns user growth and onboarding metrics.

**Response:**
```json
{
  "timestamp": "2026-05-31T08:48:19.754328Z",
  "users": {
    "total": 1,
    "new_24h": 1,
    "new_7d": 1
  },
  "onboarding": {
    "completed": 1,
    "completed_24h": 1,
    "completed_7d": 1,
    "rate": 100.0
  }
}
```

### 2. Monitoring Scripts

#### `scripts/health-check.sh`
Comprehensive health check script that tests all endpoints.

**Usage:**
```bash
/opt/solarsage-astro/scripts/health-check.sh
```

**Exit Codes:**
- `0` - All systems operational
- `1` - Some systems degraded

#### `scripts/health-check-with-alert.sh`
Health check with Telegram alerting support.

**Setup:**
```bash
export TELEGRAM_BOT_TOKEN="your_bot_token"
export TELEGRAM_CHAT_ID="your_chat_id"
/opt/solarsage-astro/scripts/health-check-with-alert.sh
```

#### `scripts/alert.sh`
Send alerts to Telegram.

**Usage:**
```bash
export TELEGRAM_BOT_TOKEN="your_bot_token"
export TELEGRAM_CHAT_ID="your_chat_id"
/opt/solarsage-astro/scripts/alert.sh "Your message"
```

#### `scripts/dashboard.sh`
Real-time monitoring dashboard (updates every 5 seconds).

**Usage:**
```bash
/opt/solarsage-astro/scripts/dashboard.sh
```

### 3. Frontend Logger

#### `lib/logger.ts`
Structured logging for frontend with automatic backend aggregation.

**Usage:**
```typescript
import { Logger } from '@/lib/logger'

// Log an event
Logger.log('user_action', { action: 'click', button: 'submit' })

// Log an error
Logger.error('api_error', error, { endpoint: '/api/profile' })

// Log a warning
Logger.warn('validation_warning', { field: 'email' })
```

**Features:**
- Structured JSON logging
- Automatic backend aggregation in production
- Console logging in development
- Fire-and-forget (doesn't break user experience)

### 4. Backend Structured Logging

Already configured in `apps/api/app/core/logging.py` (W-1.6).

**Features:**
- JSON envelope format
- ISO 8601 timestamps
- Correlation ID support
- Module/function/line tracking

## Setup Instructions

### 1. Verify Endpoints

```bash
# Test basic health
curl https://dev.astro.vasiliy-ivanov.ru/api/health

# Test extended health
curl https://dev.astro.vasiliy-ivanov.ru/api/health/extended

# Test metrics
curl https://dev.astro.vasiliy-ivanov.ru/api/metrics
```

### 2. Setup Cron Job (Optional)

Run health checks every 5 minutes:

```bash
# Add to crontab
(crontab -l 2>/dev/null; echo "*/5 * * * * /opt/solarsage-astro/scripts/health-check.sh >> /var/log/solarsage-health.log 2>&1") | crontab -

# Verify
crontab -l | grep health-check
```

### 3. Setup Alerting (Optional)

Configure Telegram alerts:

```bash
# Add to .env or environment
export TELEGRAM_BOT_TOKEN="your_bot_token"
export TELEGRAM_CHAT_ID="your_chat_id"

# Test alert
/opt/solarsage-astro/scripts/alert.sh "Test alert"

# Use health check with alerts
/opt/solarsage-astro/scripts/health-check-with-alert.sh
```

### 4. Run Dashboard

```bash
# Start real-time dashboard
/opt/solarsage-astro/scripts/dashboard.sh
```

## Monitoring Best Practices

### Critical Services
- **API** - Must be `ok`
- **Database** - Must be `ok`

### Optional Services
- **LLM** - Can be `not configured` or `ok`
- **GeoNames** - Can be `not configured` or `ok`

### Metrics to Watch
- **User Growth** - `users.new_24h`, `users.new_7d`
- **Onboarding Rate** - `onboarding.rate` (should be > 80%)
- **Onboarding Velocity** - `onboarding.completed_24h`

## Troubleshooting

### Health Check Fails

1. Check API logs:
```bash
tail -100 /tmp/api-monitoring.log
```

2. Check nginx logs:
```bash
sudo tail -100 /var/log/nginx/error.log
```

3. Verify API is running:
```bash
ps aux | grep uvicorn
```

### Metrics Endpoint Returns 500

1. Check database connection
2. Verify models are properly imported
3. Check API logs for stack traces

### Dashboard Not Updating

1. Verify API is accessible
2. Check network connectivity
3. Verify jq is installed: `sudo apt install jq`

## Files Created

### Backend
- `/opt/solarsage-astro/apps/api/app/api/metrics.py` - Metrics endpoint
- `/opt/solarsage-astro/apps/api/app/api/health_extended.py` - Extended health check
- `/opt/solarsage-astro/apps/api/app/main.py` - Updated with new routers

### Frontend
- `/opt/solarsage-astro/lib/logger.ts` - Frontend logger

### Scripts
- `/opt/solarsage-astro/scripts/health-check.sh` - Health check script
- `/opt/solarsage-astro/scripts/health-check-with-alert.sh` - Health check with alerts
- `/opt/solarsage-astro/scripts/alert.sh` - Alert script
- `/opt/solarsage-astro/scripts/dashboard.sh` - Monitoring dashboard

## Next Steps

1. **Setup Cron Jobs** - Automate health checks
2. **Configure Alerts** - Setup Telegram notifications
3. **Monitor Metrics** - Track user growth and onboarding
4. **Setup Log Aggregation** - Consider ELK stack or similar for production
5. **Add More Metrics** - Track API response times, error rates, etc.

## GRACE Compliance

- **W-1.6** - Structured logging already implemented
- **W-2.7** - Production monitoring setup complete
- All endpoints follow GRACE module contracts
- Async SQLAlchemy patterns used throughout
- No blocking operations in health checks
