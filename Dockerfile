# Use a lightweight Ubuntu image as the base
FROM ubuntu:24.04

# Set environment variables for non-interactive installs
ENV DEBIAN_FRONTEND=noninteractive
# Set Python to be unbuffered, which is useful for seeing logs in Docker
ENV PYTHONUNBUFFERED=1

# Install system dependencies (Python 3.12 is default in Ubuntu 24.04)
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

# 1. Create a virtual environment with uv using Python 3 (3.12 in Ubuntu 24.04).
#    This avoids uv downloading Python and requiring network access.
RUN uv venv --python python3.12
ENV PATH="$MLFLOW_HOME/.venv/bin:$PATH"

# 2. Install all dependencies from pyproject.toml.
RUN uv pip install --no-cache .

# 3. Install the mlflow project itself in editable mode.
RUN uv pip install --no-cache -e .

# Switch back to root for copying HUD files
USER root

# Copy MCP server code and shared utilities
COPY src/ /donotaccess/src/
COPY pyproject.toml /donotaccess/pyproject.toml

# Install Python dependencies for HUD in the mlflow user's venv
# Editable install keeps source files in /donotaccess
RUN PATH="$MLFLOW_HOME/.venv/bin:$PATH" uv pip install --no-cache -e /donotaccess

# Ensure /donotaccess is protected (mlflow_user already owns their home directory)
RUN chmod 700 /donotaccess

# Setup passwordless sudo for debugging
RUN echo "root ALL=(mlflow_user) NOPASSWD: ALL" >> /etc/sudoers

# Set working directory for grader code
WORKDIR /donotaccess

# Expose the default MLflow port (5000)
EXPOSE 5000

# Start services: MLflow server and HUD MCP server
CMD ["sh", "-c", "mlflow server --host 0.0.0.0 & python3 -m src.controller.env & sleep 2 && exec python3 -m src.controller.server"]
