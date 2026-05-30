# AI_HEADER
# module: M-DEPLOY-API
# wave: W-DEPLOY
# purpose: API Docker image

FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Run migrations on startup
CMD alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000
