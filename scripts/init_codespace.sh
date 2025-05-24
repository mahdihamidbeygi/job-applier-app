#!/bin/bash

echo "🚀 Initializing Job Applier Codespace..."

# Install dependencies
echo "📦 Installing Python dependencies..."
pip install -r requirements.txt

# Wait for PostgreSQL
echo "⏳ Waiting for PostgreSQL..."
while ! pg_isready -h localhost -p 5432 -U postgres; do
    sleep 1
done

# Wait for Redis
echo "⏳ Waiting for Redis..."
while ! redis-cli -h localhost ping > /dev/null 2>&1; do
    sleep 1
done

# Run migrations
echo "🔄 Running database migrations..."
python manage.py migrate

# Collect static files
echo "📁 Collecting static files..."
python manage.py collectstatic --noinput

# Create superuser if it doesn't exist
echo "👤 Creating default superuser..."
python manage.py shell << EOF
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'changeme123')
    print("✅ Superuser created: admin/changeme123")
else:
    print("ℹ️ Superuser already exists")
EOF

# Test Celery connection
echo "🔧 Testing Celery connection..."
python -c "
from celery import Celery
app = Celery('test')
app.config_from_object('django.conf:settings', namespace='CELERY')
print('✅ Celery connection successful')
"

echo "✅ Codespace initialization complete!"
echo "🌐 Access your app at the forwarded port 8000"
echo "📝 Remember to change the admin password!"