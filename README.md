# MicroK8s Cluster Orchestrator

A comprehensive, agnostic system for managing MicroK8s clusters using Ansible automation and a Python application. This orchestrator provides a complete solution for deploying, configuring, monitoring, and troubleshooting MicroK8s clusters across multiple nodes.

## Features

- **Node Management**: Add, remove, and monitor cluster nodes
- **Cluster Orchestration**: Automated cluster setup and configuration
- **Ansible Integration**: Uses Ansible playbooks for all operations
- **SQLite Database**: Persistent storage for cluster state and history
- **Web Interface**: Modern web UI for cluster management
- **CLI Tool**: Command-line interface for automation and scripting
- **Operation Tracking**: Complete audit trail of all operations
- **Health Monitoring**: Automated health checks and status monitoring
- **Troubleshooting**: Built-in diagnostics and troubleshooting tools

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

- Python 3.8 or higher
- Ansible 2.15 or higher
- SSH access to target nodes
- Ubuntu 20.04+ or similar Linux distribution on target nodes

### Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd microk8s-cluster-orchestrator
   ```

2. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Install Ansible collections**:
   ```bash
   ansible-galaxy install -r ansible/requirements.yml
   ```

4. **Initialize the system**:
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

5. **Start the web interface**:
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
```

### Operations

```bash
# List operations
python cli.py operation list

# Show operation details
python cli.py operation show 1

# Filter operations by status
python cli.py operation list --status running
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
│   └── utils/             # Utilities
├── ansible/               # Ansible configuration
│   ├── playbooks/         # Ansible playbooks
│   ├── roles/             # Custom Ansible roles
│   └── inventory/         # Dynamic inventories
├── config/                # Configuration files
├── cli.py                 # Command-line interface
└── requirements.txt       # Python dependencies
```

## Database Schema

The SQLite database includes:

- **nodes** - Node information and status
- **clusters** - Cluster definitions and configuration
- **operations** - Operation history and results
- **configurations** - System and cluster configurations

## API Endpoints

The system provides REST API endpoints for:
- Node management (CRUD operations)
- Cluster management
- Operation tracking
- System health checks

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