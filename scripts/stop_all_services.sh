#!/bin/bash

echo "🛑 Stopping all Job Applier services..."

# Function to stop a service
stop_service() {
    local name=$1
    if [ -f logs/${name}.pid ]; then
        pid=$(cat logs/${name}.pid)
        if kill -0 $pid 2>/dev/null; then
            kill $pid
            echo "✅ Stopped $name (PID: $pid)"
        else
            echo "ℹ️ $name was not running"
        fi
        rm -f logs/${name}.pid
    else
        echo "ℹ️ No PID file for $name"
    fi
}

# Stop services
stop_service "celery-worker"
stop_service "celery-beat"
stop_service "flower"

# Stop any remaining Celery processes
pkill -f "celery -A job_applier"

# Stop Gunicorn
pkill -f "gunicorn job_applier.wsgi"

# Optional: Stop Redis (usually you want to keep it running)
# pkill redis-server

echo "✅ All services stopped"