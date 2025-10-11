#!/bin/bash
# Server Watchdog - Manages orchestrator server lifecycle
# Called by systemd to ensure clean start/stop/restart

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="$PROJECT_DIR/.venv/bin/python"
CLI_SCRIPT="$PROJECT_DIR/cli.py"
PORT=5000
MAX_WAIT=30

echo "🐕 Server Watchdog starting..."
echo "📁 Project: $PROJECT_DIR"
echo "🔍 Port: $PORT"

# Function to check if port is free
is_port_free() {
    ! ss -tln 2>/dev/null | grep -q ":$PORT " && \
    ! netstat -tln 2>/dev/null | grep -q ":$PORT " 2>/dev/null
}

# Function to kill processes on port
kill_port_processes() {
    local port=$1
    echo "🔍 Checking for processes on port $port..."
    
    # Try to find PIDs using the port
    local pids=$(ss -tlnp 2>/dev/null | grep ":$port " | grep -oP 'pid=\K[0-9]+' || \
                 netstat -tlnp 2>/dev/null | grep ":$port " | awk '{print $NF}' | grep -oP '[0-9]+' | head -1 || \
                 ps aux | grep '[c]li.py web' | awk '{print $2}')
    
    if [ -n "$pids" ]; then
        echo "⚠️  Found process(es) using port $port: $pids"
        for pid in $pids; do
            if ps -p $pid > /dev/null 2>&1; then
                echo "🔪 Killing process $pid..."
                kill $pid 2>/dev/null || true
                sleep 1
                if ps -p $pid > /dev/null 2>&1; then
                    echo "⚠️  Process still running, using SIGKILL..."
                    kill -9 $pid 2>/dev/null || true
                fi
            fi
        done
        echo "✅ Processes killed"
        return 0
    else
        echo "✅ No processes found on port $port"
        return 0
    fi
}

# Function to wait for port to be free
wait_for_port_free() {
    local max_wait=$1
    local waited=0
    
    echo "⏳ Waiting for port $PORT to be free (max ${max_wait}s)..."
    
    while [ $waited -lt $max_wait ]; do
        if is_port_free; then
            echo "✅ Port $PORT is free"
            return 0
        fi
        
        echo "   Waiting... (${waited}s/${max_wait}s)"
        sleep 1
        waited=$((waited + 1))
    done
    
    echo "❌ Port $PORT still not free after ${max_wait}s"
    return 1
}

# Cleanup function
cleanup() {
    echo "🧹 Watchdog cleanup..."
    # Don't kill the server here - let systemd handle it
}

trap cleanup EXIT

# Main workflow
echo ""
echo "Step 1: Clean up any orphaned processes"
kill_port_processes $PORT

echo ""
echo "Step 2: Wait for port to be available"
if ! wait_for_port_free $MAX_WAIT; then
    echo "❌ Cannot proceed - port $PORT is still in use"
    echo "💡 Manual cleanup needed:"
    echo "   sudo pkill -f 'cli.py web'"
    echo "   sudo systemctl stop microk8s-orchestrator"
    exit 1
fi

echo ""
echo "Step 3: Start the orchestrator server"
echo "🚀 Launching: $PYTHON_BIN $CLI_SCRIPT web --host 0.0.0.0 --port $PORT"
echo ""

# Start the server (this blocks until server stops)
exec "$PYTHON_BIN" "$CLI_SCRIPT" web --host 0.0.0.0 --port $PORT

