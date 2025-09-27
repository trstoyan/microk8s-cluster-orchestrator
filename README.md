# MicroK8s Cluster Orchestrator

A comprehensive, agnostic system for managing MicroK8s clusters using Ansible automation and a Python application. This orchestrator provides a complete solution for deploying, configuring, monitoring, and troubleshooting MicroK8s clusters across multiple nodes.

## Features

- **Node Management**: Add, remove, and monitor cluster nodes
- **Cluster Orchestration**: Automated cluster setup, configuration, and graceful shutdown
- **Ansible Integration**: Uses Ansible playbooks for all operations
- **SQLite Database**: Persistent storage for cluster state and history
- **Web Interface**: Modern web UI for cluster management
- **CLI Tool**: Command-line interface for automation and scripting
- **Operation Tracking**: Complete audit trail of all operations
- **Health Monitoring**: Automated health checks and status monitoring
- **Troubleshooting**: Built-in diagnostics and troubleshooting tools
- **Hardware Reporting**: Comprehensive hardware information collection and display
  - CPU information (cores, usage, temperature)
  - Memory details (total, usage, swap)
  - Storage information (physical disks, partitions, filesystems)
  - Network interfaces and configuration
  - GPU detection and information
  - Thermal sensor monitoring
  - Docker and Kubernetes volume tracking
  - LVM and RAID information
- **UPS Power Management**: Intelligent power management for Raspberry Pi 5 deployments
  - USB UPS device detection and configuration
  - NUT (Network UPS Tools) integration
  - Power event monitoring (power loss, low battery, power restored)
  - Automated cluster shutdown/startup based on power events
  - Configurable power management rules
  - Real-time UPS status monitoring
  - Battery charge, voltage, and runtime tracking

## Architecture

The system follows a modular architecture with clear separation of concerns:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web UI        │    │   CLI Tool      │    │   API           │
│   (Flask)       │    │   (Click)       │    │   (REST)        │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 │
          ┌─────────────────────────────────────────────┐
          │         Orchestration Service               │
          │         (Python Application)                │
          └─────────────────┬───────────────────────────┘
                            │
          ┌─────────────────┼───────────────────────────┐
          │                 │                           │
    ┌─────▼─────┐    ┌──────▼──────┐         ┌─────────▼─────────┐
    │  SQLite   │    │   Ansible   │         │   MicroK8s Nodes │
    │ Database  │    │ Playbooks   │         │   (Target Hosts)  │
    └───────────┘    └─────────────┘         └───────────────────┘
```

## Quick Start

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
- **Privileges**: Sudo access with passwordless authentication
- **Services**: SSH server running and accessible

#### Required System Packages
```bash
# Core packages
python3 python3-pip curl wget git snapd systemd openssh-server sudo ufw

# Development tools
build-essential software-properties-common apt-transport-https ca-certificates gnupg lsb-release

# Network and system tools
iptables net-tools iputils-ping dnsutils htop vim nano unzip jq bc lvm2 mdadm

# Container runtime prerequisites
containerd.io docker-ce-cli
```

#### Network Requirements
- **SSH**: Port 22 (configurable)
- **MicroK8s Ports**: 16443, 10250-10259, 2379-2380, 6443
- **Firewall**: Must allow required ports or be properly configured
- **DNS**: Proper DNS resolution for cluster communication

#### Privilege Requirements

**Control Node Privileges:**
The orchestrator needs elevated privileges to perform system-level operations:

```bash
# Required sudo access for:
- Package management (apt, snap)
- Service management (systemctl)
- File operations (chown, chmod, cp, rm)
- Network configuration (ufw, iptables)
- User/group management (usermod, groupadd)
- System configuration (sysctl)
- NUT configuration management
- MicroK8s operations
- Hardware monitoring tools
- UPS management utilities
```

**Setup Orchestrator Privileges:**
```bash
# Automatic privilege setup (recommended)
python cli.py system setup-privileges

# Manual privilege setup
sudo python scripts/setup_orchestrator_privileges.py

