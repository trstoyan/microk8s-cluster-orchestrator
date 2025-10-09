#!/bin/bash

# MicroK8s Cluster Orchestrator - System Setup Script
# This script prepares the system for running the MicroK8s Cluster Orchestrator
# It handles dependencies, privileges, and initial configuration

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$PROJECT_DIR/.venv"
PYTHON_VERSION="3.8"
ANSIBLE_VERSION="2.15"
USER=$(whoami)

# Functions
print_header() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

check_root() {
    if [[ $EUID -eq 0 ]]; then
        print_error "This script should not be run as root directly."
        print_info "It will use sudo when needed. Please run as a regular user."
        exit 1
    fi
}

check_sudo() {
    if ! sudo -n true 2>/dev/null; then
        print_warning "This script requires sudo privileges."
        print_info "You may be prompted for your password during setup."
        echo
        read -p "Press Enter to continue or Ctrl+C to abort..."
    fi
}

check_os() {
    print_header "Checking Operating System"
    
    if [[ -f /etc/os-release ]]; then
        . /etc/os-release
        print_info "Detected OS: $NAME $VERSION"
        
        # Check if running on Raspberry Pi
        if [[ -f /proc/device-tree/model ]] && grep -q "Raspberry Pi" /proc/device-tree/model 2>/dev/null; then
            print_info "Detected Raspberry Pi hardware"
            RASPBERRY_PI=true
        else
            RASPBERRY_PI=false
        fi
        
        # Check architecture
        ARCH=$(uname -m)
        print_info "Architecture: $ARCH"
        
        if [[ "$ID" != "ubuntu" && "$ID" != "debian" ]]; then
            print_warning "This script is optimized for Ubuntu/Debian systems."
            print_warning "Other distributions may require manual adjustments."
        fi
    else
        print_error "Cannot detect operating system."
        exit 1
    fi
}

install_system_dependencies() {
    print_header "Installing System Dependencies"
    
    # Determine the correct package manager
    if command -v apt >/dev/null 2>&1; then
        PKG_MANAGER="apt"
        PKG_UPDATE="update"
        PKG_INSTALL="install"
    elif command -v apt-get >/dev/null 2>&1; then
        PKG_MANAGER="apt-get"
        PKG_UPDATE="update"
        PKG_INSTALL="install"
    else
        print_error "No supported package manager found (apt or apt-get)"
        exit 1
    fi
    
    print_info "Using package manager: $PKG_MANAGER"
    print_info "Updating package list..."
    if ! sudo $PKG_MANAGER $PKG_UPDATE; then
        print_error "Failed to update package list"
        exit 1
    fi
    
    print_info "Installing essential packages..."
    
    # Base packages that should work on all systems
    BASE_PACKAGES="python3 python3-pip python3-venv python3-dev build-essential curl wget git openssh-server sudo ufw apt-transport-https ca-certificates gnupg lsb-release software-properties-common iptables net-tools iputils-ping dnsutils htop vim nano unzip jq bc lvm2 mdadm"
    
    # Packages that might not be available on all systems
    OPTIONAL_PACKAGES="snapd ansible ansible-core"
    
    # Install base packages
    if ! sudo $PKG_MANAGER $PKG_INSTALL -y $BASE_PACKAGES; then
        print_error "Failed to install base system dependencies"
        exit 1
    fi
    
    # Try to install optional packages, but don't fail if they're not available
    for package in $OPTIONAL_PACKAGES; do
        if sudo $PKG_MANAGER $PKG_INSTALL -y $package 2>/dev/null; then
            print_info "Installed optional package: $package"
        else
            print_warning "Optional package not available: $package"
        fi
    done
    
    print_success "System dependencies installed"
}

