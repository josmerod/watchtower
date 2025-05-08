# TODO: This is a temporary Dockerfile. Refine
# Use the latest CentOS Stream 9 as the base image
FROM centos:stream9

# Set environment variables for non-interactive installs and UTF-8
ENV LANG en_US.UTF-8
ENV LC_ALL en_US.UTF-8

# Install system dependencies
RUN dnf -y update && \
    dnf -y install \
        python3 \
        python3-pip \
        python3-venv \
        git \
        curl \
        gcc \
        make \
        # Add any other system dependencies here
    && dnf clean all

# Set up a working directory
WORKDIR /app

# Copy only requirements first for better caching
COPY requirements.txt .

# Install Python dependencies in a virtual environment
RUN python3 -m venv /opt/venv && \
    /opt/venv/bin/pip install --upgrade pip && \
    /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

# Ensure venv is used for all future RUN/CMD/ENTRYPOINT
ENV PATH="/opt/venv/bin:$PATH"

# Copy only the source code and data directory
COPY src/ ./src/
COPY data/ ./data/

# (Optional) Copy other necessary files, e.g., config, scripts, etc.
# COPY config/ ./config/
# COPY scripts/ ./scripts/

# Expose the port your app runs on (change as needed)
EXPOSE 8000

# Set the default command (adjust as needed, e.g., for FastAPI). Using streamlit
CMD ["streamlit", "run", "src/web/fullstreamlit/main.py"]
