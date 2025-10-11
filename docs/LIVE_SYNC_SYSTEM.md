# Live Sync System Documentation

## 🔄 Overview

The Live Sync System allows you to securely synchronize data between multiple MicroK8s Orchestrator instances in real-time. Transfer nodes, clusters, SSH keys, and configurations between servers without downtime.

## ✨ Features

- **Live Transfer**: Sync while servers are running (no downtime required)
- **Encrypted Communication**: AES-256 encryption with optional password protection
- **Selective Sync**: Choose exactly what to transfer
- **Diff Comparison**: See differences before syncing
- **Conflict Detection**: Identifies and handles data conflicts
- **Web Interface**: Interactive UI for easy management
- **CLI Support**: Automate sync operations via command line
- **Real-time Progress**: Track sync status live

## 🏗️ Architecture

```
┌─────────────────┐         Encrypted API         ┌─────────────────┐
│   Server 1      │◄──────────────────────────────►│   Server 2      │
│  (Source)       │    HTTPS + Token Auth         │  (Target)       │
│                 │                                │                 │
│ ┌─────────────┐ │                                │ ┌─────────────┐ │
│ │   Web UI    │ │  1. Connect & Authenticate     │ │  API Server │ │
│ │   Compare   │ │  2. Fetch metadata from both   │ │  /api/v1/   │ │
│ │   Select    │ │  3. Show diff table            │ │  sync/*     │ │
│ └─────────────┘ │  4. User selects items         │ └─────────────┘ │
│                 │  5. Stream transfer encrypted  │                 │
└─────────────────┘  6. Verify & apply changes     └─────────────────┘
```

## 🚀 Quick Start

### 1. Prerequisites

Both servers must:
- Be running the MicroK8s Orchestrator web interface
- Have network connectivity to each other
- Be using the same version of the orchestrator

### 2. Using Web Interface

```bash
# On Server 1 (already running)
# Navigate to: http://localhost:5000/sync/interactive

# Or use make command:
make sync-interactive
```

**Steps:**
1. Enter remote server URL (e.g., `https://server2:5000`)
2. Optional: Enter encryption password
3. Click "Connect & Compare"
4. Review the differences
5. Select items to sync
6. Click "Start Sync"

### 3. Using Make Commands

```bash
# Test connection to remote server
make sync-connect URL=https://server2:5000

# Open interactive sync interface
make sync-interactive

# Full workflow (test + open interface)
make sync-full URL=https://server2:5000
```

### 4. Using API Directly

```bash
# Test sync API
curl http://localhost:5000/api/v1/sync/test

# Connect and get token
curl -X POST http://localhost:5000/api/v1/sync/connect \
  -H "Content-Type: application/json" \
  -d '{"server_id": "server1", "password": "optional_password"}'

# Get inventory (requires token)
curl -X GET http://localhost:5000/api/v1/sync/inventory \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## 📋 Syncable Items

### Nodes
- Hostname, IP address, username
- SSH configuration
- MicroK8s installation status
- Wake-on-LAN settings
- Hardware information

### Clusters
- Name and description
- HA configuration
- Node assignments
- Cluster settings

### SSH Keys
- Public/private key pairs
- Fingerprints
- Key names and paths
- **Note**: Keys are encrypted during transfer

### Configurations
- YAML configuration files
- Playbook templates
- Custom settings

## 🔐 Security

### Encryption

The sync system uses multiple layers of security:

1. **Transport Encryption**: All API calls use HTTPS (in production)
2. **Data Encryption**: AES-256 encryption for sensitive data
3. **Token Authentication**: JWT-style tokens for API access
4. **Password Protection**: Optional password for additional security

### Token Management

Tokens are:
- Generated per sync session
- Valid for 1 hour by default
- Automatically revoked after use
- Stored in memory (not persisted)

### Best Practices

1. **Use HTTPS in Production**
   ```bash
   # Set up reverse proxy with SSL
   # Or use gunicorn with SSL certificates
   ```

2. **Use Strong Passwords**
   ```bash
   # Provide encryption password for sensitive data
   make sync-full URL=https://server2:5000 PASSWORD=your-strong-password
   ```

3. **Restrict Network Access**
   ```bash
   # Use firewall rules to limit sync API access
   sudo ufw allow from 192.168.1.0/24 to any port 5000
   ```

4. **Rotate Tokens Regularly**
   - Tokens auto-expire after 1 hour
   - Each sync session gets a new token
   - Old tokens are automatically invalidated

## 🔄 Sync Workflow

### Step 1: Connection & Authentication

```
Server 1 → POST /api/v1/sync/connect → Server 2
       ← Token + Session ID
