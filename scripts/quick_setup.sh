#!/bin/bash

# MicroK8s Cluster Orchestrator - Quick Setup Script
# Minimal setup for experienced users

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
USER=$(whoami)

echo "🚀 MicroK8s Cluster Orchestrator - Quick Setup"
echo "=============================================="

# Check if running as root
if [[ $EUID -eq 0 ]]; then
    echo "❌ Don't run as root. This script will use sudo when needed."
    exit 1
fi

# Install basic dependencies
echo "📦 Installing basic dependencies..."
sudo apt update
sudo apt install -y python3 python3-pip python3-venv ansible git

# Create virtual environment
echo "🐍 Setting up Python environment..."
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Install Ansible collections
echo "⚙️  Installing Ansible collections..."
ansible-galaxy install -r ansible/requirements.yml

# Setup basic privileges
echo "🔐 Setting up privileges..."
sudo tee /etc/sudoers.d/microk8s-orchestrator > /dev/null <<EOF
$USER ALL=(ALL) NOPASSWD: /usr/bin/apt, /usr/bin/apt-get
$USER ALL=(ALL) NOPASSWD: /bin/systemctl
$USER ALL=(ALL) NOPASSWD: /bin/chown, /bin/chmod, /bin/cp, /bin/rm, /bin/mv
$USER ALL=(ALL) NOPASSWD: /usr/bin/microk8s, /usr/bin/snap
$USER ALL=(ALL) NOPASSWD: /usr/sbin/ufw, /sbin/iptables
$USER ALL=(ALL) NOPASSWD: /usr/bin/nut-scanner, /usr/bin/upsc, /usr/bin/upsdrvctl
EOF

sudo chmod 440 /etc/sudoers.d/microk8s-orchestrator
sudo chown root:root /etc/sudoers.d/microk8s-orchestrator

# Initialize database
echo "🗄️  Initializing database..."
python cli.py init

echo "✅ Quick setup complete!"
echo
echo "Next steps:"
echo "1. Start the web interface: python cli.py web"
echo "2. Add a node: python cli.py node add --hostname node1 --ip 192.168.1.10 --user ubuntu"
echo "3. Check prerequisites: python cli.py system check-prerequisites 1"
echo
echo "For full setup with firewall, systemd service, and complete configuration:"
echo "  ./setup_system.sh"
