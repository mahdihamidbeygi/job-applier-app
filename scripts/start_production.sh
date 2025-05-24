#!/bin/bash

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "🔌 Activating virtual environment..."
    source venv/bin/activate
else
    echo "⚠️  No virtual environment found. Run ./scripts/init_codespace.sh first!"
    exit 1
fi

export DJANGO_DEBUG=False

echo "🔍 Running Django deployment checks..."
python manage.py check --deploy

echo "🚀 Starting Gunicorn server..."
gunicorn job_applier.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 2 \
    --threads 4 \
    --worker-class gthread \
    --log-level info \
    --access-logfile - \
    --error-logfile -