```

### Step 2: Inventory Collection

```
Server 1 → GET /api/v1/sync/inventory → Server 2
       ← Remote inventory data
```

### Step 3: Comparison

```
Server 1 compares local and remote inventories
Identifies:
  - Identical items
  - Different items
  - Missing items (on remote)
  - Missing items (on local)
```

### Step 4: Selection

```
User reviews comparison results
Selects items to sync:
  ☑ Node: webserver-01
  ☑ Cluster: production
  ☐ Node: db-server-01 (skip)
```

### Step 5: Transfer

```
Server 1 → POST /api/v1/sync/transfer → Server 2
       Package:
         - Encrypted data
         - Selected items
         - Checksums
       
Server 2 validates and applies changes
       ← Success/Failure status
```

### Step 6: Verification

```
Both servers verify:
  - Data integrity (checksums)
  - Database constraints
  - No data loss
```

## 📊 Comparison Results

### Status Types

| Status | Icon | Description |
|--------|------|-------------|
| Identical | 🟢 | Item exists on both servers with same data |
| Different | 🟡 | Item exists on both but has different values |
| Missing on Remote | 🔵 | Item exists locally but not on remote |
| Missing on Local | ⚪ | Item exists on remote but not locally |
| Conflict | 🔴 | Item has conflicting changes on both sides |

### Example Comparison

```
Nodes:
  ✅ node-01 (192.168.1.10) - Identical
  ⚠️  node-02 (192.168.1.11) - Different IP: 192.168.1.11 → 192.168.1.12
  ➕ node-03 (192.168.1.13) - Missing on remote
  
Clusters:
  ✅ production - Identical
  ⚠️  staging - Different: 2 nodes → 3 nodes
```

## 🛠️ API Reference

### Endpoints

#### POST `/api/v1/sync/connect`
Establish sync connection

**Request:**
```json
{
  "server_id": "unique_server_identifier",
  "password": "optional_encryption_password"
}
```

**Response:**
```json
{
  "success": true,
  "token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "session_id": "abc123...",
  "expires_in": 3600,
  "server_info": {
    "name": "MicroK8s Orchestrator",
    "version": "1.0.0"
  }
}
```

#### GET `/api/v1/sync/inventory`
Get server inventory

**Headers:**
```
Authorization: Bearer <token>
```

**Response:**
```json
{
  "success": true,
  "inventory": {
    "metadata": {...},
    "nodes": [...],
    "clusters": [...],
    "ssh_keys": [...],
    "stats": {...}
  }
}
```

#### POST `/api/v1/sync/compare`
Compare inventories

**Request:**
```json
{
  "remote_inventory": {...}
}
```

**Response:**
```json
{
  "success": true,
  "comparison": {
    "summary": {...},
    "nodes": {
      "identical": [...],
      "different": [...],
      "missing_on_remote": [...],
      "missing_on_local": [...]
    },
    "clusters": {...}
  }
}
```

#### POST `/api/v1/sync/transfer`
Create transfer package

**Request:**
```json
{
  "session_id": "abc123",
  "items": {
    "nodes": [...],
    "clusters": [...]
  },
  "encrypted": true
}
```

**Response:**
```json
{
  "success": true,
  "package": {
    "payload": "encrypted_base64_data",
    "salt": "base64_salt"
  }
}
```

#### POST `/api/v1/sync/receive`
Receive and apply package

**Request:**
```json
{
  "session_id": "abc123",
  "package": {...},
  "encrypted": true
}
```

**Response:**
```json
{
  "success": true,
  "applied": {
    "nodes": 3,
    "clusters": 1,
    "ssh_keys": 2
  },
  "errors": []
}
```

## 🐛 Troubleshooting

### Connection Issues

**Problem**: Cannot connect to remote server

**Solutions**:
1. Check network connectivity: `ping remote-server`
2. Verify server is running: `curl http://remote-server:5000/api/v1/sync/test`
3. Check firewall rules: `sudo ufw status`
4. Verify URL format: Use `http://` or `https://` prefix

### Authentication Errors

**Problem**: Invalid or expired token

**Solutions**:
1. Tokens expire after 1 hour - reconnect
2. Each sync session needs a new token
3. Check system time is synchronized (NTP)

### Transfer Failures

**Problem**: Sync fails midway

**Solutions**:
1. Check database locks: No other operations running
2. Verify disk space: `df -h`
3. Check logs: `tail -f logs/production.log`
4. Retry with smaller batches

### Encryption Issues

**Problem**: Decryption fails

**Solutions**:
1. Ensure same password on both servers
2. Check cryptography library version: `pip show cryptography`
3. Verify Python version compatibility

