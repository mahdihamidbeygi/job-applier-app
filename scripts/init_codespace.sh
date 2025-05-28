#!/bin/bash

echo "🚀 Initializing Job Applier Codespace..."

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "🐍 Creating virtual environment..."
    python3 -m venv venv
else
    echo "🐍 Virtual environment already exists"
fi

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
python -m pip install --upgrade pip

# Install dependencies
echo "📦 Installing Python dependencies..."
pip install -r requirements.txt

# Function to check if PostgreSQL is ready
check_postgres() {
    python -c "
import psycopg2
import time
import os
from urllib.parse import urlparse

database_url = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/jobapplier')
parsed = urlparse(database_url)

max_attempts = 30
attempt = 0

print('⏳ Waiting for PostgreSQL...')
while attempt < max_attempts:
    try:
        conn = psycopg2.connect(
            host=parsed.hostname or 'localhost',
            port=parsed.port or 5432,
            user=parsed.username or 'postgres',
            password=parsed.password or 'postgres',
            database='postgres'  # Connect to default db first
        )
        conn.close()
        print('✅ PostgreSQL is ready!')
        return 0
    except Exception as e:
        attempt += 1
        if attempt % 5 == 0:
            print(f'   Still waiting... (attempt {attempt}/{max_attempts})')
        time.sleep(1)

print('⚠️  PostgreSQL not available, using SQLite instead')
os.environ['DATABASE_URL'] = 'sqlite:///db.sqlite3'
return 1
"
}

# Check PostgreSQL (but don't fail if not available)
check_postgres

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
    User.objects.create_superuser('admin', 'admin@example.com', 'flower123')
    print("✅ Superuser created: admin/flower123")
else:
    print("ℹ️ Superuser already exists")
EOF

# Check if Redis is available (optional, won't fail if not)
echo "🔍 Checking Redis connection..."
python -c "
try:
    import redis
    r = redis.Redis(host='localhost', port=6379, decode_responses=True)
    r.ping()
    print('✅ Redis is available')
except:
    print('⚠️  Redis is not available (Celery features may not work)')
"

echo ""
echo "✅ Codespace initialization complete!"
echo ""
echo "📝 Virtual environment is activated. To activate it in new terminals:"
echo "   source venv/bin/activate"
echo ""
echo "🌐 Start the development server with:"
echo "   python manage.py runserver 0.0.0.0:8000"
echo ""
echo "🚀 Or start production server with:"
echo "   ./scripts/start_production.sh"
echo ""
echo "👤 Admin login: admin / flower123"