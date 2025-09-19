#!/bin/bash
# Setup script for MicroK8s Cluster Orchestrator

set -e

echo "🚀 Setting up MicroK8s Cluster Orchestrator..."

# Check Python version
python_version=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
required_version="3.8"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "❌ Python 3.8 or higher is required. Found: $python_version"
    exit 1
fi

echo "✅ Python version check passed: $python_version"

# Check if Ansible is installed
if ! command -v ansible &> /dev/null; then
    echo "❌ Ansible is not installed. Please install Ansible 2.15 or higher."
    exit 1
fi

ansible_version=$(ansible --version | head -n1 | cut -d' ' -f3 | cut -d']' -f1)
echo "✅ Ansible version check passed: $ansible_version"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Install Ansible collections
echo "📦 Installing Ansible collections..."
ansible-galaxy install -r ansible/requirements.yml

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p logs config ansible/inventory

# Initialize the system
echo "🏗️  Initializing system..."
python cli.py init

echo ""
echo "🎉 Setup completed successfully!"
echo ""
echo "Next steps:"
echo "1. Activate the virtual environment: source venv/bin/activate"
echo "2. Add nodes: python cli.py node add --hostname <hostname> --ip <ip>"
echo "3. Create clusters: python cli.py cluster add --name <name>"
echo "4. Start web interface: python cli.py web"
echo ""
echo "For help: python cli.py --help"
