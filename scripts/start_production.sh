#!/bin/bash

# Export environment for production
export DJANGO_DEBUG=False

# Run production checks
echo "🔍 Running Django deployment checks..."
python manage.py check --deploy

# Start Gunicorn
echo "🚀 Starting Gunicorn server..."
gunicorn job_applier.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 2 \
    --threads 4 \
    --worker-class gthread \
    --log-level info \
    --access-logfile - \
    --error-logfile - \
    --timeout 120