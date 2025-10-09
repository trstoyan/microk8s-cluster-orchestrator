#!/bin/bash
# Server Restart Helper
# Handles clean restart from Web UI or CLI

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_FILE="$PROJECT_DIR/.prod-server.pid"
PORT=5000

echo "🔄 Server Restart Helper"
echo "========================"

# Step 1: Stop current process gracefully
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    echo "🛑 Stopping old process (PID: $OLD_PID)..."
    
    if ps -p $OLD_PID > /dev/null 2>&1; then
        kill $OLD_PID 2>/dev/null || true
        
        # Wait for process to stop (max 10 seconds)
        for i in {1..10}; do
            if ! ps -p $OLD_PID > /dev/null 2>&1; then
                echo "✅ Process stopped"
                break
            fi
            sleep 1
        done
        
        # Force kill if still running
        if ps -p $OLD_PID > /dev/null 2>&1; then
            echo "⚠️  Process still running, forcing stop..."
            kill -9 $OLD_PID 2>/dev/null || true
        fi
    fi
    
    rm -f "$PID_FILE"
fi

# Step 2: Wait for port to be free
echo "⏳ Waiting for port $PORT to be free..."
for i in {1..15}; do
    if ! ss -tln 2>/dev/null | grep -q ":$PORT " && \
       ! netstat -tln 2>/dev/null | grep -q ":$PORT " 2>/dev/null; then
        echo "✅ Port $PORT is free"
        break
    fi
    
    if [ $i -eq 15 ]; then
        echo "❌ Port $PORT still in use after 15 seconds"
        echo "🔪 Killing remaining processes..."
        pkill -f 'cli.py web' 2>/dev/null || true
        sleep 2
    else
        sleep 1
    fi
done

# Step 3: Start new server
echo "🚀 Starting new server..."
cd "$PROJECT_DIR"

# Start in background
nohup "$PROJECT_DIR/.venv/bin/python" "$PROJECT_DIR/cli.py" web --host 0.0.0.0 --port 5000 \
    > "$PROJECT_DIR/logs/production.log" 2>&1 & 

NEW_PID=$!
echo $NEW_PID > "$PID_FILE"

# Wait a bit and verify it started
sleep 2

if ps -p $NEW_PID > /dev/null 2>&1; then
    echo "✅ Server restarted successfully (PID: $NEW_PID)"
    echo "🌐 Access at: http://0.0.0.0:5000"
    exit 0
else
    echo "❌ Server failed to start"
    echo "Check logs: $PROJECT_DIR/logs/production.log"
    rm -f "$PID_FILE"
    exit 1
fi

