# 🚀 MicroK8s Cluster Orchestrator

A comprehensive MicroK8s cluster orchestration tool with web interface, CLI, and visual playbook editor for managing Kubernetes clusters efficiently.

![MicroK8s Cluster Orchestrator](https://img.shields.io/badge/MicroK8s-Orchestrator-blue?style=for-the-badge&logo=kubernetes)
![Python](https://img.shields.io/badge/Python-3.8+-blue?style=flat-square&logo=python)
![Flask](https://img.shields.io/badge/Flask-2.0+-green?style=flat-square&logo=flask)
![Ansible](https://img.shields.io/badge/Ansible-Automation-red?style=flat-square&logo=ansible)

## ✨ Features

### 🎯 **Core Functionality**
- **Multi-Node Management**: Manage multiple MicroK8s nodes from a single interface
- **Cluster Orchestration**: Automated cluster setup, scaling, and management
- **Web Dashboard**: Modern, responsive web interface for cluster management
- **CLI Tools**: Command-line interface for automation and scripting
- **Real-time Monitoring**: Live status updates and health checks

### 🎨 **Playbook Editor**
- **Visual Playbook Creation**: Drag-and-drop interface for creating Ansible playbooks
- **Template Library**: Pre-built templates for common MicroK8s operations
- **Target Selection**: Flexible targeting (nodes, clusters, custom groups)
- **Real-time Execution**: Live output streaming and progress tracking
- **YAML Preview**: Real-time YAML generation and validation

### 🔧 **Advanced Features**
- **SSH Key Management**: Automated SSH key generation and distribution
- **Wake-on-LAN**: Remote power management for cluster nodes
- **Network Monitoring**: Real-time network status and connectivity checks
- **UPS Integration**: Power management and graceful shutdown capabilities
- **Database Management**: SQLite-based data persistence with backup/restore

## 🏗️ Architecture

```
microk8s-cluster-orchestrator/
├── app/                    # Flask application
│   ├── controllers/        # API and web controllers
│   ├── models/            # Database models
│   ├── services/          # Business logic services
│   ├── templates/         # Jinja2 templates
│   └── static/           # Static assets
├── cli.py                # Command-line interface
├── requirements.txt      # Python dependencies
└── docs/                # Documentation
```

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- MicroK8s installed on target nodes
- SSH access to cluster nodes
- Ansible (for playbook execution)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/trstoyan/microk8s-cluster-orchestrator.git
   cd microk8s-cluster-orchestrator
   ```

2. **Create virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Initialize the database**
   ```bash
   python cli.py init-db
   ```

5. **Start the web interface**
   ```bash
   python cli.py web
   ```

6. **Access the dashboard**
   Open your browser and go to `http://localhost:5000`

## 📖 Usage

### Web Interface
- **Dashboard**: Overview of all clusters and nodes
- **Node Management**: Add, configure, and monitor individual nodes
- **Cluster Management**: Create and manage MicroK8s clusters
- **Playbook Editor**: Visual creation and execution of Ansible playbooks
- **Operations**: View and manage cluster operations

### CLI Commands

#### Node Management
```bash
# Add a new node
python cli.py node add --hostname node1 --ip 192.168.1.10

# List all nodes
python cli.py node list

# Update node details
python cli.py node update 1 --hostname new-hostname --cluster-id 2

# Configure SSH keys
python cli.py node configure-ssh 1
```

#### Cluster Operations
```bash
# Create a new cluster
python cli.py cluster create --name production --description "Production cluster"

# List clusters
python cli.py cluster list

# Scale cluster
python cli.py cluster scale production --nodes 5
```

#### Playbook Management
```bash
# List available templates
python cli.py playbook list-templates

# Show template details
python cli.py playbook show-template 1

# Initialize system templates
python cli.py playbook init-templates
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

## 🔧 Configuration

### Environment Variables
```bash
export FLASK_ENV=development
export FLASK_DEBUG=True
export DATABASE_URL=sqlite:///orchestrator.db
```

### SSH Configuration
- SSH keys are automatically generated and distributed
- Supports both password and key-based authentication
- Configurable SSH ports and users per node

## 📊 Monitoring & Health Checks

- **Real-time Status**: Live updates of node and cluster health
- **Network Monitoring**: Connectivity and latency checks
- **Resource Monitoring**: CPU, memory, and disk usage
- **Alert System**: Notifications for critical issues

## 🛡️ Security Features

- **SSH Key Management**: Secure, automated key distribution
- **Access Control**: User authentication and authorization
- **Encrypted Communication**: All communications use SSH encryption
- **Audit Logging**: Comprehensive operation logging

## 📚 Documentation

- [Installation Guide](docs/INSTALLATION.md)
- [User Manual](docs/USER_MANUAL.md)
- [API Documentation](docs/API.md)
- [Playbook Editor Guide](docs/PLAYBOOK_EDITOR.md)
- [Deployment Guide](docs/DEPLOYMENT.md)
- [SSH Key Management](docs/SSH_KEY_MANAGEMENT.md)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [MicroK8s](https://microk8s.io/) - Lightweight Kubernetes distribution
- [Ansible](https://www.ansible.com/) - Automation platform
- [Flask](https://flask.palletsprojects.com/) - Web framework
- [Bootstrap](https://getbootstrap.com/) - CSS framework

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/trstoyan/microk8s-cluster-orchestrator/issues)
- **Discussions**: [GitHub Discussions](https://github.com/trstoyan/microk8s-cluster-orchestrator/discussions)
- **Email**: [Your Email]

---

**Made with ❤️ by [trstoyan](https://github.com/trstoyan)**

![GitHub stars](https://img.shields.io/github/stars/trstoyan/microk8s-cluster-orchestrator?style=social)
![GitHub forks](https://img.shields.io/github/forks/trstoyan/microk8s-cluster-orchestrator?style=social)
![GitHub watchers](https://img.shields.io/github/watchers/trstoyan/microk8s-cluster-orchestrator?style=social)