#!/bin/bash

echo "📊 Celery Monitoring Dashboard"
echo "=============================="

while true; do
    clear
    echo "📊 Celery Status - $(date)"
    echo "=============================="
    
    # Check Redis
    echo -n "Redis: "
    if redis-cli ping > /dev/null 2>&1; then
        echo "✅ Running"
    else
        echo "❌ Not running"
    fi
    
    # Check Celery Worker
    echo -n "Celery Worker: "
    if pgrep -f "celery.*worker" > /dev/null; then
        echo "✅ Running"
    else
        echo "❌ Not running"
    fi
    
    # Check Celery Beat
    echo -n "Celery Beat: "
    if pgrep -f "celery.*beat" > /dev/null; then
        echo "✅ Running"
    else
        echo "❌ Not running"
    fi
    
    echo ""
    echo "📈 Queue Statistics:"
    redis-cli -h localhost llen celery 2>/dev/null || echo "Unable to get queue length"
    
    echo ""
    echo "🔄 Recent Tasks (last 5):"
    tail -n 5 logs/celery-worker.log 2>/dev/null | grep -E "Task|Received" || echo "No recent tasks"
    
    echo ""
    echo "Press Ctrl+C to exit"
    sleep 5
done