## 🔧 Configuration

### Environment Variables

```bash
# Set default remote URL
export SYNC_REMOTE_URL="https://remote-server:5000"

# Set encryption password
export SYNC_PASSWORD="your-secret-password"

# Set token expiration (seconds)
export SYNC_TOKEN_EXPIRY=3600
```

### Config File

Add to `config/local.yml`:

```yaml
sync:
  enabled: true
  default_remote_url: "https://remote-server:5000"
  token_expiry: 3600
  encryption:
    enabled: true
    algorithm: "AES-256"
  rate_limiting:
    enabled: true
    max_requests_per_hour: 100
```

## 📈 Performance

### Transfer Speed

- **Small datasets** (<100 items): ~1-2 seconds
- **Medium datasets** (100-1000 items): ~5-10 seconds
- **Large datasets** (1000+ items): ~30-60 seconds

### Optimization Tips

1. **Selective Sync**: Only sync what's needed
2. **Batch Processing**: Group related items
3. **Network**: Use wired connection for large transfers
4. **Compression**: Enable gzip for large payloads (coming soon)

## 🔄 Use Cases

### 1. Server Migration

```bash
# Scenario: Migrate all data from old to new server

# Step 1: Connect to new server
make sync-connect URL=https://new-server:5000

# Step 2: Open interactive interface
make sync-interactive

# Step 3: Select all items and sync
# (Use web interface)
```

### 2. Backup & Restore

```bash
# Create backup on secondary server
make sync-full URL=https://backup-server:5000

# Select all items to create complete backup
```

### 3. Development → Production

```bash
# Sync specific clusters from dev to prod
# Use web interface to select only production cluster
make sync-interactive
```

### 4. Multi-Site Sync

```bash
# Sync between data centers
# Server A ← → Server B ← → Server C
```

## 🚧 Limitations

### Current Limitations

1. **No Conflict Resolution**: Manual intervention required for conflicts
2. **No Delta Sync**: Transfers full items, not just changes
3. **No Compression**: Large datasets transfer uncompressed
4. **No Scheduling**: No automatic/scheduled sync (yet)
5. **No Bidirectional**: One-way sync (source → target)

### Planned Features

- [ ] Bidirectional sync
- [ ] Automatic conflict resolution
- [ ] Scheduled sync jobs
- [ ] Compression support
- [ ] Incremental sync (delta updates)
- [ ] Sync history and rollback
- [ ] Multi-server sync (broadcast)

## 📚 Examples

### Example 1: Basic Sync

```bash
# Terminal 1: Start Server 1
cd server1
make prod-start

# Terminal 2: Start Server 2
cd server2
make prod-start

# Terminal 3: Sync from Server 1 to Server 2
cd server1
make sync-full URL=http://localhost:5001
```

### Example 2: Encrypted Sync

```python
# Using Python API
from app.services.sync_service import SyncService
from app.utils.encryption import SyncEncryption

# Initialize with encryption
sync = SyncService(
    remote_url="https://server2:5000",
    api_token="your_token"
)
sync.encryption = SyncEncryption("strong-password")

# Create encrypted package
package = sync.create_sync_package({
    'nodes': [node1, node2],
    'clusters': [cluster1]
})
```

### Example 3: Custom Selection

```javascript
// Web interface JavaScript
const selectedItems = {
    nodes: [
        nodeData.find(n => n.hostname === 'webserver-01'),
        nodeData.find(n => n.hostname === 'dbserver-01')
    ],
    clusters: [
        clusterData.find(c => c.name === 'production')
    ]
};

fetch('/sync/transfer', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
        remote_url: remoteUrl,
        selected_items: selectedItems
    })
});
```

## 🔗 Related Documentation

- [Production Deployment](PRODUCTION_DEPLOYMENT.md)
- [API Documentation](../README.md#api-reference)
- [Security Guide](SECURITY.md)
- [Troubleshooting](../README.md#troubleshooting)

## 📝 Summary

The Live Sync System provides a secure, efficient way to synchronize data between MicroK8s Orchestrator instances:

✅ **Secure**: AES-256 encryption + token authentication  
✅ **Flexible**: Web UI + CLI + API  
✅ **Selective**: Choose exactly what to sync  
✅ **Live**: No downtime required  
✅ **Visual**: See differences before syncing  

**Quick Command Reference:**
```bash
make sync-test              # Test sync API
make sync-connect URL=...   # Test connection
make sync-interactive       # Open web UI
make sync-full URL=...      # Complete workflow
```

For support, open an issue on GitHub or check the troubleshooting section above.

