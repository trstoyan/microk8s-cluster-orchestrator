#!/bin/bash

# MicroK8s Cluster Orchestrator Production Deployment Script
# This script sets up the application for production deployment

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DEPLOY_USER="${DEPLOY_USER:-orchestrator}"
DEPLOY_DIR="${DEPLOY_DIR:-/opt/microk8s-orchestrator}"
VENV_PATH="$DEPLOY_DIR/venv"
SERVICE_NAME="microk8s-orchestrator"

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

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root for production deployment"
        exit 1
    fi
}

# Create deployment user
create_user() {
    if ! id "$DEPLOY_USER" &>/dev/null; then
        log_info "Creating deployment user: $DEPLOY_USER"
        useradd -r -s /bin/bash -d "$DEPLOY_DIR" -m "$DEPLOY_USER"
        log_success "User $DEPLOY_USER created"
    else
        log_info "User $DEPLOY_USER already exists"
    fi
}

# Setup deployment directory
setup_directory() {
    log_info "Setting up deployment directory: $DEPLOY_DIR"
    
    # Create directory structure
    mkdir -p "$DEPLOY_DIR"
    mkdir -p "$DEPLOY_DIR/logs"
    mkdir -p "$DEPLOY_DIR/backups"
    mkdir -p "$DEPLOY_DIR/ssh_keys"
    
    # Copy application files
    log_info "Copying application files..."
    cp -r "$PROJECT_ROOT"/* "$DEPLOY_DIR/"
    
    # Set ownership
    chown -R "$DEPLOY_USER:$DEPLOY_USER" "$DEPLOY_DIR"
    
    log_success "Deployment directory setup complete"
}

# Install system dependencies
install_dependencies() {
    log_info "Installing system dependencies..."
    
    # Update package list
    apt-get update
    
    # Install required packages
    apt-get install -y \
        python3 \
        python3-pip \
        python3-venv \
        python3-dev \
        build-essential \
        git \
        ansible \
        openssh-client \
        systemd
    
    log_success "System dependencies installed"
}

# Setup Python virtual environment
setup_venv() {
    log_info "Setting up Python virtual environment..."
    
    # Create virtual environment as deploy user
    sudo -u "$DEPLOY_USER" python3 -m venv "$VENV_PATH"
    
    # Install Python dependencies
    sudo -u "$DEPLOY_USER" "$VENV_PATH/bin/pip" install --upgrade pip
    sudo -u "$DEPLOY_USER" "$VENV_PATH/bin/pip" install -r "$DEPLOY_DIR/requirements.txt"
    
    log_success "Virtual environment setup complete"
}

# Setup systemd service
setup_service() {
    log_info "Setting up systemd service..."
    
    # Copy service file
    cp "$PROJECT_ROOT/microk8s-orchestrator.service" /etc/systemd/system/
    
    # Update service file with correct paths
    sed -i "s|/opt/microk8s-orchestrator|$DEPLOY_DIR|g" /etc/systemd/system/microk8s-orchestrator.service
    sed -i "s|orchestrator|$DEPLOY_USER|g" /etc/systemd/system/microk8s-orchestrator.service
    
    # Reload systemd and enable service
    systemctl daemon-reload
    systemctl enable "$SERVICE_NAME"
    
    log_success "Systemd service setup complete"
}

# Setup SSH keys and permissions
setup_permissions() {
    log_info "Setting up permissions and SSH keys..."
    
    # Setup SSH directory for deploy user
    sudo -u "$DEPLOY_USER" mkdir -p "/home/$DEPLOY_USER/.ssh"
    sudo -u "$DEPLOY_USER" chmod 700 "/home/$DEPLOY_USER/.ssh"
    
    # Copy SSH keys if they exist
    if [[ -d "$DEPLOY_DIR/ssh_keys" ]]; then
        sudo -u "$DEPLOY_USER" cp -r "$DEPLOY_DIR/ssh_keys"/* "/home/$DEPLOY_USER/.ssh/"
        sudo -u "$DEPLOY_USER" chmod 600 "/home/$DEPLOY_USER/.ssh"/*
        sudo -u "$DEPLOY_USER" chmod 644 "/home/$DEPLOY_USER/.ssh"/*.pub
    fi
    
    log_success "Permissions setup complete"
}

# Initialize database
init_database() {
    log_info "Initializing database..."
    
    # Run database initialization as deploy user
    sudo -u "$DEPLOY_USER" -E "$VENV_PATH/bin/python" "$DEPLOY_DIR/scripts/init_db.py"
    
    log_success "Database initialized"
}

# Start service
start_service() {
    log_info "Starting $SERVICE_NAME service..."
    
    systemctl start "$SERVICE_NAME"
    
    # Wait a moment and check status
    sleep 2
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        log_success "Service started successfully"
        log_info "Service status:"
        systemctl status "$SERVICE_NAME" --no-pager
    else
        log_error "Failed to start service"
        log_info "Service logs:"
        journalctl -u "$SERVICE_NAME" --no-pager -n 20
        exit 1
    fi
}

# Main deployment function
deploy() {
    log_info "MicroK8s Cluster Orchestrator Production Deployment"
    log_info "=================================================="
    
    check_root
    create_user
    setup_directory
    install_dependencies
    setup_venv
    setup_permissions
    setup_service
    init_database
    start_service
    
    log_success "Production deployment completed successfully!"
    log_info "Service is running and accessible at http://localhost:5000"
    log_info "To check service status: systemctl status $SERVICE_NAME"
    log_info "To view logs: journalctl -u $SERVICE_NAME -f"
}

# Handle script arguments
case "${1:-deploy}" in
    deploy)
        deploy
        ;;
    status)
        systemctl status "$SERVICE_NAME" --no-pager
        ;;
    logs)
        journalctl -u "$SERVICE_NAME" -f
        ;;
    restart)
        log_info "Restarting $SERVICE_NAME service..."
        systemctl restart "$SERVICE_NAME"
        log_success "Service restarted"
        ;;
    stop)
        log_info "Stopping $SERVICE_NAME service..."
        systemctl stop "$SERVICE_NAME"
        log_success "Service stopped"
        ;;
    *)
        echo "Usage: $0 [deploy|status|logs|restart|stop]"
        echo "  deploy  - Deploy the application (default)"
        echo "  status  - Check service status"
        echo "  logs    - View service logs"
        echo "  restart - Restart the service"
        echo "  stop    - Stop the service"
        exit 1
        ;;
esac