setup_python_environment() {
    print_header "Setting up Python Environment"
    
    # Check Python version
    python3_version=$(python3 --version | cut -d' ' -f2)
    print_info "Python version: $python3_version"
    
    # Create virtual environment
    if [[ ! -d "$VENV_DIR" ]]; then
        print_info "Creating Python virtual environment..."
        python3 -m venv "$VENV_DIR"
        print_success "Virtual environment created"
    else
        print_info "Virtual environment already exists"
    fi
    
    # Activate virtual environment
    source "$VENV_DIR/bin/activate"
    
    # Upgrade pip
    print_info "Upgrading pip..."
    pip install --upgrade pip setuptools wheel
    
    # Install Python dependencies
    print_info "Installing Python dependencies..."
    pip install -r requirements.txt
    
    print_success "Python environment setup complete"
}

setup_ansible() {
    print_header "Setting up Ansible"
    
    # Check if Ansible is installed
    if ! command -v ansible >/dev/null 2>&1; then
        print_warning "Ansible not found, attempting to install via pip..."
        if pip install ansible; then
            print_success "Ansible installed via pip"
        else
            print_error "Failed to install Ansible"
            print_warning "Continuing without Ansible - some features may not work"
            return 0
        fi
    fi
    
    # Check Ansible version
    ansible_version=$(ansible --version | head -n1 | cut -d' ' -f2)
    print_info "Ansible version: $ansible_version"
    
    # Install Ansible collections if requirements file exists
    if [[ -f "$PROJECT_DIR/ansible/requirements.yml" ]]; then
        print_info "Installing Ansible collections..."
        if ansible-galaxy install -r "$PROJECT_DIR/ansible/requirements.yml"; then
            print_success "Ansible collections installed"
        else
            print_warning "Failed to install some Ansible collections"
        fi
    else
        print_warning "Ansible requirements file not found, skipping collections installation"
    fi
    
    print_success "Ansible setup complete"
}

setup_orchestrator_privileges() {
    print_header "Setting up Orchestrator Privileges"
    
    print_info "Configuring sudo privileges for orchestrator operations..."
    
    # Run the privilege setup script
    if [[ -f "$PROJECT_DIR/scripts/setup_orchestrator_privileges.py" ]]; then
        sudo python3 "$PROJECT_DIR/scripts/setup_orchestrator_privileges.py"
        print_success "Privileges configured successfully"
    else
        print_warning "Privilege setup script not found. Setting up basic sudoers configuration..."
        
        # Create basic sudoers file
        sudo tee /etc/sudoers.d/microk8s-orchestrator > /dev/null <<EOF
# MicroK8s Cluster Orchestrator privileges
$USER ALL=(ALL) NOPASSWD: /usr/bin/apt, /usr/bin/apt-get
$USER ALL=(ALL) NOPASSWD: /bin/systemctl
$USER ALL=(ALL) NOPASSWD: /bin/chown, /bin/chmod, /bin/cp, /bin/rm, /bin/mv, /bin/cat
$USER ALL=(ALL) NOPASSWD: /usr/bin/microk8s, /usr/bin/snap
$USER ALL=(ALL) NOPASSWD: /usr/sbin/ufw, /sbin/iptables
$USER ALL=(ALL) NOPASSWD: /usr/sbin/usermod, /usr/sbin/groupadd, /usr/sbin/useradd
$USER ALL=(ALL) NOPASSWD: /sbin/sysctl, /usr/bin/tee
$USER ALL=(ALL) NOPASSWD: /usr/bin/nut-scanner, /usr/bin/upsc, /usr/bin/upsdrvctl, /usr/bin/upscmd
$USER ALL=(ALL) NOPASSWD: /usr/sbin/upsd, /usr/sbin/upsmon, /usr/sbin/upssched
EOF
        
        sudo chmod 440 /etc/sudoers.d/microk8s-orchestrator
        sudo chown root:root /etc/sudoers.d/microk8s-orchestrator
        
        # Validate sudoers file
        if sudo visudo -c -f /etc/sudoers.d/microk8s-orchestrator; then
            print_success "Basic privileges configured successfully"
        else
            print_error "Failed to configure privileges"
            exit 1
        fi
    fi
}

