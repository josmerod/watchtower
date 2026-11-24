# The official Python image, as in the root Dockerfile. The uv image that
# ships Python (ghcr.io/astral-sh/uv:python3.11-bookworm-slim) is not rebuilt
# for every Python release: on 2026-11-24 it still held 3.11.14 on Debian 12,
# three patch releases behind the image then running in production.
FROM python:3.11-slim

# uv, pinned: it changes only when this line does.
COPY --from=ghcr.io/astral-sh/uv:0.12.3 /uv /uvx /bin/

# Install system dependencies
# supervisor: to manage multiple processes
# curl, git: standard utilities often needed
# libatomic1: the node binary bundled with Playwright (>= 1.65) needs it, and
# the slim base image does not ship it — `playwright install` cannot even start
RUN apt-get update && apt-get install -y \
    supervisor \
    curl \
    git \
    dos2unix \
    procps \
    libatomic1 \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy dependency files first to leverage cache
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-install-project

# Copy the rest of the application
COPY . .

# Install the project itself
RUN uv sync --frozen

# Convert line endings for shell script
RUN dos2unix run_all_etl.sh && chmod +x run_all_etl.sh

# Create directory for supervisor logs
RUN mkdir -p /app/logs

# Install the browser for the Playwright-backed ETLs (chromium only to save space)
RUN uv run playwright install --with-deps chromium

# Copy configuration files
COPY deployment/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV PATH="/app/.venv/bin:$PATH"

# deploy.py waits on this status after `docker run`: the API is the deploy gate.
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:45714/health || exit 1

# Expose Dashboard port
EXPOSE 7780
# Expose API port
EXPOSE 45714

# Verify uv installation and python path
RUN uv --version && python --version

# Start supervisord
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
