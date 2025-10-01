# Use a lightweight Ubuntu image as the base
FROM ubuntu:24.04

# Set environment variables for non-interactive installs
ENV DEBIAN_FRONTEND=noninteractive
# Set Python to be unbuffered, which is useful for seeing logs in Docker
ENV PYTHONUNBUFFERED=1

# Install system dependencies as the root user.
RUN apt-get update && apt-get install -y \
    make \
    build-essential \
    libssl-dev \
    zlib1g-dev \
    libbz2-dev \
    libreadline-dev \
    libsqlite3-dev \
    wget \
    curl \
    llvm \
    libncursesw5-dev \
    xz-utils \
    tk-dev \
    libxml2-dev \
    libxmlsec1-dev \
    libffi-dev \
    liblzma-dev \
    git \
    sudo \
    python3 \
    python3-pip \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy and install uv from local binary
COPY uv-x86_64-unknown-linux-gnu.tar.gz /tmp/uv.tar.gz
RUN cd /tmp && \
    tar -xzf uv.tar.gz && \
    mv uv-x86_64-unknown-linux-gnu/uv /usr/local/bin/uv && \
    chmod +x /usr/local/bin/uv

# Create a non-root user and set their home directory
RUN useradd -m -s /bin/bash mlflow_user

# Switch to the non-root user
USER mlflow_user
ENV HOME=/home/mlflow_user
ENV MLFLOW_HOME=$HOME/mlflow
WORKDIR $MLFLOW_HOME

# Clone the MLflow test environment
RUN git clone -b CVE-2025-99999-vuln https://github.com/stuxbench/mlflow-clone.git .

# ---- Build and Caching Strategy ----

# 1. Create a virtual environment with uv using system Python.
#    This avoids uv downloading Python and requiring network access.
RUN uv venv --python python3
ENV PATH="$MLFLOW_HOME/.venv/bin:$PATH"

# 2. Install all dependencies from pyproject.toml.
RUN uv pip install --no-cache .

# 3. Install the mlflow project itself in editable mode.
RUN uv pip install --no-cache -e .

# Switch back to root for copying HUD files
USER root

# Copy MCP server code and shared utilities
COPY src/ /app/src/
COPY pyproject.toml /app/pyproject.toml

# Switch back to mlflow_user for installing HUD in their venv
USER mlflow_user
WORKDIR $MLFLOW_HOME

# Install Python dependencies for HUD in the mlflow user's venv
RUN uv pip install --no-cache -e /app

# Expose the default MLflow port (5000)
EXPOSE 5000

# Start services: MLflow server and HUD MCP server
CMD ["sh", "-c", "mlflow server --host 0.0.0.0 & cd /app && python3 -m src.controller.env & sleep 2 && cd /app && exec python3 -m src.controller.server"]
