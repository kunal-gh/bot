# ─── Stage 1: Python deps (cached layer) ───────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /app

# Install system build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first (layer-cached)
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# ─── Stage 2: Runtime ──────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /root/.local /root/.local

# Copy application code
COPY bot/ ./bot/
COPY data/ ./data/

# Create required dirs
RUN mkdir -p logs

# Make sure scripts in .local are usable
ENV PATH=/root/.local/bin:$PATH
ENV PYTHONPATH=/app

# Railway sets PORT dynamically
ENV PORT=8000

EXPOSE $PORT
# Railway's external healthcheck will monitor the container


CMD uvicorn bot.api.main:app --host 0.0.0.0 --port $PORT
