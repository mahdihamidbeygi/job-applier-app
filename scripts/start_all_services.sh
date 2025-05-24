#!/bin/bash

# This script starts all services needed for production

echo "🚀 Starting all Job Applier services..."

# Create logs directory
mkdir -p logs

# Function to start a service in background
start_service() {
    local name=$1
    local command=$2
    echo "Starting $name..."
    nohup $command > logs/${name}.log 2>&1 &
    echo "$!" > logs/${name}.pid
    echo "✅ $name started (PID: $(cat logs/${name}.pid))"
}

# Start Redis if not running
if ! pgrep -x "redis-server" > /dev/null; then
    start_service "redis" "redis-server"
    sleep 2
fi

# Start Celery Worker
start_service "celery-worker" "celery -A job_applier worker -l info --concurrency=2"

# Start Celery Beat
start_service "celery-beat" "celery -A job_applier beat -l info"

# Optional: Start Flower for Celery monitoring
# start_service "flower" "celery -A job_applier flower --port=5555"

# Start Django/Gunicorn
echo "🌐 Starting Django application..."
export DJANGO_DEBUG=False
gunicorn job_applier.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 2 \
    --threads 4 \
    --worker-class gthread \
    --log-level info \
    --access-logfile logs/gunicorn-access.log \
    --error-logfile logs/gunicorn-error.log \
    --timeout 120