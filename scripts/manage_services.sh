#!/bin/bash

# Service management script for production

case "$1" in
    start)
        echo "🚀 Starting all services..."
        supervisorctl start all
        ;;
    stop)
        echo "🛑 Stopping all services..."
        supervisorctl stop all
        ;;
    restart)
        echo "🔄 Restarting all services..."
        supervisorctl restart all
        ;;
    status)
        echo "📊 Service Status:"
        supervisorctl status
        ;;
    logs)
        service=${2:-django}
        echo "📜 Showing logs for $service..."
        supervisorctl tail -f $service
        ;;
    monitor)
        echo "📊 Real-time monitoring..."
        watch -n 2 'supervisorctl status; echo ""; echo "Redis Info:"; redis-cli info keyspace | grep "^db"; echo ""; echo "Celery Queue:"; redis-cli llen celery'
        ;;
    flower-start)
        echo "🌸 Starting Flower..."
        supervisorctl start flower
        echo "Flower available at http://localhost:5555"
        ;;
    flower-stop)
        echo "🌸 Stopping Flower..."
        supervisorctl stop flower
        ;;
    reload)
        echo "🔄 Reloading Django..."
        supervisorctl restart django
        ;;
    celery-purge)
        echo "🧹 Purging Celery queues..."
        celery -A job_applier purge -f
        ;;
    shell)
        echo "🐚 Opening Django shell..."
        python manage.py shell
        ;;
    dbshell)
        echo "🗄️ Opening database shell..."
        python manage.py dbshell
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|logs [service]|monitor|flower-start|flower-stop|reload|celery-purge|shell|dbshell}"
        echo ""
        echo "Services: django, celery-worker, celery-beat, flower"
        echo ""
        echo "Examples:"
        echo "  $0 status              - Show all service status"
        echo "  $0 logs celery-worker  - Show Celery worker logs"
        echo "  $0 monitor             - Real-time monitoring"
        exit 1
        ;;
esac