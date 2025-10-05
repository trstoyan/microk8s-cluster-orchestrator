# MicroK8s Cluster Orchestrator - Production Deployment Guide

This guide covers deploying the MicroK8s Cluster Orchestrator in a production environment using Gunicorn as the WSGI server.

## Overview

The production deployment includes:
- **Gunicorn WSGI Server**: Production-grade WSGI server instead of Flask's development server
- **Systemd Service**: Automatic startup and management
- **Proper Error Handling**: Enhanced API error handling with detailed error messages
- **Security Configuration**: Isolated user and proper permissions
- **Logging**: Structured logging for monitoring and debugging

## Quick Start

### 1. Install Dependencies

```bash
# Install system dependencies
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-venv python3-dev build-essential git ansible openssh-client systemd

# Install Python dependencies
pip install -r requirements.txt
```

### 2. Start Production Server

#### Option A: Using CLI (Recommended for testing)
```bash
# Start with production mode
python cli.py web --production --host 0.0.0.0 --port 5000

# Or start with development mode (NOT for production)
python cli.py web --host 0.0.0.0 --port 5000
```

#### Option B: Using Production Scripts
```bash
# Check if production setup is ready
./scripts/start_production.sh check

# Start production server
./scripts/start_production.sh start
```

#### Option C: Using Gunicorn Directly
```bash
# Using configuration file
gunicorn --config gunicorn.conf.py wsgi:application

# Using command line options
gunicorn --bind 0.0.0.0:5000 --workers 4 --timeout 30 wsgi:application
```

### 3. Stop Production Server

```bash
# Stop gracefully
./scripts/stop_production.sh graceful

# Force stop all processes
./scripts/stop_production.sh force

# Check status
./scripts/stop_production.sh status
```

## Full Production Deployment

### 1. Automated Deployment

```bash
# Run as root for full system setup
sudo ./scripts/deploy_production.sh deploy
```

This script will:
- Create a dedicated `orchestrator` user
- Set up the application in `/opt/microk8s-orchestrator`
- Install all dependencies
- Configure systemd service
- Start the service automatically

### 2. Manual Deployment

#### Step 1: Create Application User
```bash
sudo useradd -r -s /bin/bash -d /opt/microk8s-orchestrator -m orchestrator
```

#### Step 2: Setup Application Directory
```bash
sudo mkdir -p /opt/microk8s-orchestrator
sudo cp -r . /opt/microk8s-orchestrator/
sudo chown -R orchestrator:orchestrator /opt/microk8s-orchestrator
```

#### Step 3: Create Virtual Environment
```bash
sudo -u orchestrator python3 -m venv /opt/microk8s-orchestrator/venv
sudo -u orchestrator /opt/microk8s-orchestrator/venv/bin/pip install --upgrade pip
sudo -u orchestrator /opt/microk8s-orchestrator/venv/bin/pip install -r /opt/microk8s-orchestrator/requirements.txt
```

#### Step 4: Initialize Database
```bash
sudo -u orchestrator /opt/microk8s-orchestrator/venv/bin/python /opt/microk8s-orchestrator/scripts/init_db.py
```

#### Step 5: Setup Systemd Service
```bash
sudo cp microk8s-orchestrator.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable microk8s-orchestrator
sudo systemctl start microk8s-orchestrator
```

## Configuration

### Environment Variables

You can customize the deployment using environment variables:

```bash
# Gunicorn configuration
export GUNICORN_BIND="0.0.0.0:5000"
export GUNICORN_WORKERS="4"
export GUNICORN_TIMEOUT="30"
export GUNICORN_LOG_LEVEL="info"

# Application paths
export VENV_PATH="/opt/microk8s-orchestrator/venv"
export GUNICORN_CONFIG="/opt/microk8s-orchestrator/gunicorn.conf.py"
```

### Gunicorn Configuration

The `gunicorn.conf.py` file contains production-optimized settings:

- **Workers**: Automatically set to `CPU_COUNT * 2 + 1`
- **Timeout**: 30 seconds for long-running operations
- **Logging**: Structured logging to stdout/stderr
- **Security**: Request size limits and field limits
- **Performance**: Preload application for better memory usage

## Service Management

### Systemd Commands

```bash
# Check service status
sudo systemctl status microk8s-orchestrator

# View logs
sudo journalctl -u microk8s-orchestrator -f

# Restart service
sudo systemctl restart microk8s-orchestrator

# Stop service
sudo systemctl stop microk8s-orchestrator

# Start service
sudo systemctl start microk8s-orchestrator
```

### Using Deployment Scripts

