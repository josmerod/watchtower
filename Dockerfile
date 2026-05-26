# Multi-stage build for Watchtower
FROM python:3.11-slim as base

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install UV package manager
RUN pip install uv

# Set working directory
WORKDIR /app

# Copy project files
COPY pyproject.toml uv.lock README.md ./
COPY run_watchtower_dashboard.py ./
COPY run_all_etl.sh ./
COPY deployment/ ./deployment/
COPY src/ ./src/
COPY secrets/ ./secrets/

# Install dependencies
RUN uv sync --frozen --no-dev

# Production stage
FROM python:3.11-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    bash \
    curl \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from base stage
COPY --from=base /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=base /usr/local/bin/uv /usr/local/bin/uv
COPY --from=base /app/.venv /app/.venv

# Set working directory
WORKDIR /app

# Copy application code
COPY run_watchtower_dashboard.py ./
COPY run_all_etl.sh ./
COPY deployment/ ./deployment/
COPY src/ ./src/
COPY secrets/ ./secrets/

# Set Python path to include virtual environment
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/.venv/lib/python3.11/site-packages"

# Prepare writable runtime directories. The Unraid bind-mounted data/logs tree
# contains historical root-owned files; run as root to preserve compatibility.
RUN mkdir -p /app/config /app/logs /app/data \
    && chmod +x /app/run_all_etl.sh

# Health check — API is the stable local health endpoint.
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:45714/health || exit 1

# Expose ports
EXPOSE 45714 7777 7780

# Default command: run API, dashboard, and ETL scheduler under supervisor.
CMD ["supervisord", "-c", "/app/deployment/supervisord.conf"]