# Check current privileges
python cli.py system check-privileges
```

**Manual Privilege Configuration:**
If automatic setup fails, manually configure sudoers:

```bash
# Create sudoers file for orchestrator user
sudo visudo /etc/sudoers.d/microk8s-orchestrator

# Add the following content (replace 'orchestrator' with your username):
orchestrator ALL=(ALL) NOPASSWD: /usr/bin/apt, /usr/bin/apt-get
orchestrator ALL=(ALL) NOPASSWD: /bin/systemctl
orchestrator ALL=(ALL) NOPASSWD: /bin/chown, /bin/chmod, /bin/cp, /bin/rm, /bin/mv, /bin/cat
orchestrator ALL=(ALL) NOPASSWD: /usr/bin/microk8s, /usr/bin/snap
orchestrator ALL=(ALL) NOPASSWD: /usr/sbin/ufw, /sbin/iptables
orchestrator ALL=(ALL) NOPASSWD: /usr/bin/nut-scanner, /usr/bin/upsc, /usr/bin/upsdrvctl
orchestrator ALL=(ALL) NOPASSWD: /usr/sbin/upsd, /usr/sbin/upsmon
# ... (see setup script for complete list)

# Set proper permissions
sudo chmod 440 /etc/sudoers.d/microk8s-orchestrator
sudo chown root:root /etc/sudoers.d/microk8s-orchestrator
```

### Installation

#### Option 1: Automated Setup (Recommended)

**Complete Setup (Full System Configuration):**
```bash
git clone <repository-url>
cd microk8s-cluster-orchestrator
./setup_system.sh
```

**Quick Setup (Minimal Configuration):**
```bash
git clone <repository-url>
cd microk8s-cluster-orchestrator
./quick_setup.sh
```

#### Option 2: Manual Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd microk8s-cluster-orchestrator
   ```

2. **Install system dependencies**:
   ```bash
   sudo apt update
   sudo apt install -y python3 python3-pip python3-venv ansible git
   ```

3. **Create Python virtual environment**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

4. **Install Python dependencies**:
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

5. **Install Ansible collections**:
   ```bash
   ansible-galaxy install -r ansible/requirements.yml
   ```

6. **Setup orchestrator privileges**:
   ```bash
   python cli.py system setup-privileges
   ```

7. **Initialize the system**:
   ```bash
   python cli.py init
   ```

### Basic Usage

1. **Add a node**:
   ```bash
   python cli.py node add --hostname node1 --ip 192.168.1.10 --user ubuntu --key-path ~/.ssh/id_rsa
   ```

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

5. **Shutdown the cluster** (when needed):
   ```bash
   python cli.py cluster shutdown 1 --graceful
   ```

6. **Start the web interface**:
   ```bash
   python cli.py web
   ```
   Then open http://localhost:5000 in your browser.

## CLI Reference

### Node Management

```bash
# List all nodes
python cli.py node list

# Add a node
python cli.py node add --hostname node1 --ip 192.168.1.10 --user ubuntu

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

# Gracefully shutdown a cluster
python cli.py cluster shutdown 1 --graceful

# Force shutdown a cluster (immediate termination)
python cli.py cluster shutdown 1 --force
```

### Web Interface Operations

**Cluster Management:**
- Navigate to "Clusters" section
- Use the Actions dropdown for each cluster
- Available operations: Setup, Scan, Hardware Report, Graceful Shutdown, Force Shutdown
- Monitor operation progress in the Operations page

**Shutdown Options:**
- **Graceful Shutdown**: Safely stops all MicroK8s services with confirmation dialog
- **Force Shutdown**: Immediate termination with warning about potential data loss
- All shutdown operations are tracked and logged in the Operations section

### Operations

```bash
# List operations
python cli.py operation list

# Show operation details
python cli.py operation show 1

# Filter operations by status
python cli.py operation list --status running
```

### Hardware Reporting

```bash
# Collect hardware report for a node
python cli.py hardware collect 1

# View hardware report in web interface
python cli.py web
# Then navigate to: http://localhost:5000/hardware-report/node/1
```