create_directories() {
    print_header "Creating Required Directories"
    
    # Create project directories
    sudo mkdir -p /opt/microk8s-orchestrator
    sudo mkdir -p /var/log/microk8s-orchestrator
    sudo mkdir -p /etc/nut
    sudo mkdir -p /var/lib/nut
    sudo mkdir -p /var/log/nut
    sudo mkdir -p /var/run/nut
    
    # Set proper ownership
    sudo chown -R "$USER:$USER" /opt/microk8s-orchestrator
    sudo chown -R "$USER:$USER" /var/log/microk8s-orchestrator
    
    # Create logs directory in project
    mkdir -p "$PROJECT_DIR/logs"
    
    print_success "Required directories created"
}

configure_firewall() {
    print_header "Configuring Firewall"
    
    print_info "Setting up UFW firewall rules..."
    
    # Allow SSH
    sudo ufw allow ssh
    
    # Allow MicroK8s ports
    sudo ufw allow 16443/tcp  # API server
    sudo ufw allow 10250:10259/tcp  # Kubelet and other services
    sudo ufw allow 2379:2380/tcp  # etcd
    sudo ufw allow 6443/tcp  # Kubernetes API
    
    # Allow NUT ports
    sudo ufw allow 3493/tcp  # NUT upsd
    sudo ufw allow 3493/udp  # NUT upsd
    
    # Enable firewall
    sudo ufw --force enable
    
    print_success "Firewall configured"
}

setup_systemd_service() {
    print_header "Setting up Systemd Service"
    
    print_info "Creating systemd service for the orchestrator..."
    
    sudo tee /etc/systemd/system/microk8s-orchestrator.service > /dev/null <<EOF
[Unit]
Description=MicroK8s Cluster Orchestrator
After=network.target

[Service]
Type=simple
User=$USER
Group=$USER
WorkingDirectory=$PROJECT_DIR
Environment=PATH=$VENV_DIR/bin:/usr/local/bin:/usr/bin:/bin
ExecStart=$VENV_DIR/bin/python $PROJECT_DIR/cli.py web
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
    
    sudo systemctl daemon-reload
    sudo systemctl enable microk8s-orchestrator.service
    
    print_success "Systemd service configured"
    print_info "To start the service: sudo systemctl start microk8s-orchestrator"
}

initialize_database() {
    print_header "Initializing Database"
    
    cd "$PROJECT_DIR"
    source "$VENV_DIR/bin/activate"
    
    print_info "Initializing orchestrator database..."
    python cli.py init
    
    print_success "Database initialized"
}

test_installation() {
    print_header "Testing Installation"
    
    cd "$PROJECT_DIR"
    source "$VENV_DIR/bin/activate"
    
    # Test basic CLI functionality
    print_info "Testing CLI functionality..."
    if python cli.py --help > /dev/null 2>&1; then
        print_success "CLI is working"
    else
        print_error "CLI test failed"
        return 1
    fi
    
    # Test privilege setup
    print_info "Testing privilege configuration..."
    if python cli.py system check-privileges; then
        print_success "Privileges are properly configured"
    else
        print_warning "Some privilege tests failed"
    fi
    
    # Test database
    print_info "Testing database connection..."
    if python -c "from app.models.database import get_session; session = get_session(); session.close()"; then
        print_success "Database connection working"
    else
        print_error "Database connection failed"
        return 1
    fi
    
    print_success "Installation test completed"
}

