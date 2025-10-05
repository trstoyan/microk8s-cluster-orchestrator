#!/bin/bash

# MicroK8s Cluster Orchestrator Production Stop Script
# This script stops the Gunicorn production server

set -euo pipefail

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_FILE="${PID_FILE:-$PROJECT_ROOT/gunicorn.pid}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Stop the application gracefully
stop_graceful() {
    if [[ -f "$PID_FILE" ]]; then
        local pid
        pid=$(cat "$PID_FILE")
        
        if kill -0 "$pid" 2>/dev/null; then
            log_info "Stopping Gunicorn master process (PID: $pid)..."
            kill -TERM "$pid"
            
            # Wait for graceful shutdown
            local count=0
            while kill -0 "$pid" 2>/dev/null && [[ $count -lt 30 ]]; do
                sleep 1
                ((count++))
                log_info "Waiting for graceful shutdown... ($count/30)"
            done
            
            if kill -0 "$pid" 2>/dev/null; then
                log_warning "Graceful shutdown failed, forcing termination..."
                kill -KILL "$pid"
            fi
            
            log_success "Gunicorn master process stopped"
        else
            log_warning "PID file exists but process is not running"
        fi
        
        rm -f "$PID_FILE"
    else
        log_warning "PID file not found at $PID_FILE"
    fi
}

# Force stop all Gunicorn processes
stop_force() {
    log_info "Force stopping all Gunicorn processes..."
    
    # Find and kill all Gunicorn processes
    local pids
    pids=$(pgrep -f "gunicorn.*wsgi:application" || true)
    
    if [[ -n "$pids" ]]; then
        echo "$pids" | xargs kill -KILL 2>/dev/null || true
        log_success "All Gunicorn processes stopped"
    else
        log_info "No Gunicorn processes found"
    fi
    
    # Clean up PID file
    rm -f "$PID_FILE"
}

# Check if any Gunicorn processes are running
check_status() {
    local pids
    pids=$(pgrep -f "gunicorn.*wsgi:application" || true)
    
    if [[ -n "$pids" ]]; then
        log_info "Gunicorn processes running:"
        ps -p "$pids" -o pid,ppid,cmd
        return 0
    else
        log_info "No Gunicorn processes running"
        return 1
    fi
}

# Main execution
main() {
    log_info "MicroK8s Cluster Orchestrator Production Stop"
    log_info "============================================="
    
    case "${1:-graceful}" in
        graceful)
            stop_graceful
            ;;
        force)
            stop_force
            ;;
        status)
            check_status
            ;;
        *)
            echo "Usage: $0 [graceful|force|status]"
            echo "  graceful - Stop gracefully (default)"
            echo "  force    - Force stop all processes"
            echo "  status   - Check if processes are running"
            exit 1
            ;;
    esac
}

main "$@"
