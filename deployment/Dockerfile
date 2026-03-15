FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim

# Install system dependencies
# supervisor: to manage multiple processes
# curl, git: standard utilities often needed
RUN apt-get update && apt-get install -y \
    supervisor \
    curl \
    git \
    dos2unix \
    procps \
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

# Copy configuration files
COPY deployment/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV PATH="/app/.venv/bin:$PATH"

# Expose Dashboard port
EXPOSE 7780
# Expose API port
EXPOSE 45714

# Verify uv installation and python path
RUN uv --version && python --version

# Start supervisord
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
