# MicroK8s Cluster Orchestrator - Deployment Guide

This guide covers all deployment methods for the MicroK8s Cluster Orchestrator with enhanced SSH key management.

## 🚀 Quick Start

### Option 1: Using Makefile (Recommended)

```bash
# Full installation from scratch
make install-full

# Initialize the database
make init

# Start the web interface
make run
```

### Option 2: Using Setup Scripts

```bash
# Quick setup for experienced users
./quick_setup.sh

# Comprehensive system setup with service
./setup_system.sh
```

### Option 3: Using Docker

```bash
# Build and run with Docker Compose
make docker-build
make docker-run
```

## 📋 Detailed Deployment Methods

### 1. Local Development Deployment

#### Prerequisites
- Python 3.8+
- Ansible 2.15+
- Git

#### Steps
```bash
# Clone the repository
git clone <repository-url>
cd microk8s-cluster-orchestrator

# Install dependencies
make install

# Initialize the application
make init

# Start development server
make dev
```

#### Access
- Web Interface: http://localhost:5000
- API: http://localhost:5000/api/

### 2. Production Deployment

#### Using System Setup Script
```bash
# Run comprehensive setup
./setup_system.sh

# Start as systemd service
sudo systemctl start microk8s-orchestrator

# Enable auto-start
sudo systemctl enable microk8s-orchestrator
```

#### Manual Production Setup
```bash
# Install system dependencies
make install-deps

# Create directories
make create-dirs

# Install application
make install

# Initialize database
make init

# Start production server
make prod
```

### 3. Docker Deployment

#### Using Docker Compose (Recommended)
```bash
# Build and start
make docker-run

# View logs
make docker-logs

# Stop services
make docker-stop
```

#### Manual Docker Commands
```bash
# Build image
docker-compose build

# Start services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f orchestrator
```

### 4. Development with Auto-reload
```bash
# Start development server with auto-reload
make dev
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `FLASK_ENV` | Flask environment | `production` |
| `DATABASE_PATH` | Database file path | `./cluster_data.db` |
| `ORCHESTRATOR_CONFIG` | Config file path | `./config/production.yml` |
| `SSH_KEYS_DIR` | SSH keys directory | `./ssh_keys` |
| `BACKUPS_DIR` | Backups directory | `./backups` |

### Configuration Files

- **Main Config**: `config/production.yml`
- **Local Overrides**: `config/local.yml`
- **Ansible Config**: `ansible/ansible.cfg`

## 📁 Directory Structure

```
microk8s-cluster-orchestrator/
├── app/                    # Application code
├── ansible/               # Ansible playbooks
├── config/                # Configuration files
├── logs/                  # Application logs
├── ssh_keys/             # SSH key storage
├── backups/              # Database backups
├── migrations/           # Database migrations
├── scripts/              # Utility scripts
├── tests/                # Test files
├── docker-compose.yml    # Docker Compose config
├── Dockerfile           # Docker image definition
├── Makefile             # Build and deployment commands
├── requirements.txt     # Python dependencies
└── README.md           # Documentation
```

## 🏥 Health Monitoring

### System Health Check
```bash
# Run comprehensive health check
make health-check

# Check system status
make status

# Validate models
make validate-models
```

### API Health Endpoint
```bash
# Check health via API
curl http://localhost:5000/api/system/health
```

## 🔄 Database Management

### Migrations
```bash
# Run migrations
make migrate

# Validate model consistency
make validate-models

# Sync models with database
make validate-and-sync
```

### Backups
```bash
# Create backup
make backup

# Restore from backup
make restore
```

## 🐳 Docker Configuration

### Docker Compose Services

#### Orchestrator Service
- **Image**: Built from local Dockerfile
- **Port**: 5000
- **Volumes**: 
  - Database, config, logs
  - SSH keys, backups, migrations
- **Health Check**: `/api/system/health`
- **Restart Policy**: `unless-stopped`

### Docker Environment
```yaml
environment:
  - FLASK_ENV=production
  - DATABASE_PATH=/app/cluster_data.db
  - ORCHESTRATOR_CONFIG=/app/config/production.yml
  - SSH_KEYS_DIR=/app/ssh_keys
  - BACKUPS_DIR=/app/backups
```

## 🔐 SSH Key Management

### Automatic Setup
The system automatically:
- Creates SSH key directories with proper permissions
- Generates SSH key pairs for nodes
- Manages key lifecycle (generate, test, regenerate)
- Provides setup instructions

### Manual SSH Key Management
```bash
# Check SSH key status
curl -X POST http://localhost:5000/api/nodes/1/check-ssh-keys

# Regenerate SSH key
curl -X POST http://localhost:5000/api/nodes/1/regenerate-ssh-key
```

## 🛠️ Development Tools

### Code Quality
```bash
# Format code
make format

# Run linting
make lint

# Run tests
make test
```

### Cleanup
```bash
# Clean temporary files
make clean
```

## 📊 Monitoring

### Logs
```bash
# Application logs
tail -f logs/app.log

# Docker logs
make docker-logs

# System service logs
sudo journalctl -u microk8s-orchestrator -f
```

### Metrics
- System health endpoint: `/api/system/health`
- Node status: Available in web UI
- SSH key status: Real-time monitoring in UI

## 🚨 Troubleshooting

### Common Issues

#### 1. SSH Key Generation Fails
```bash
# Check SSH keys directory permissions
ls -la ssh_keys/

# Fix permissions
chmod 700 ssh_keys/
```

#### 2. Database Issues
```bash
# Run health check
make health-check

# Validate models
make validate-models

# Run migrations
make migrate
```

#### 3. Docker Issues
```bash
# Rebuild image
make docker-build

# Check container logs
make docker-logs

# Restart services
make docker-stop && make docker-run
```

#### 4. Permission Issues
```bash
# Check sudoers configuration
sudo visudo -c -f /etc/sudoers.d/microk8s-orchestrator

# Re-run privilege setup
./setup_system.sh --privileges
```

### Getting Help
```bash
# Show all available commands
make help

# Get help for specific command
make help-<command>

# Check system status
make status
```

## 🔄 Updates and Maintenance

### Updating the Application
```bash
# Pull latest changes
git pull

# Update dependencies
make install

# Run migrations
make migrate

# Restart service
sudo systemctl restart microk8s-orchestrator
```

### Regular Maintenance
```bash
# Daily health check
make health-check

# Weekly backup
make backup

# Monthly model validation
make validate-models
```

## 📞 Support

For issues and questions:
1. Check the troubleshooting section above
2. Run `make health-check` to identify issues
3. Check logs for detailed error information
4. Review the README.md for additional documentation

## 🎯 Production Checklist

Before deploying to production:

- [ ] Run `make health-check` - all systems healthy
- [ ] Configure firewall rules
- [ ] Set up SSL/TLS certificates
- [ ] Configure backup strategy
- [ ] Set up monitoring
- [ ] Test SSH key management
- [ ] Verify all API endpoints
- [ ] Check systemd service configuration
- [ ] Review security settings
- [ ] Test disaster recovery procedures
