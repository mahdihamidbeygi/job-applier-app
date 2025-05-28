FROM mcr.microsoft.com/devcontainers/python:3

# Avoid warnings by switching to noninteractive
ENV DEBIAN_FRONTEND=noninteractive

# Create a non-root user
ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=$USER_UID

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
    # Clean up
    && rm -rf /var/lib/apt/lists/*

# Install Chrome and its dependencies for Selenium
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# Install additional packages
RUN apt-get update && \
    apt-get install -y postgresql-client && \
    rm -rf /var/lib/apt/lists/*

# Create the user
RUN groupadd --gid $USER_GID $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME \
    # Add sudo support
    && apt-get update \
    && apt-get install -y sudo \
    && echo $USERNAME ALL=\(root\) NOPASSWD:ALL > /etc/sudoers.d/$USERNAME \
    && chmod 0440 /etc/sudoers.d/$USERNAME \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /workspace

# Install Python development tools
RUN pip install --no-cache-dir \
    black \
    flake8 \
    isort \
    pytest \
    pytest-django \
    ipython \
    django-debug-toolbar \
    celery \
    redis

# Install Python packages
COPY requirements.txt /tmp/pip-tmp/
RUN pip3 install --requirement /tmp/pip-tmp/requirements.txt && \
    rm -rf /tmp/pip-tmp

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DJANGO_SETTINGS_MODULE=job_applier.settings \
    PATH="${PATH}:/home/${USERNAME}/.local/bin" \
    DEBIAN_FRONTEND=dialog \
    HOME=/home/${USERNAME}

# Switch to non-root user
USER $USERNAME