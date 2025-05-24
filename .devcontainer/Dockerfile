FROM mcr.microsoft.com/devcontainers/python:3.11

# Avoid warnings by switching to noninteractive
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    build-essential \
    libpq-dev \
    wget \
    gnupg2 \
    # Add development tools
    vim \
    htop \
    # Redis tools for monitoring
    redis-tools \
    # PostgreSQL client
    postgresql-client \
    # Process management
    supervisor \
    # Clean up
    && rm -rf /var/lib/apt/lists/*

# Install Chrome and its dependencies for Selenium
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# The vscode user is already created in the base image, so we skip user creation

# Set work directory
WORKDIR /workspace

# Copy requirements first for better caching
COPY requirements.txt /tmp/pip-tmp/

# Install Python packages
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r /tmp/pip-tmp/requirements.txt && \
    # Install additional production tools
    pip install --no-cache-dir \
    black \
    flake8 \
    isort \
    pytest \
    pytest-django \
    ipython \
    django-debug-toolbar \
    flower \
    django-extensions \
    # Monitoring tools
    prometheus-client \
    django-prometheus && \
    rm -rf /tmp/pip-tmp

# Create necessary directories
RUN mkdir -p /workspace/logs /workspace/staticfiles /workspace/media && \
    chown -R vscode:vscode /workspace

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DJANGO_SETTINGS_MODULE=job_applier.settings \
    PATH="${PATH}:/home/vscode/.local/bin" \
    DEBIAN_FRONTEND=dialog \
    HOME=/home/vscode \
    # Chrome driver path for Selenium
    CHROME_DRIVER_PATH=/usr/bin/chromedriver

# Copy supervisor configuration if it exists
# COPY .devcontainer/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Switch to vscode user (already exists in base image)
USER vscode

# Expose ports
EXPOSE 8000 5555 9090