```bash
# Check deployment status
sudo ./scripts/deploy_production.sh status

# View logs
sudo ./scripts/deploy_production.sh logs

# Restart service
sudo ./scripts/deploy_production.sh restart

# Stop service
sudo ./scripts/deploy_production.sh stop
```

## Monitoring and Logging

### Log Locations

- **Systemd logs**: `journalctl -u microk8s-orchestrator`
- **Application logs**: Check stdout/stderr in systemd
- **Access logs**: Gunicorn access logs via systemd

### Health Checks

The application provides health check endpoints:

```bash
# Basic health check
curl http://localhost:5000/api/system/health

# Detailed system status
curl http://localhost:5000/api/system/status
```

## Troubleshooting

### Common Issues

#### 1. Permission Errors
```bash
# Fix ownership
sudo chown -R orchestrator:orchestrator /opt/microk8s-orchestrator

# Fix SSH key permissions
sudo chmod 600 /home/orchestrator/.ssh/*
```

#### 2. Database Issues
```bash
# Reinitialize database
sudo -u orchestrator /opt/microk8s-orchestrator/venv/bin/python /opt/microk8s-orchestrator/scripts/init_db.py
```

#### 3. Service Won't Start
```bash
# Check service status
sudo systemctl status microk8s-orchestrator

# View detailed logs
sudo journalctl -u microk8s-orchestrator -n 50
```

#### 4. API 500 Errors

The application now includes better error handling for common issues:

- **SSH Key Not Configured**: Clear error message with setup instructions
- **Missing Files**: FileNotFoundError with specific file path
- **Permission Issues**: PermissionError with details
- **General Errors**: Detailed error messages with context

### Debug Mode

For debugging, you can run in debug mode:

```bash
# Using CLI with debug
python cli.py web --production --debug

# Using Gunicorn with reload
gunicorn --config gunicorn.conf.py --reload --log-level debug wsgi:application
```

## Security Considerations

### 1. User Isolation
- Application runs as dedicated `orchestrator` user
- Limited file system access via systemd security settings

### 2. Network Security
- Bind to specific interfaces (not 0.0.0.0 in production)
- Use reverse proxy (nginx/apache) for HTTPS termination
- Implement firewall rules

### 3. SSH Key Management
- SSH keys stored in isolated directory
- Proper file permissions (600 for private keys)
- Regular key rotation

### 4. Database Security
- SQLite database with proper permissions
- Regular backups
- Consider PostgreSQL for multi-user environments

## Performance Tuning

### Gunicorn Workers
```bash
# For CPU-bound workloads
workers = CPU_COUNT * 2 + 1

# For I/O-bound workloads (recommended for this app)
workers = CPU_COUNT * 4
```

### Memory Usage
- Enable `preload_app = True` for better memory efficiency
- Monitor memory usage with `htop` or `ps`
- Adjust worker count based on available memory

### Timeout Settings
- Increase timeout for long-running Ansible operations
- Set `timeout = 120` for complex cluster operations
- Use `keepalive = 5` for better connection reuse

## Backup and Recovery

### Database Backup
```bash
# Manual backup
sudo -u orchestrator cp /opt/microk8s-orchestrator/cluster_data.db /opt/microk8s-orchestrator/backups/cluster_data_$(date +%Y%m%d_%H%M%S).db

# Automated backup (add to crontab)
0 2 * * * sudo -u orchestrator /opt/microk8s-orchestrator/scripts/backup_db.py
```

### Configuration Backup
```bash
# Backup SSH keys and configuration
sudo tar -czf orchestrator_backup_$(date +%Y%m%d).tar.gz /opt/microk8s-orchestrator/ssh_keys /opt/microk8s-orchestrator/config
```

## Upgrading

### 1. Stop Service
```bash
sudo systemctl stop microk8s-orchestrator
```

### 2. Backup Current Installation
```bash
sudo cp -r /opt/microk8s-orchestrator /opt/microk8s-orchestrator.backup
```

### 3. Update Application
```bash
sudo -u orchestrator git pull origin main
sudo -u orchestrator /opt/microk8s-orchestrator/venv/bin/pip install -r /opt/microk8s-orchestrator/requirements.txt
```

### 4. Run Migrations
```bash
sudo -u orchestrator /opt/microk8s-orchestrator/venv/bin/python /opt/microk8s-orchestrator/scripts/validate_and_sync_models.py
```

### 5. Restart Service
```bash
sudo systemctl start microk8s-orchestrator
```

## Support

For issues and support:
1. Check the logs: `sudo journalctl -u microk8s-orchestrator -f`
2. Verify configuration: `./scripts/start_production.sh check`
3. Test API endpoints: `curl http://localhost:5000/api/system/health`
4. Check system resources: `htop`, `df -h`, `free -h`
