FROM mcr.microsoft.com/devcontainers/python:1-3.11-bullseye

ENV PYTHONUNBUFFERED 1

# [Optional] If your requirements rarely change, uncomment this section to add them to the image.
# COPY requirements.txt /tmp/pip-tmp/
# RUN pip3 --disable-pip-version-check --no-cache-dir install -r /tmp/pip-tmp/requirements.txt \
#    && rm -rf /tmp/pip-tmp

# [Optional] Uncomment this section to install additional OS packages.
# RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
#     && apt-get -y install --no-install-recommends <your-package-list-here>

# Install prerequisites for Chrome and Chromedriver, and Chrome itself
RUN apt-get update && apt-get install -y wget gnupg unzip jq curl --no-install-recommends \
    && wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    # Install Chromedriver using CfT JSON endpoint
    # Fetches the URL for the latest stable Linux64 Chromedriver
    && CHROMEDRIVER_URL=$(curl -s https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions-with-downloads.json | jq -r '.channels.Stable.downloads.chromedriver[] | select(.platform=="linux64") | .url') \
    && echo "Downloading Chromedriver from ${CHROMEDRIVER_URL}" \
    # Download and install Chromedriver
    && curl -sSL ${CHROMEDRIVER_URL} -o chromedriver_linux64.zip \
    && unzip chromedriver_linux64.zip -d /usr/local/bin/ \
    && rm chromedriver_linux64.zip \
    && chmod +x /usr/local/bin/chromedriver \
    # Clean up apt cache
    && rm -rf /var/lib/apt/lists/*

# The vscode user is already created in the base image, so we skip user creation

RUN pip install --upgrade pip && \
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

# Set environment variables (PYTHONUNBUFFERED=1 is often set by the base image)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python \
    DJANGO_SETTINGS_MODULE=job_applier.settings \
    PATH="/home/vscode/.local/bin:${PATH}" \
    DEBIAN_FRONTEND=noninteractive \
    # Chrome driver path for Selenium
    CHROME_DRIVER_PATH=/usr/local/bin/chromedriver

# Expose ports
EXPOSE 8000 5555 9090