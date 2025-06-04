FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Chrome and its dependencies for Selenium
RUN apt-get update && apt-get install -y \
    wget \
    gnupg2 \
    && wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /code

# Copy project files
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=job_applier.settings
ENV PORT=7860

ARG DJANGO_SECRET_KEY
ENV SECRET_KEY=$DJANGO_SECRET_KEY

# Collect static files
RUN python manage.py collectstatic --noinput

# Expose the port
EXPOSE 7860

# Start Gunicorn
CMD gunicorn job_applier.wsgi:application --bind 0.0.0.0:$PORT 