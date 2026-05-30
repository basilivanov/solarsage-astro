# AI_HEADER
# module: M-DEPLOY-SOLARSAGE
# wave: W-DEPLOY
# purpose: SolarSage Docker image

FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

CMD uvicorn solarsage.main:app --host 0.0.0.0 --port 8001