### System Management

```bash
# Check system prerequisites for a node
python cli.py system check-prerequisites 1

# Install missing prerequisites on a node
python cli.py system install-prerequisites 1

# Setup orchestrator privileges (run once after installation)
python cli.py system setup-privileges

# Check orchestrator privileges
python cli.py system check-privileges
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

# Check NUT service status
python cli.py ups services

# Restart NUT services
python cli.py ups restart
```

## Configuration

The system uses YAML configuration files in the `config/` directory. Key settings include:

- Database path and connection settings
- Ansible configuration and playbook locations
- MicroK8s default settings and network configuration
- SSH connection parameters
- Web interface settings

## Project Structure

```
microk8s-cluster-orchestrator/
├── app/                    # Python application
│   ├── controllers/        # Web and API controllers
│   ├── models/            # Database models
│   ├── services/          # Business logic
│   ├── templates/         # Web UI templates
│   └── utils/             # Utilities
├── ansible/               # Ansible configuration
│   ├── playbooks/         # Ansible playbooks
│   │   ├── collect_hardware_report.yml  # Hardware data collection
│   │   ├── shutdown_cluster.yml         # Cluster shutdown operations
│   │   ├── check_prerequisites.yml      # System prerequisites validation
│   │   └── install_prerequisites.yml    # Automated prerequisites installation
│   ├── roles/             # Custom Ansible roles
│   └── inventory/         # Dynamic inventories
├── config/                # Configuration files
├── scripts/               # Utility and migration scripts
│   ├── migrate_disk_partitions_fields.py
│   ├── migrate_ups_tables.py
│   ├── init_db.py
│   ├── backup_db.py
│   └── setup_orchestrator_privileges.py  # Privilege setup automation
├── calculate_disk_total.py # Hardware calculation utility
├── cli.py                 # Command-line interface
├── requirements.txt       # Python dependencies
├── setup_system.sh        # Complete system setup script
├── quick_setup.sh         # Quick minimal setup script
├── README.md             # This file
└── CHANGELOG.md          # Version history and changes
```

## Database Schema

The SQLite database includes:

- **nodes** - Node information and status
  - Basic node information (hostname, IP, SSH details)
  - Hardware information (CPU, memory, disk, GPU)
  - Detailed disk partitions and storage volumes
  - Network and thermal sensor data
- **clusters** - Cluster definitions and configuration
- **operations** - Operation history and results
- **configurations** - System and cluster configurations
- **ups** - UPS device information and status
  - USB UPS device details and configuration
  - NUT service status and driver information
  - Real-time UPS status (battery, voltage, load, temperature)
  - Power management settings and thresholds
- **ups_cluster_rules** - Power management rules
  - Links UPS devices to clusters
  - Defines power events and cluster actions
  - Execution history and success tracking
  - Priority-based rule execution

## Hardware Reporting System

The orchestrator includes a comprehensive hardware reporting system that collects detailed information about each node's hardware configuration and status.

### Features
- **Automatic Detection**: Discovers all hardware components automatically
- **Detailed Information**: Collects comprehensive data about CPUs, memory, storage, network, and more
- **Real-time Updates**: Hardware information is collected on-demand or scheduled
- **Web Interface**: Beautiful, responsive web interface for viewing hardware reports
- **API Access**: REST API endpoints for programmatic access to hardware data

### Hardware Data Collected
- **CPU**: Model, cores, usage, temperature
- **Memory**: Total, usage, swap information
- **Storage**: Physical disks, partitions, filesystems, LVM, RAID
- **Network**: Interfaces, configurations, performance
- **GPU**: Detection and usage information
- **Thermal**: Temperature sensors and fan speeds
- **Containers**: Docker volumes, Kubernetes PVCs/PVs, storage classes

### Usage
```bash
# Collect hardware report via CLI
python cli.py hardware collect 1

# View in web interface
python cli.py web
# Navigate to: http://localhost:5000/hardware-report/node/1

# Trigger via API
curl -X POST http://localhost:5000/api/hardware-report \
  -H "Content-Type: application/json" \
  -d '{"node_id": 1}'
```

