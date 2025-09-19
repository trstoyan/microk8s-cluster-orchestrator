# Scripts Directory

This directory contains utility scripts for the MicroK8s Cluster Orchestrator.

## Database Scripts

### `init_db.py`
Initialize or recreate the database with all required tables.

```bash
# Initialize database (skip if exists)
python scripts/init_db.py

# Force recreation of database
python scripts/init_db.py --force
```

## Usage

All scripts should be run from the project root directory with the virtual environment activated:

```bash
source .venv/bin/activate
python scripts/<script_name>.py
```

### `backup_db.py`
Database backup and restore utilities.

```bash
# Create a backup
python scripts/backup_db.py backup

# List available backups
python scripts/backup_db.py list

# Restore from backup
python scripts/backup_db.py restore --file cluster_data_backup_20250920_003403.db

# Use custom backup directory
python scripts/backup_db.py backup --backup-dir /path/to/backups
```

### `detect_microk8s.py`
Detect and update MicroK8s status on nodes via SSH.

```bash
# Check specific node
python scripts/detect_microk8s.py --node-id 1

# Check all nodes
python scripts/detect_microk8s.py --all
```

### `update_node_status.py`
Manually update node MicroK8s status.

```bash
# Set MicroK8s status to running
python scripts/update_node_status.py 1 --status running

# Set status to stopped
python scripts/update_node_status.py 1 --status stopped
```

## Available Scripts

- `init_db.py` - Database initialization and recreation
- `backup_db.py` - Database backup and restore utilities
- `detect_microk8s.py` - Automatic MicroK8s status detection
- `update_node_status.py` - Manual node status updates
- `migrate_db.py` - Database migration utilities (planned)
- `cleanup_logs.py` - Log cleanup utilities (planned)
