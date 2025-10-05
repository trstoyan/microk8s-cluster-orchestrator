#!/bin/bash

# MicroK8s Cluster Orchestrator Production Startup Script
# This script starts the application using Gunicorn for production deployment

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
VENV_PATH="${VENV_PATH:-$PROJECT_ROOT/venv}"
GUNICORN_CONFIG="${GUNICORN_CONFIG:-$PROJECT_ROOT/gunicorn.conf.py}"
WSGI_MODULE="${WSGI_MODULE:-wsgi:application}"

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

# Check if virtual environment exists
check_venv() {
    if [[ ! -d "$VENV_PATH" ]]; then
        log_error "Virtual environment not found at $VENV_PATH"
        log_info "Please create a virtual environment first:"
        log_info "  python3 -m venv $VENV_PATH"
        log_info "  source $VENV_PATH/bin/activate"
        log_info "  pip install -r requirements.txt"
        exit 1
    fi
}

# Check if Gunicorn is installed
check_gunicorn() {
    if ! "$VENV_PATH/bin/python" -c "import gunicorn" 2>/dev/null; then
        log_error "Gunicorn not found in virtual environment"
        log_info "Installing Gunicorn..."
        "$VENV_PATH/bin/pip" install gunicorn
    fi
}

# Check if WSGI module exists
check_wsgi() {
    if [[ ! -f "$PROJECT_ROOT/wsgi.py" ]]; then
        log_error "WSGI module not found at $PROJECT_ROOT/wsgi.py"
        exit 1
    fi
}

# Check if Gunicorn config exists
check_config() {
    if [[ ! -f "$GUNICORN_CONFIG" ]]; then
        log_error "Gunicorn configuration not found at $GUNICORN_CONFIG"
        exit 1
    fi
}

# Start the application
start_app() {
    log_info "Starting MicroK8s Cluster Orchestrator in production mode..."
    log_info "Project root: $PROJECT_ROOT"
    log_info "Virtual environment: $VENV_PATH"
    log_info "WSGI module: $WSGI_MODULE"
    log_info "Configuration: $GUNICORN_CONFIG"
    
    cd "$PROJECT_ROOT"
    
    # Set environment variables
    export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"
    export FLASK_APP="$WSGI_MODULE"
    
    # Start Gunicorn
    exec "$VENV_PATH/bin/gunicorn" \
        --config "$GUNICORN_CONFIG" \
        "$WSGI_MODULE"
}

# Main execution
main() {
    log_info "MicroK8s Cluster Orchestrator Production Startup"
    log_info "================================================"
    
    check_venv
    check_gunicorn
    check_wsgi
    check_config
    
    start_app
}

# Handle script arguments
case "${1:-start}" in
    start)
        main
        ;;
    check)
        log_info "Checking production setup..."
        check_venv
        check_gunicorn
        check_wsgi
        check_config
        log_success "All checks passed!"
        ;;
    *)
        echo "Usage: $0 [start|check]"
        echo "  start  - Start the production server (default)"
        echo "  check  - Check if production setup is ready"
        exit 1
        ;;
esac