## UPS Power Management System

The orchestrator includes a comprehensive UPS power management system designed for Raspberry Pi 5 deployments with USB-connected UPS devices. This system provides intelligent power management to ensure safe cluster shutdown during power outages and automatic recovery when power is restored.

### Features

- **USB UPS Detection**: Automatically detects and configures USB-connected UPS devices
- **NUT Integration**: Uses Network UPS Tools (NUT) for UPS communication and control
- **Power Event Monitoring**: Monitors power loss, low battery, and power restoration events
- **Automated Cluster Management**: Executes configurable actions on clusters based on power events
- **Real-time Status Monitoring**: Tracks battery charge, voltage, load, and temperature
- **Rule-based Configuration**: Flexible power management rules with priority-based execution
- **Web Interface**: Complete web-based management interface for UPS devices and rules
- **CLI and API Support**: Full command-line and REST API access to all UPS functions

### Power Events

- **Power Loss**: UPS switches to battery power
- **Low Battery**: Battery charge drops below configured threshold
- **Critical Battery**: Battery critically low (10% or less)
- **Power Restored**: Main power returns, UPS back online

### Cluster Actions

- **Graceful Shutdown**: Safely shutdown cluster with proper cleanup
- **Force Shutdown**: Immediate cluster shutdown
- **Startup**: Start cluster when power is restored
- **Scale Down**: Reduce cluster resources to conserve power
- **Scale Up**: Restore full cluster resources
- **Pause/Resume**: Temporarily pause or resume cluster operations

### UPS Management Usage

**Initial Setup:**
```bash
# Install NUT packages (on Raspberry Pi 5)
sudo apt install nut nut-client nut-server nut-driver

# Scan for connected UPS devices
python cli.py ups scan

# Start power monitoring
python cli.py ups monitor start
```

**Power Management Rules:**
```bash
# Create emergency shutdown rule
python cli.py ups rules create 1 1 power_loss graceful_shutdown \
  --name "Emergency Shutdown" \
  --action-delay 60

# Create low battery protection rule
python cli.py ups rules create 1 1 low_battery force_shutdown \
  --name "Low Battery Protection" \
  --battery-threshold 20 \
  --action-delay 30

# Create power recovery rule
python cli.py ups rules create 1 1 power_restored startup \
  --name "Power Recovery" \
  --priority 50
```

**Web Interface:**
- Navigate to "UPS Management" section
- View all configured UPS devices and their status
- Create and manage power management rules
- Monitor power events and rule execution
- Configure UPS settings and thresholds

**API Usage:**
```bash
# Get UPS status
curl -X GET http://localhost:5000/api/ups/1/status

# Create power management rule
curl -X POST http://localhost:5000/api/ups/rules \
  -H "Content-Type: application/json" \
  -d '{
    "ups_id": 1,
    "cluster_id": 1,
    "power_event": "power_loss",
    "cluster_action": "graceful_shutdown",
    "name": "Emergency Shutdown",
    "action_delay": 60
  }'

# Start power monitoring
curl -X POST http://localhost:5000/api/ups/monitor/start
```

## API Endpoints

The system provides REST API endpoints for:
- Node management (CRUD operations)
- Cluster management
- Operation tracking
- System health checks
- Hardware reporting and data collection
- UPS power management and monitoring
- Power management rules configuration

## Security

- SQLite database is excluded from version control
- SSH keys are stored securely with proper permissions
- Configuration supports environment-specific settings
- Sensitive data can be encrypted in the database

## Development

The system is designed to be:
- **Turing Complete**: Fully programmable and extensible
- **Agnostic**: Works with any infrastructure that supports SSH
- **Modular**: Easy to extend with custom playbooks and operations
- **Persistent**: All state and history stored in SQLite

## License

MIT License - see LICENSE file for details.

## Support

For support:
- Check operation logs for detailed error information
- Review the troubleshooting playbooks
- Create issues in the repository for bugs or feature requests