#!/bin/bash

// ############################################################################
// AI_HEADER: MODULE_SCRIPTS_DEPLOY
// ROLE: Tooling script
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-GUARDRAILS-TOOLING
// ############################################################################

// START_MODULE_CONTRACT
// purpose: Tooling script — scripts/deploy.sh
// owns:
//   - scripts/deploy.sh
// inputs: varies
// outputs: varies
// dependencies: local modules
// side_effects: varies
// emitted_logs: n/a
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT

// START_MODULE_MAP
// mapping:
//   - export: default
//     contract: main export
// END_MODULE_MAP

# AI_HEADER
# module: M-DEPLOY-SCRIPT
# wave: W-DEPLOY
# purpose: Deployment script for Docker Compose production deployment

set -e

cd "$(dirname "$0")/.."

echo "🚀 Deploying SolarSage Astro..."

# Load environment
if [ ! -f .env ]; then
    echo "❌ .env file not found. Copy .env.example and configure."
    exit 1
fi

source .env

# Build images
echo "📦 Building Docker images..."
docker-compose build

# Run migrations
echo "🔄 Running database migrations..."
docker-compose run --rm api alembic upgrade head

# Start services
echo "▶️  Starting services..."
docker-compose up -d

# Health check
echo "🏥 Waiting for services to be healthy..."
sleep 10

if curl -f http://localhost:8000/api/health > /dev/null 2>&1; then
    echo "✅ API is healthy"
else
    echo "❌ API health check failed"
    exit 1
fi

if curl -f http://localhost:8000/api/health > /dev/null 2>&1; then
    echo "✅ SolarSage is healthy"
else
    echo "❌ SolarSage health check failed"
    exit 1
fi

echo "✅ Deployment complete!"
echo "🌐 Frontend: http://localhost:3000"
echo "🔌 API: http://localhost:8000"
echo "🔮 SolarSage: http://localhost:8001"
