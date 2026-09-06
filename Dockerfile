# Company AI Workbench Production Container
FROM python:3.13-slim

# Install system dependencies: Git, SQLite3, curl, Node.js (for multi-model runners)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    sqlite3 \
    curl \
    ca-certificates \
    gnupg \
    && mkdir -p /etc/apt/keyrings \
    && curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg \
    && echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_20.x nodistro main" | tee /etc/apt/sources.list.d/nodesource.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Setup application directory and data mount points
WORKDIR /app
RUN mkdir -p /data /workspace

# Install project package
COPY pyproject.toml /app/
COPY src/ /app/src/
COPY prototype/ /app/prototype/

RUN pip install --no-cache-dir -e .

# Configure Git default identity inside container
RUN git config --global user.name "Workbench Daemon" \
    && git config --global user.email "workbench@local.daemon" \
    && git config --global commit.gpgsign false

# Environment configuration
ENV PYTHONUNBUFFERED=1
ENV WORKBENCH_DB=/data/workbench.db
ENV WORKBENCH_NODE_PATH=/usr/bin/node
ENV PYTHONPATH=/app/src:/app/prototype

EXPOSE 8088

# Default healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8088/ || exit 1

# Launch Web UI & Engine Daemon
CMD ["wb", "ui", "--port", "8088", "--host", "0.0.0.0", "--no-browser"]
