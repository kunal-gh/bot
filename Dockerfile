# Use official Python runtime as a parent image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies (required for some Python packages)
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Create directories for data and logs
RUN mkdir -p data logs

# Default port for Cloud Run
ENV PORT=8000

# Expose ports (8000 for FastAPI, 8501 for Streamlit)
EXPOSE 8000 8501

# The CMD will be overridden by docker-compose or the deployment platform
# depending on whether we want to run the API or the UI
CMD ["uvicorn", "bot.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
