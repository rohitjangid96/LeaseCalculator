#!/bin/bash

# Change to script directory first
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "🚀 Starting Lease Application (Production Structure)..."
echo "📍 Working directory: $(pwd)"

# Install dependencies
pip3 install --user flask flask-cors python-dateutil 2>&1 | grep -v "already satisfied" || true

# Kill old processes
pkill -f "app.py" || true
pkill -f "main_app.py" || true
pkill -f "complete_lease_backend" || true
pkill -f "http.server.*8000" || true
sleep 2

# Start Flask app (from lease_application directory)
cd "$SCRIPT_DIR/lease_application"
echo "📍 Application directory: $(pwd)"

# Ensure logs directory exists
mkdir -p logs

# Start Flask application (serves both API and static files)
echo "🚀 Starting Flask application..."
python3 app.py > logs/lease_app.log 2>&1 &
FLASK_PID=$!
echo "✅ Flask app starting on http://localhost:5001 (PID: $FLASK_PID)"

# Wait for server to be ready
echo "⏳ Waiting for server to start..."
max_attempts=30
attempt=0
while [ $attempt -lt $max_attempts ]; do
    if curl -s http://localhost:5001/login.html > /dev/null 2>&1; then
        echo "✅ Server is ready!"
        break
    fi
    attempt=$((attempt + 1))
    sleep 1
    echo -n "."
done
echo ""

if [ $attempt -eq $max_attempts ]; then
    echo "⚠️  Server may still be starting. Check logs if pages don't load."
fi

# Open application
echo "🌐 Opening application..."
sleep 1
open http://localhost:5001/login.html 2>/dev/null || start http://localhost:5001/login.html 2>/dev/null || xdg-open http://localhost:5001/login.html

echo ""
echo "══════════════════════════════════════════════════════════════"
echo "   📊 Application Ready!"
echo "══════════════════════════════════════════════════════════════"
echo ""
echo "🔗 Application: http://localhost:5001"
echo "📝 Login: http://localhost:5001/login.html"
echo "📊 Dashboard: http://localhost:5001/dashboard.html"
echo "📄 Logs: $(pwd)/logs/lease_app.log"
echo ""
echo "Press Ctrl+C to stop"
echo ""

tail -f logs/lease_app.log

