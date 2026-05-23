# ─── Stage 1: Build virtual environment ───────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /app

# Install system build tools required for compiled dependencies (DuckDB, scikit-learn, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create a virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ─── Stage 2: Runtime ──────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

WORKDIR /app

# Copy the virtual environment from the builder
COPY --from=builder /opt/venv /opt/venv

# Copy application code
COPY bot/ ./bot/
COPY data/ ./data/

# Create required dirs
RUN mkdir -p logs

# Ensure the virtual environment is used
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONPATH=/app

# Start the server using shell form to guarantee $PORT expansion
CMD uvicorn bot.api.main:app --host 0.0.0.0 --port $PORT
