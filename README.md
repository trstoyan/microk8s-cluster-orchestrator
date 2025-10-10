# ⚡ MicroK8s Cluster Orchestrator

A comprehensive, agnostic system for managing MicroK8s clusters using Ansible automation and a Python application. This orchestrator provides a complete solution for deploying, configuring, monitoring, and troubleshooting MicroK8s clusters across multiple nodes.

> **Built for developers who understand that AI is just really advanced autocompletion** 🧠⚡

![MicroK8s Cluster Orchestrator](https://img.shields.io/badge/MicroK8s-Orchestrator-blue?style=for-the-badge&logo=kubernetes)
![Python](https://img.shields.io/badge/Python-3.8+-blue?style=flat-square&logo=python)
![Flask](https://img.shields.io/badge/Flask-2.0+-green?style=flat-square&logo=flask)
![Ansible](https://img.shields.io/badge/Ansible-Automation-red?style=flat-square&logo=ansible)
![SQLite](https://img.shields.io/badge/SQLite-Database-lightgrey?style=flat-square&logo=sqlite)
![SSH](https://img.shields.io/badge/SSH-Secure%20Shell-black?style=flat-square&logo=ssh)
![WoL](https://img.shields.io/badge/Wake--on--LAN-Magic%20Packets-purple?style=flat-square&logo=wake-on-lan)
![AI](https://img.shields.io/badge/AI--Assisted-Cursor%20Powered-orange?style=flat-square&logo=artificial-intelligence)

📚 **Documentation**: See the [docs/](docs/) directory for detailed guides and documentation.

## ⚠️ Disclaimer

This project is not affiliated with, endorsed by, or sponsored by Canonical Ltd. or the MicroK8s project. MicroK8s is a trademark of Canonical Ltd. This tool is an independent management interface for MicroK8s clusters.

## ✨ Features

### 🎯 **Core Functionality**
- **Node Management**: Add, remove, and monitor cluster nodes
  - **Auto-Discovery**: Scan clusters to find nodes already joined but not in orchestrator
  - One-click bulk addition of discovered nodes with automatic SSH key generation
  - Friendly duplicate detection with helpful error messages and edit links
- **Cluster Orchestration**: Automated cluster setup, configuration, and graceful shutdown
- **Web Dashboard**: Modern, responsive tabbed interface for system management
  - Overview: Quick status and system actions
  - Updates: Version management with safe update strategies
  - Live Sync: Real-time server-to-server data synchronization
  - Logs: Built-in log viewer with live streaming
  - Timezone: System timezone configuration
- **CLI Tools**: Command-line interface for automation and scripting
- **Real-time Monitoring**: Live status updates and health checks
- **Live Progress Logging**: Ubuntu-style progress indicators for long-running operations

### 🔐 **SSH Key Management**
- **One-Liner Automated Setup**: `curl -sSL http://orchestrator:5000/setup/node-ssh?node_id=1 | bash`
  - Automatic prerequisite checks (SSH client, permissions, connectivity)
  - Creates `.ssh` directory with correct permissions (700)
  - Adds orchestrator's public key to `authorized_keys` (600)
  - Configures passwordless sudo for orchestrator operations
  - Automatic SSH connection test and status update
  - Safe to run multiple times (idempotent)
- **Automatic SSH Key Generation**: Unique SSH key pairs for each node with absolute paths
- **Manual SSH Key Selection**: Choose from existing SSH keys
- **SSH Key Scanning**: Automatic detection and listing of available keys
- **Connection Testing**: Built-in SSH connection validation with sudo access testing
- **Key Regeneration**: Easy key regeneration for compromised or lost keys
- **Auto-Verification**: Setup script automatically tests connection and updates node status

### 🌐 **Network & Communication**
- **Hosts File Configuration**: Automatic `/etc/hosts` configuration for MicroK8s HA clusters
  - Ensures proper hostname resolution across all cluster nodes
  - Creates backups of original files before modification
  - Validates hostname resolution and DNS functionality
  - Essential for MicroK8s High Availability cluster communication

### 🔄 **Live Server Sync**
- **Real-Time Data Synchronization**: Sync orchestrator data between multiple servers
  - Server-to-server inventory comparison (nodes, clusters, SSH keys)
  - Selective sync with checkboxes for specific items
  - Live progress streaming (Ubuntu installer-style logs)
  - Color-coded log output (success, error, warning, info)
  - Session-based authentication for secure cross-server communication
  - CORS support for browser-based sync operations
  - Automatic detection of identical, different, and missing items
- **Embedded in System Management**: Access sync via System Management > Live Sync tab
- **Real-Time Progress**: Watch every step with auto-scrolling log console

### 🎨 **Playbook Editor**
- **Visual Drag-and-Drop Interface**: Build Ansible playbooks without YAML knowledge
- **Template Library**: Pre-built templates for common MicroK8s operations
- **Target Selection System**: Flexible node targeting (all nodes, clusters, groups, individual)
- **Real-time YAML Preview**: Live generation of Ansible YAML from visual components
- **Execution Engine**: Background Ansible execution with real-time monitoring
- **Template Management**: System and user templates with versioning and usage tracking
- **Custom Playbooks**: User-created playbooks with visual configuration support
- **Node Groups**: Custom node groupings for flexible targeting
- **Execution History**: Complete audit trail with status tracking and output capture

### 🔋 **Power Management**
- **Wake-on-LAN (WoL) Management**: Complete Wake-on-LAN functionality for cluster nodes
  - WoL configuration for individual nodes with MAC address management
  - Support for virtual nodes (Proxmox VMs) with special handling
  - Manual wake-up operations from web interface and CLI
  - Cluster-wide wake-up functionality
  - Integration with UPS power management for automatic node startup
- **UPS Power Management**: Intelligent power management for Raspberry Pi 5 deployments
  - USB UPS device detection and configuration
  - NUT (Network UPS Tools) integration
  - Power event monitoring (power loss, low battery, power restored)
  - Automated cluster shutdown/startup based on power events
  - Configurable power management rules
  - Real-time UPS status monitoring

### 📊 **Hardware Reporting & Storage**
- **Comprehensive Hardware Information**: Detailed system information collection
  - CPU information (cores, usage, temperature)
  - Memory details (total, usage, swap)
  - Storage information (physical disks, partitions, filesystems)
  - Network interfaces and configuration
  - GPU detection and information
  - Thermal sensor monitoring
  - Docker and Kubernetes volume tracking
  - LVM and RAID information
- **Longhorn Storage Prerequisites**: Intelligent prerequisite management
  - Actual status display (not checked, met, or failed)
  - Package verification (lvm2, nfs-common, open-iscsi, etc.)
  - Service status checks (iscsid, multipathd)
  - One-click installation of missing prerequisites
  - Color-coded visual feedback (✓ green checks, ✗ red for missing, ? gray for unchecked)

#### 🤖 **AI Assistant with Local RAG System**
- **Local-Only Operation**: Runs entirely on local resources, no external dependencies
- **Retrieval-Augmented Generation (RAG)**: Learns from Ansible outputs and operation logs
- **Searchable Content**: Index and search through playbooks, documentation, and operation logs
- **Multiple Chat Sessions**: Separate conversations for different topics and issues
- **Operation Log Analysis**: Intelligent analysis of failed operations with recommendations
- **Ansible Output Analysis**: Parse and explain complex Ansible execution results
- **Health Insights**: AI-powered system health monitoring and recommendations
- **Knowledge Base**: Automatically builds knowledge from successful and failed operations
- **Privacy-First**: All data processed locally, configurable data retention and anonymization
- **Raspberry Pi 5 Optimized**: Designed for resource-constrained environments

### 🚀 **AI-Assisted Development with Cursor**
This project was developed using **Cursor AI** for exponential development speed. Here's the philosophy behind AI-assisted coding:

- **AI as Advanced Autocompletion**: Cursor AI acts like an incredibly sophisticated autocompletion tool that understands context, architecture, and best practices
- **Code Understanding is Fundamental**: Having solid programming knowledge is essential to understand, review, and maintain AI-generated code effectively
- **Exponential Productivity**: AI doesn't replace developers - it amplifies their capabilities, allowing complex systems to be built in record time
- **Quality Through Understanding**: The key to successful AI-assisted development is understanding the generated code, not just accepting it blindly
- **Architecture-Driven Development**: AI helps implement well-designed architectures faster, but the design thinking still comes from human expertise

**Development Philosophy**: 
> "AI will be like a really advanced autocompletion tool - knowing how to code is the basis to understand the generated code"

This project demonstrates how AI can accelerate development while maintaining code quality through proper understanding and review processes.

### 🔧 **Development Stack & Philosophy**
- **Language**: Python 3.8+ (because life's too short for legacy Python)
- **Framework**: Flask (lightweight, flexible, and doesn't get in your way)
- **Database**: SQLite (zero-config, perfect for orchestration data)
- **Automation**: Ansible (the Swiss Army knife of infrastructure)
- **AI Assistant**: Cursor (exponential development speed)
- **Architecture**: Modular, testable, and maintainable (because technical debt is real)

**Core Principles**:
- **Simplicity over Complexity**: Every feature should be as simple as possible, but no simpler
- **Automation First**: If you're doing it manually more than twice, automate it
- **Fail Fast**: Better to fail quickly with clear errors than to fail silently
- **Documentation as Code**: If it's not documented, it doesn't exist
- **AI-Enhanced Development**: Use AI to amplify human intelligence, not replace it

## 🏗️ Architecture

The system follows a modular architecture with clear separation of concerns:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web UI        │    │   CLI Tool      │    │   API           │
│   (Flask)       │    │   (Click)       │    │   (REST)        │
│   + AI Chat     │    │                 │    │   + AI Endpoints│
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 │
          ┌─────────────────────────────────────────────┐
          │         Orchestration Service               │
          │         (Python Application)                │
          │         + AI Assistant (Local RAG)         │
          └─────────────────┬───────────────────────────┘
                            │
          ┌─────────────────┼───────────────────────────┐
          │                 │                           │
    ┌─────▼─────┐    ┌──────▼──────┐         ┌─────────▼─────────┐
    │  SQLite   │    │   Ansible   │         │   MicroK8s Nodes │
    │ Database  │    │ Playbooks   │         │   (Target Hosts)  │
    │ + RAG KB  │    │ + Docs      │         │                   │
    └───────────┘    └─────────────┘         └───────────────────┘
```

## 🚀 Quick Start

### Prerequisites

#### Control Node (Where orchestrator runs)
- **Python**: 3.8 or higher
- **Ansible**: 2.15 or higher
- **SSH**: Access to target nodes
- **Internet**: Connectivity for package downloads

#### Target Nodes (MicroK8s hosts)
- **Operating System**: Ubuntu 20.04+ or similar Linux distribution
- **Architecture**: x86_64 or ARM64
- **Memory**: Minimum 2GB RAM (4GB+ recommended)
- **Storage**: Minimum 10GB available disk space (20GB+ recommended)
- **Network**: Internet connectivity and proper network configuration
- **Privileges**: Sudo access (passwordless authentication will be configured automatically)
- **Services**: SSH server running and accessible
- **SSH Access**: Initial SSH access (password or existing key) for setup

### Installation

#### Option 1: Automated Setup (Recommended)

**Complete Setup (Full System Configuration):**
```bash
git clone https://github.com/trstoyan/microk8s-cluster-orchestrator.git
cd microk8s-cluster-orchestrator
./scripts/setup_system.sh
```

**Quick Setup (Minimal Configuration):**
```bash
git clone https://github.com/trstoyan/microk8s-cluster-orchestrator.git
cd microk8s-cluster-orchestrator
./scripts/quick_setup.sh
```

#### Option 2: Manual Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/trstoyan/microk8s-cluster-orchestrator.git
   cd microk8s-cluster-orchestrator
   ```

2. **Create Python virtual environment**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. **Initialize the database**:
   ```bash
   python cli.py init-db
   ```

5. **Start the web interface**:
   ```bash
   python cli.py web
   ```

6. **Access the dashboard**:
   Open your browser and go to `http://localhost:5000`

### Basic Usage

1. **Add a node** (SSH key will be automatically generated):
   ```bash
   python cli.py node add --hostname node1 --ip 192.168.1.10 --user ubuntu
   ```
   Follow the setup instructions to add the generated public key to the target node.

2. **Create a cluster**:
   ```bash
   python cli.py cluster add --name production --description "Production MicroK8s cluster" --ha
   ```

3. **Install MicroK8s on a node**:
   ```bash
   python cli.py node install 1
   ```

4. **Setup the cluster**:
   ```bash
   python cli.py cluster setup 1
   ```

5. **Start the web interface**:
   ```bash
   python cli.py web
   ```
   Then open http://localhost:5000 in your browser.

### Production Server Management

Run the web interface as a background service with convenient make commands:

```bash
# Start production server in background
make prod-start

# Check server status
make prod-status

# View server logs in real-time
make prod-logs

# Stop the server
make prod-stop

# Restart the server
make prod-restart
```

The server will run in the background and continue even after you log out. All output is logged to `logs/production.log`. See [docs/PRODUCTION_SERVER_MANAGEMENT.md](docs/PRODUCTION_SERVER_MANAGEMENT.md) for detailed documentation.

## 📖 CLI Reference

### Node Management

```bash
# List all nodes
python cli.py node list

# Add a node (SSH key automatically generated)
python cli.py node add --hostname node1 --ip 192.168.1.10 --user ubuntu

# Update node details
python cli.py node update 1 --hostname new-hostname --cluster-id 2

# Test SSH connection to a node
python cli.py node test-ssh 1

# Show SSH key status for a node
python cli.py node ssh-status 1

# Regenerate SSH key for a node
python cli.py node regenerate-ssh-key 1

# Remove a node
python cli.py node remove 1

# Check node status
python cli.py node status 1

# Install MicroK8s on a node
python cli.py node install 1
```

### Cluster Management

```bash
# List all clusters
python cli.py cluster list

# Add a cluster
python cli.py cluster add --name prod --description "Production cluster" --ha

# Setup a cluster
python cli.py cluster setup 1

# Configure /etc/hosts file for HA cluster communication
python cli.py cluster configure-hosts 1

# Gracefully shutdown a cluster
python cli.py cluster shutdown 1 --graceful

# Force shutdown a cluster (immediate termination)
python cli.py cluster shutdown 1 --force
```

### Playbook Management

```bash
# List available templates
python cli.py playbook list-templates

# Show template details
python cli.py playbook show-template 1

# List custom playbooks
python cli.py playbook list-custom

# List executions
python cli.py playbook list-executions

# Show execution details
python cli.py playbook show-execution 1

# Initialize system templates
python cli.py playbook init-templates
```

### Wake-on-LAN Management

```bash
# Wake a specific node
python cli.py wol wake-node 1

# Wake all nodes in a cluster
python cli.py wol wake-cluster 1

# Check WoL status for a node
python cli.py wol status 1

# Enable WoL for a node
python cli.py wol enable 1

# Disable WoL for a node
python cli.py wol disable 1

# Configure WoL settings for a node
python cli.py wol configure 1 --mac-address "AA:BB:CC:DD:EE:FF" --method ethernet

# Collect MAC addresses from nodes
python cli.py wol collect-mac 1 2 3
```

### UPS Power Management

```bash
# Scan for connected UPS devices
python cli.py ups scan

# List all UPS devices
python cli.py ups list

# Get detailed UPS status
python cli.py ups status 1

# Test UPS connection
python cli.py ups test 1

# Create power management rule
python cli.py ups rules create 1 1 power_loss graceful_shutdown \
  --name "Emergency Shutdown" \
  --action-delay 60

# List power management rules
python cli.py ups rules list

# Start power monitoring
python cli.py ups monitor start

# Check monitoring status
python cli.py ups monitor status
```

### Database Management

```bash
# Show database path and information
python cli.py database path

# Example output:
# Database path: /path/to/cluster_data.db
# Database exists: Yes
# Database size: 98,304 bytes (0.09 MB)
```

## 🎨 Playbook Editor

The visual playbook editor allows you to:

1. **Select Targets**: Choose nodes, clusters, or custom groups
2. **Drag & Drop Tasks**: Build playbooks visually
3. **Configure Parameters**: Set variables and options
4. **Preview YAML**: See generated Ansible playbook
5. **Execute**: Run playbooks with real-time output

### Available Task Categories
- **MicroK8s Operations**: Install, configure, and manage MicroK8s
- **System Operations**: Package management, firewall, system updates
- **Monitoring**: Health checks, metrics collection, status monitoring

### Pre-built Templates
- **Install MicroK8s**: Complete MicroK8s installation with user setup
- **Enable Addons**: Common addons (DNS, Dashboard, Storage, Ingress, Metrics Server)
- **System Health Check**: Comprehensive system health assessment
- **Update Packages**: System package management
- **Configure Firewall**: Security configuration

## 📊 Hardware Reporting System

The orchestrator includes a comprehensive hardware reporting system that collects detailed information about each node's hardware configuration and status.

### Features
- **Automatic Detection**: Discovers all hardware components automatically
- **Detailed Information**: Collects comprehensive data about CPUs, memory, storage, network, and more
- **Real-time Updates**: Hardware information is collected on-demand or scheduled
- **Web Interface**: Beautiful, responsive web interface for viewing hardware reports
- **API Access**: REST API endpoints for programmatic access to hardware data

### Usage
```bash
# Collect hardware report via CLI
python cli.py hardware collect 1

# View in web interface
python cli.py web
# Navigate to: http://localhost:5000/hardware-report/node/1
```

## 🔧 Configuration

The system uses YAML configuration files in the `config/` directory. Key settings include:

- Database path and connection settings
- Ansible configuration and playbook locations
- MicroK8s default settings and network configuration
- SSH connection parameters
- Web interface settings

## 📁 Project Structure

```
microk8s-cluster-orchestrator/
├── app/                    # Python application
│   ├── controllers/        # Web and API controllers
│   ├── models/            # Database models
│   ├── services/          # Business logic
│   ├── templates/         # Web UI templates
│   └── static/           # Static assets
├── ansible/               # Ansible configuration
│   ├── playbooks/         # Ansible playbooks
│   ├── roles/             # Custom Ansible roles
│   └── inventory/         # Dynamic inventories
├── config/                # Configuration files
├── docs/                  # Documentation
├── migrations/            # Database migration scripts
├── scripts/               # Utility and migration scripts
├── ssh_keys/              # SSH key storage directory
├── cli.py                # Command-line interface
├── requirements.txt      # Python dependencies
└── README.md            # This file
```

## 🗄️ Database Schema

The SQLite database includes:

- **nodes** - Node information and status
- **clusters** - Cluster definitions and configuration
- **operations** - Operation history and results
- **configurations** - System and cluster configurations
- **ups** - UPS device information and status
- **ups_cluster_rules** - Power management rules
- **playbook_templates** - Pre-built playbook templates
- **custom_playbooks** - User-created playbooks
- **playbook_executions** - Execution history and results
- **node_groups** - Custom node groupings

## 🔒 Security Features

- **SSH Key Management**: Secure, automated key distribution
- **Access Control**: User authentication and authorization
- **Encrypted Communication**: All communications use SSH encryption
- **Audit Logging**: Comprehensive operation logging
- **Local-Only AI**: Privacy-first AI assistant with no external dependencies

## 📚 Documentation

- [Installation Guide](docs/INSTALLATION.md)
- [User Manual](docs/USER_MANUAL.md)
- [API Documentation](docs/API.md)
- [Playbook Editor Guide](docs/PLAYBOOK_EDITOR.md)
- [Deployment Guide](docs/DEPLOYMENT.md)
- [SSH Key Management](docs/SSH_KEY_MANAGEMENT.md)
- [Wake-on-LAN Guide](docs/WAKE_ON_LAN_GUIDE.md)
- [UPS Setup Guide](docs/NUT_SETUP_GUIDE.md)

## 🤝 Contributing

We welcome contributions! Please see our [CONTRIBUTING.md](CONTRIBUTING.md) guide for details on how to get started.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

- [Code of Conduct](CODE_OF_CONDUCT.md) - Our community standards
- [Security Policy](SECURITY.md) - How to report security issues
- [Contributors](CONTRIBUTORS.md) - Recognition for contributors

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [MicroK8s](https://microk8s.io/) - Lightweight Kubernetes distribution
- [Ansible](https://www.ansible.com/) - Automation platform
- [Flask](https://flask.palletsprojects.com/) - Web framework
- [Bootstrap](https://getbootstrap.com/) - CSS framework

## 🎯 **Technical Achievements**

This project showcases several technical accomplishments:

- **Zero-Config Database**: SQLite with automatic schema migrations
- **SSH Key Orchestration**: Automated key generation, distribution, and management
- **Wake-on-LAN Integration**: Magic packet delivery for remote node startup
- **UPS Power Management**: Intelligent power event handling with NUT integration
- **Visual Playbook Editor**: Drag-and-drop Ansible playbook creation
- **Real-time Monitoring**: Live status updates and health checks
- **Local AI Assistant**: Privacy-first RAG system for troubleshooting
- **Modular Architecture**: Clean separation of concerns and testable components
- **Comprehensive CLI**: Full-featured command-line interface
- **Modern Web UI**: Responsive, professional web interface

**Performance Metrics**:
- **Startup Time**: < 2 seconds for web interface
- **Database Queries**: Optimized with proper indexing
- **SSH Operations**: Parallel execution for multiple nodes
- **Memory Usage**: < 100MB for typical operations
- **AI Response Time**: < 500ms for local RAG queries

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/trstoyan/microk8s-cluster-orchestrator/issues)
- **Discussions**: [GitHub Discussions](https://github.com/trstoyan/microk8s-cluster-orchestrator/discussions)
- **Email**: stoyantr+fromgit@icloud.com

---

**Built with ⚡ by [trstoyan](https://github.com/trstoyan)**

![GitHub stars](https://img.shields.io/github/stars/trstoyan/microk8s-cluster-orchestrator?style=social)
![GitHub forks](https://img.shields.io/github/forks/trstoyan/microk8s-cluster-orchestrator?style=social)
![GitHub watchers](https://img.shields.io/github/watchers/trstoyan/microk8s-cluster-orchestrator?style=social)
