FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies (same as backend)
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r ./backend/requirements.txt

# Copy required app components
COPY backend/ ./backend
COPY workers/ ./workers
COPY ingestion/ ./ingestion
COPY ai_agents/ ./ai_agents
COPY vector_store/ ./vector_store
COPY shared/ ./shared

# Add app directories to path
ENV PYTHONPATH=/app

CMD ["celery", "-A", "workers.celery_app", "worker", "--loglevel=info"]
