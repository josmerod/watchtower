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
COPY src/ ./src/
COPY secrets/ ./secrets/

# Install dependencies
RUN uv sync --frozen --no-dev

# Production stage
FROM python:3.11-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from base stage
COPY --from=base /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=base /usr/local/bin/uv /usr/local/bin/uv
COPY --from=base /app/.venv /app/.venv

# Set working directory
WORKDIR /app

# Copy application code
COPY run_watchtower_dashboard.py ./
COPY src/ ./src/
COPY secrets/ ./secrets/

# Set Python path to include virtual environment
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/.venv/lib/python3.11/site-packages"

# Install Playwright browsers and dependencies (must use uv run to install into venv)

# Create non-root user and writable runtime directories
RUN useradd --create-home --shell /bin/bash watchtower \
    && mkdir -p /app/config \
    && chown -R watchtower:watchtower /app/config
USER watchtower

# Health check — dashboard runs on WATCHTOWER_DASHBOARD_PORT (compose sets 7777)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${WATCHTOWER_DASHBOARD_PORT:-7777}/health || exit 1

# Expose ports
EXPOSE 45714 7777 7780

# Default command
CMD ["uv", "run", "python", "src/launcher/main.py", "--mode", "production"]