show_completion_message() {
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║          🎉 SETUP COMPLETE - SUMMARY                      ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    echo "✅ What Was Installed/Configured:"
    echo "   ✓ Python $(python3 --version 2>&1 | cut -d' ' -f2)"
    echo "   ✓ Virtual environment (.venv)"
    echo "   ✓ Python dependencies ($(pip list 2>/dev/null | wc -l) packages)"
    echo "   ✓ Ansible $(ansible --version 2>&1 | head -1 | cut -d' ' -f3 || echo 'installed')"
    
    # Check what's actually installed
    if id nut &>/dev/null; then
        echo "   ✓ NUT (Network UPS Tools) - UPS support enabled"
    else
        echo "   ⊘ NUT not installed - UPS features disabled (optional)"
    fi
    
    if command -v microk8s &>/dev/null; then
        echo "   ✓ MicroK8s - This machine is a cluster node"
    else
        echo "   ⊘ MicroK8s not installed - Orchestrator will manage remote nodes"
    fi
    
    echo "   ✓ Sudo privileges configured"
    echo "   ✓ Systemd service created"
    echo "   ✓ Firewall rules configured"
    echo "   ✓ Database initialized"
    echo ""
    echo "📊 System Status:"
    echo "   📁 Project: $PROJECT_DIR"
    echo "   👤 User: $USER"
    if systemctl is-enabled microk8s-orchestrator &>/dev/null; then
        echo "   🔧 Service: Enabled (starts on boot)"
    fi
    if [ -f "$PROJECT_DIR/.prod-server.pid" ]; then
        echo "   🟢 Server: Running"
    else
        echo "   🔴 Server: Stopped"
    fi
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║              ✨ NEXT STEPS                                ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    echo "🚀 Quick Start:"
    echo "   make prod-start       # Start server in background"
    echo "   make prod-status      # Check server status"
    echo ""
    echo "🌐 Access Web Interface:"
    echo "   http://localhost:5000"
    echo ""
    echo "📋 Useful Commands:"
    echo "   make logo            # Show project logo"
    echo "   make help            # See all available commands"
    echo "   make prod-logs       # View server logs"
    echo "   make update-dry      # Check for updates"
    echo ""
    echo -e "${GREEN}For more information, see the README.md file.${NC}"
}

# Main execution
main() {
    print_header "MicroK8s Cluster Orchestrator - System Setup"
    echo -e "${BLUE}This script will prepare your system for the MicroK8s Cluster Orchestrator.${NC}"
    echo -e "${BLUE}It will install dependencies, configure privileges, and set up the environment.${NC}"
    echo
    
    # Pre-flight checks
    check_root
    check_sudo
    check_os
    
    # Confirmation
    echo -e "${YELLOW}Ready to proceed with the setup?${NC}"
    read -p "Press Enter to continue or Ctrl+C to abort..."
    
    # Setup steps
    install_system_dependencies
    setup_python_environment
    setup_ansible
    setup_orchestrator_privileges
    create_directories
    configure_firewall
    setup_systemd_service
    initialize_database
    test_installation
    
    # Completion
    show_completion_message
}

# Handle script arguments
case "${1:-}" in
    --help|-h)
        echo "MicroK8s Cluster Orchestrator - System Setup Script"
        echo
        echo "Usage: $0 [OPTIONS]"
        echo
        echo "Options:"
        echo "  --help, -h     Show this help message"
        echo "  --test         Run installation test only"
        echo "  --privileges   Setup privileges only"
        echo
        echo "This script will:"
        echo "  - Install system dependencies (Python, Ansible, etc.)"
        echo "  - Create Python virtual environment"
        echo "  - Install Python packages"
        echo "  - Configure Ansible collections"
        echo "  - Setup orchestrator privileges"
        echo "  - Configure firewall rules"
        echo "  - Create systemd service"
        echo "  - Initialize database"
        echo "  - Run installation tests"
        exit 0
        ;;
    --test)
        cd "$PROJECT_DIR"
        source "$VENV_DIR/bin/activate"
        test_installation
        exit 0
        ;;
    --privileges)
        setup_orchestrator_privileges
        exit 0
        ;;
    *)
        main
        ;;
esac
