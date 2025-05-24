#!/bin/bash

echo "🚀 Starting Job Applier Production Environment..."

# Ensure log directory exists
mkdir -p /workspace/logs

# Run database migrations
echo "🔄 Running database migrations..."
python manage.py migrate

# Collect static files
echo "📁 Collecting static files..."
python manage.py collectstatic --noinput

# Create cache tables if using database cache
echo "🗄️ Creating cache tables..."
python manage.py createcachetable || true

# Start supervisord
echo "🎯 Starting Supervisor..."
if [ "$1" = "foreground" ]; then
    # Run in foreground for debugging
    supervisord -n -c /etc/supervisor/conf.d/supervisord.conf
else
    # Run in background
    supervisord -c /etc/supervisor/conf.d/supervisord.conf
    
    # Wait a moment for services to start
    sleep 5
    
    # Show status
    echo "📊 Service Status:"
    supervisorctl status
    
    echo ""
    echo "✅ Production environment started!"
    echo "🌐 Django: http://localhost:8000"
    echo "🌸 Flower: http://localhost:5555 (admin/changeme123)"
    echo ""
    echo "📝 Useful commands:"
    echo "  supervisorctl status    - Check service status"
    echo "  supervisorctl restart all - Restart all services"
    echo "  supervisorctl tail -f django - View Django logs"
    echo "  supervisorctl tail -f celery-worker - View Celery logs"
fi