# Cluster Graceful Shutdown Feature

## Overview

The Cluster Graceful Shutdown feature provides a comprehensive solution for safely shutting down MicroK8s clusters. This feature supports both graceful and force shutdown modes, with full integration across the web interface, CLI, and API.

## Features

### Graceful Shutdown
- **Safe Service Termination**: Stops all MicroK8s services in the correct order
- **Workload Protection**: Allows running workloads to finish gracefully
- **Timeout Handling**: Configurable timeout (default: 5 minutes)
- **Status Monitoring**: Real-time feedback on shutdown progress

### Force Shutdown
- **Immediate Termination**: Immediately stops all MicroK8s processes
- **Emergency Use**: For situations requiring immediate shutdown
- **Quick Response**: Shorter timeout (default: 1 minute)
- **Process Cleanup**: Kills any remaining MicroK8s processes

## Implementation

### Backend Components

#### 1. OrchestrationService.shutdown_cluster()
```python
def shutdown_cluster(self, cluster: Cluster, graceful: bool = True) -> Operation:
    """Gracefully shutdown a MicroK8s cluster."""
```
- Creates operation tracking
- Generates Ansible inventory
- Executes shutdown playbook
- Updates cluster and node statuses
- Provides comprehensive error handling

#### 2. API Endpoint
```python
@bp.route('/clusters/<int:cluster_id>/shutdown', methods=['POST'])
def shutdown_cluster(cluster_id):
```
- RESTful API for cluster shutdown
- Supports both graceful and force modes
- User authentication required
- Returns operation details

#### 3. Ansible Playbook: shutdown_cluster.yml
- **Service Management**: Stops MicroK8s services in proper order
- **Graceful Mode**: Disables services and waits for completion
- **Force Mode**: Immediately terminates processes
- **Cleanup**: Removes stale socket files and processes
- **Verification**: Confirms shutdown completion

### Frontend Components

#### 1. Web Interface Integration
- **Dropdown Menu**: Added to cluster actions dropdown
- **Two Options**: Graceful Shutdown and Force Shutdown
- **Confirmation Dialogs**: Different messages for each mode
- **Status Feedback**: Real-time operation progress

#### 2. JavaScript Functions
```javascript
function shutdownCluster(clusterId, clusterName, graceful)
```
- Handles user confirmation
- Makes API calls to shutdown endpoint
- Provides user feedback
- Refreshes page after operation starts

### CLI Integration

#### Command Structure
```bash
python cli.py cluster shutdown <cluster_id> [--graceful] [--force]
```

#### Options
- `--graceful`: Graceful shutdown (default)
- `--force`: Force shutdown (immediate termination)

#### Features
- Input validation
- Clear messaging for each shutdown type
- Operation tracking integration
- Error handling and user feedback

## Usage Examples

### Web Interface
1. Navigate to Clusters page
2. Click "Actions" dropdown for desired cluster
3. Select "Graceful Shutdown" or "Force Shutdown"
4. Confirm the action
5. Monitor progress in Operations page

### CLI Usage
```bash
# Graceful shutdown (default)
python cli.py cluster shutdown 1

# Explicit graceful shutdown
python cli.py cluster shutdown 1 --graceful

# Force shutdown
python cli.py cluster shutdown 1 --force
```

### API Usage
```bash
# Graceful shutdown
curl -X POST http://localhost:5000/api/clusters/1/shutdown \
  -H "Content-Type: application/json" \
  -d '{"graceful": true}'

# Force shutdown
curl -X POST http://localhost:5000/api/clusters/1/shutdown \
  -H "Content-Type: application/json" \
  -d '{"graceful": false}'
```

## Safety Features

### Graceful Shutdown Safety
- **Service Order**: Stops services in dependency order
- **Timeout Protection**: Prevents infinite waiting
- **Status Verification**: Confirms services are stopped
- **Cleanup**: Removes stale files and processes

### Force Shutdown Safety
- **Process Identification**: Only targets MicroK8s processes
- **Limited Scope**: Doesn't affect system services
- **Cleanup**: Removes MicroK8s-specific files
- **Verification**: Confirms shutdown completion

## Error Handling

### Common Scenarios
- **No Nodes**: Cluster has no assigned nodes
- **Service Errors**: MicroK8s services fail to stop
- **Timeout**: Shutdown exceeds timeout limit
- **Permission Issues**: Insufficient privileges

### Recovery
- **Operation Tracking**: All attempts are logged
- **Status Updates**: Cluster and node statuses reflect current state
- **Manual Recovery**: Users can manually restart services if needed

## Monitoring and Tracking

### Operation Tracking
- **Status Updates**: Running → Completed/Failed
- **Progress Monitoring**: Real-time status updates
- **Error Logging**: Detailed error messages
- **User Attribution**: Tracks who initiated shutdown

### Cluster Status
- **Status Field**: Updated to 'shutdown' on completion
- **Health Score**: Set to 0 when shutdown
- **Node Status**: Individual node statuses updated

## Integration Points

### Power Management
- Integrates with UPS power management system
- Can be triggered by power loss events
- Supports automated cluster shutdown

### Operations System
- Full integration with operation tracking
- Status monitoring and progress updates
- Historical operation records

### Web Interface
- Seamless integration with cluster management
- Consistent UI/UX with other operations
- Real-time status updates

## Future Enhancements

### Planned Features
- **Scheduled Shutdown**: Time-based shutdown scheduling
- **Conditional Shutdown**: Shutdown based on system conditions
- **Rolling Shutdown**: Gradual shutdown of cluster nodes
- **Backup Integration**: Automatic backup before shutdown

### Advanced Options
- **Custom Timeouts**: User-configurable shutdown timeouts
- **Service Prioritization**: Priority-based service shutdown
- **Health Checks**: Pre-shutdown health validation
- **Notification System**: Email/SMS notifications

## Testing

### Test Scenarios
1. **Normal Graceful Shutdown**: Standard cluster shutdown
2. **Force Shutdown**: Immediate termination
3. **Empty Cluster**: Cluster with no nodes
4. **Failed Services**: Services that won't stop
5. **Permission Issues**: Insufficient privileges
6. **Network Issues**: Remote node communication failures

### Validation
- **Service Status**: Verify all services are stopped
- **Process Cleanup**: Confirm no orphaned processes
- **File Cleanup**: Check for stale socket files
- **Status Updates**: Verify database status updates

## Security Considerations

### Access Control
- **Authentication Required**: All shutdown operations require login
- **User Attribution**: Operations are tied to authenticated users
- **Permission Validation**: Proper privilege checking

### Safety Measures
- **Confirmation Dialogs**: User confirmation required
- **Clear Messaging**: Different messages for graceful vs force
- **Operation Logging**: Complete audit trail
- **Rollback Capability**: Ability to restart after shutdown

## Conclusion

The Cluster Graceful Shutdown feature provides a comprehensive, safe, and user-friendly solution for shutting down MicroK8s clusters. With support for both graceful and force shutdown modes, full integration across all interfaces, and robust error handling, this feature ensures that cluster shutdown operations are reliable, trackable, and safe for production environments.
