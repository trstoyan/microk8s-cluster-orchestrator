# Playbook Editor Documentation

The MicroK8s Cluster Orchestrator includes a comprehensive visual playbook editor that allows you to create, manage, and execute Ansible playbooks without requiring deep YAML knowledge. This system provides a user-friendly interface for automating MicroK8s cluster operations.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Getting Started](#getting-started)
- [Visual Editor](#visual-editor)
- [Template Library](#template-library)
- [Target Selection](#target-selection)
- [Execution Engine](#execution-engine)
- [CLI Commands](#cli-commands)
- [API Reference](#api-reference)
- [Advanced Usage](#advanced-usage)
- [Troubleshooting](#troubleshooting)

## Overview

The Playbook Editor is a visual interface that allows users to:

- Build Ansible playbooks using a drag-and-drop interface
- Select from pre-built templates for common operations
- Target specific nodes, clusters, or custom groups
- Execute playbooks with real-time monitoring
- Manage a library of custom playbooks
- Track execution history and results

## Features

### Visual Interface
- **Drag-and-Drop Builder**: Build playbooks by dragging tasks from a library
- **Real-time YAML Preview**: See the generated Ansible YAML as you build
- **Task Configuration**: Interactive forms for configuring task parameters
- **Step Management**: Add, remove, and reorder playbook steps

### Template System
- **System Templates**: Pre-built templates for common MicroK8s operations
- **User Templates**: Create and share custom templates
- **Template Categories**: Organized by operation type (microk8s, system, monitoring)
- **Version Control**: Track template versions and usage statistics

### Target Selection
- **All Nodes**: Target every node in the system
- **Cluster-based**: Target specific clusters
- **Node Groups**: Custom groupings with dynamic criteria
- **Individual Nodes**: Precise node selection
- **Tag-based**: Target nodes with specific tags

### Execution Management
- **Background Execution**: Non-blocking playbook execution
- **Real-time Monitoring**: Live progress and output streaming
- **Status Tracking**: Pending, Running, Completed, Failed states
- **Error Handling**: Comprehensive error capture and reporting
- **Cancellation**: Stop running executions if needed

## Getting Started

### Accessing the Playbook Editor

1. **Web Interface**: Navigate to "Playbooks" in the main menu
2. **CLI**: Use `python cli.py playbook` commands
3. **API**: Access via REST endpoints

### Initial Setup

1. **Initialize System Templates**:
   ```bash
   python cli.py playbook init-templates
   # or
   make playbook-init
   ```

2. **Verify Installation**:
   ```bash
   python cli.py playbook list-templates
   ```

## Visual Editor

### Interface Layout

The visual editor consists of three main sections:

1. **Target Selection Sidebar**: Choose which nodes to target
2. **Task Library**: Available tasks organized by category
3. **Playbook Builder**: Drag-and-drop area for building playbooks

### Building a Playbook

1. **Select Targets**: Choose nodes, clusters, or groups from the sidebar
2. **Add Tasks**: Drag tasks from the library to the builder
3. **Configure Tasks**: Click "Configure" to set task parameters
4. **Preview YAML**: Switch to the YAML tab to see generated code
5. **Execute**: Run the playbook with real-time monitoring

### Task Categories

#### MicroK8s Operations
- **Install MicroK8s**: Complete installation with user setup
- **Enable Addons**: Common addons (DNS, Dashboard, Storage, etc.)
- **Join Cluster**: Add nodes to existing clusters
- **Configure HA**: High availability setup

#### System Operations
- **Update Packages**: System package management
- **Configure Firewall**: Security configuration
- **Install Packages**: Additional software installation
- **User Management**: Create and manage users

#### Monitoring
- **Health Check**: Comprehensive system health assessment
- **Collect Metrics**: Performance data gathering
- **Log Collection**: System log aggregation

## Template Library

### System Templates

The system includes several pre-built templates:

#### Install MicroK8s
```yaml
---
- name: Install MicroK8s
  hosts: all
  become: yes
  tasks:
    - name: Update package cache
      apt:
        update_cache: yes
      when: ansible_os_family == "Debian"
    
    - name: Install MicroK8s
      snap:
        name: microk8s
        classic: yes
    
    - name: Add user to microk8s group
      user:
        name: "{{ ansible_user }}"
        groups: microk8s
        append: yes
```

#### Enable MicroK8s Addons
```yaml
---
- name: Enable MicroK8s Addons
  hosts: all
  become: yes
  vars:
    addons:
      - dns
      - dashboard
      - storage
      - ingress
      - metrics-server
  tasks:
    - name: Enable MicroK8s addons
      shell: microk8s enable {{ item }}
      loop: "{{ addons }}"
```

#### System Health Check
```yaml
---
- name: System Health Check
  hosts: all
  become: yes
  tasks:
    - name: Check disk usage
      shell: df -h
      register: disk_usage
    
    - name: Check memory usage
      shell: free -h
      register: memory_usage
    
    - name: Check CPU load
      shell: uptime
      register: cpu_load
    
    - name: Check MicroK8s status
      shell: microk8s status
      register: microk8s_status
      ignore_errors: yes
```

### Creating Custom Templates

1. **Build Playbook**: Use the visual editor to create your playbook
2. **Save as Template**: Click "Save as Template" in the editor
3. **Configure Template**: Set name, description, category, and tags
4. **Share**: Make template public for team use

## Target Selection

### Target Types

#### All Nodes
Targets every node in the system:
```json
{"type": "all_nodes"}
```

#### Cluster-based
Targets all nodes in specific clusters:
```json
{"type": "cluster", "cluster_id": 1}
```

#### Node Groups
Targets nodes in custom groups:
```json
{"type": "node_group", "group_id": 1}
```

#### Individual Nodes
Targets specific nodes:
```json
{"type": "individual_nodes", "node_ids": [1, 2, 3]}
```

#### Tag-based
Targets nodes with specific tags:
```json
{"type": "tag", "tag": "production"}
```

### Node Groups

Node groups allow you to create custom groupings of nodes:

#### Group Types
- **Static**: Manual node selection
- **Dynamic**: Based on criteria (status, tags, etc.)
- **Cluster**: All nodes in a cluster
- **Tag**: Nodes with specific tags

#### Creating Groups
1. Navigate to "Node Groups" in the playbook section
2. Click "Create Group"
3. Set name, description, and type
4. Configure criteria or select nodes
5. Save the group

## Execution Engine

### Execution Process

1. **Validation**: Check YAML syntax and target availability
2. **Inventory Generation**: Create Ansible inventory from targets
3. **Background Execution**: Run Ansible in background thread
4. **Real-time Monitoring**: Stream output and update progress
5. **Result Capture**: Store execution results and logs

### Execution States

- **Pending**: Execution queued but not started
- **Running**: Currently executing
- **Completed**: Successfully finished
- **Failed**: Execution failed with errors
- **Cancelled**: Execution was cancelled

### Monitoring Features

- **Progress Tracking**: Visual progress indicators
- **Live Output**: Real-time log streaming
- **Error Highlighting**: Clear error messages and stack traces
- **Duration Tracking**: Execution time measurement
- **Result Summary**: Success/failure statistics

## CLI Commands

### Template Management
```bash
# List all templates
python cli.py playbook list-templates

# Show template details
python cli.py playbook show-template 1

# Initialize system templates
python cli.py playbook init-templates
```

### Custom Playbooks
```bash
# List custom playbooks
python cli.py playbook list-custom

# Show playbook details (via API)
curl -X GET http://localhost:5000/api/custom-playbooks/1
```

### Execution Management
```bash
# List executions
python cli.py playbook list-executions

# Show execution details
python cli.py playbook show-execution 1

# Cancel running execution (via API)
curl -X POST http://localhost:5000/api/playbook-executions/1/cancel
```

### Make Commands
```bash
# List templates
make playbook-templates

# Initialize system templates
make playbook-init

# List recent executions
make playbook-executions
```

## API Reference

### Templates

#### List Templates
```http
GET /api/playbook-templates
```

Query Parameters:
- `category`: Filter by category
- `is_public`: Filter by public/private status

#### Get Template
```http
GET /api/playbook-templates/{id}
```

#### Create Template
```http
POST /api/playbook-templates
```

Body:
```json
{
  "name": "Template Name",
  "description": "Template description",
  "category": "microk8s",
  "yaml_content": "---\n- name: Template\n  hosts: all\n  tasks: []",
  "variables_schema": "{}",
  "tags": "tag1,tag2",
  "is_public": true
}
```

### Custom Playbooks

#### List Playbooks
```http
GET /api/custom-playbooks
```

#### Create Playbook
```http
POST /api/custom-playbooks
```

Body:
```json
{
  "name": "My Playbook",
  "description": "Custom automation",
  "yaml_content": "---\n- name: My Playbook\n  hosts: all\n  tasks: []",
  "visual_config": "{}",
  "category": "custom",
  "tags": "tag1,tag2",
  "is_public": false
}
```

### Executions

#### List Executions
```http
GET /api/playbook-executions
```

Query Parameters:
- `status`: Filter by execution status

#### Execute Playbook
```http
POST /api/playbook-executions
```

Body:
```json
{
  "execution_name": "My Execution",
  "yaml_content": "---\n- name: My Playbook\n  hosts: all\n  tasks: []",
  "targets": [{"type": "all_nodes"}],
  "extra_vars": {"variable": "value"}
}
```

#### Get Execution
```http
GET /api/playbook-executions/{id}
```

#### Cancel Execution
```http
POST /api/playbook-executions/{id}/cancel
```

### Utilities

#### Validate YAML
```http
POST /api/playbooks/validate-yaml
```

Body:
```json
{
  "yaml_content": "---\n- name: Test\n  hosts: all\n  tasks: []"
}
```

#### Resolve Targets
```http
POST /api/playbooks/resolve-targets
```

Body:
```json
{
  "targets": [{"type": "all_nodes"}]
}
```

#### Generate Inventory
```http
POST /api/playbooks/generate-inventory
```

Body:
```json
{
  "node_ids": [1, 2, 3]
}
```

## Advanced Usage

### Custom Task Development

To add custom tasks to the task library:

1. **Extend Task Configurations**: Add new task types to the `getTaskConfig()` function
2. **Update YAML Generation**: Add corresponding YAML generators
3. **Create Templates**: Build templates using the new tasks

### Integration with Existing Playbooks

The playbook editor can work with existing Ansible playbooks:

1. **Import YAML**: Copy existing playbook YAML into the editor
2. **Convert to Visual**: Manually recreate the playbook using visual components
3. **Hybrid Approach**: Use visual editor for new sections, import existing YAML

### Automation and Scripting

Use the API for automation:

```bash
#!/bin/bash
# Automated playbook execution script

# Create playbook
PLAYBOOK_ID=$(curl -s -X POST http://localhost:5000/api/custom-playbooks \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Automated Setup",
    "yaml_content": "---\n- name: Setup\n  hosts: all\n  tasks: []"
  }' | jq -r '.id')

# Execute playbook
EXECUTION_ID=$(curl -s -X POST http://localhost:5000/api/playbook-executions \
  -H "Content-Type: application/json" \
  -d '{
    "execution_name": "Automated Execution",
    "yaml_content": "---\n- name: Setup\n  hosts: all\n  tasks: []",
    "targets": [{"type": "all_nodes"}]
  }' | jq -r '.id')

# Monitor execution
while true; do
  STATUS=$(curl -s http://localhost:5000/api/playbook-executions/$EXECUTION_ID | jq -r '.status')
  echo "Execution status: $STATUS"
  
  if [ "$STATUS" = "completed" ] || [ "$STATUS" = "failed" ]; then
    break
  fi
  
  sleep 5
done
```

## Troubleshooting

### Common Issues

#### Template Not Found
**Problem**: Template not appearing in the library
**Solution**: 
1. Check if templates are initialized: `python cli.py playbook list-templates`
2. Initialize templates: `python cli.py playbook init-templates`
3. Check database permissions and connectivity

#### Execution Fails
**Problem**: Playbook execution fails immediately
**Solution**:
1. Check YAML syntax: Use the validate endpoint
2. Verify target nodes are accessible
3. Check SSH connectivity to target nodes
4. Review execution logs for specific errors

#### YAML Generation Errors
**Problem**: Generated YAML is invalid
**Solution**:
1. Check task configurations in the visual editor
2. Verify all required parameters are set
3. Test YAML with the validate endpoint
4. Review task library configurations

#### Performance Issues
**Problem**: Editor is slow or unresponsive
**Solution**:
1. Check database performance
2. Reduce number of nodes in target selection
3. Clear browser cache
4. Check server resources

### Debug Mode

Enable debug mode for detailed logging:

```bash
# Start web interface with debug
python cli.py web --debug

# Check logs
tail -f logs/app.log
```

### Database Issues

If you encounter database-related issues:

```bash
# Check database status
python cli.py database path

# Validate models
python cli.py migrate status

# Recreate database (WARNING: This will delete all data)
rm cluster_data.db
python cli.py migrate run
python cli.py playbook init-templates
```

### API Debugging

Test API endpoints directly:

```bash
# Test health endpoint
curl -X GET http://localhost:5000/api/health

# Test template listing
curl -X GET http://localhost:5000/api/playbook-templates

# Test YAML validation
curl -X POST http://localhost:5000/api/playbooks/validate-yaml \
  -H "Content-Type: application/json" \
  -d '{"yaml_content": "---\n- name: Test\n  hosts: all\n  tasks: []"}'
```

## Best Practices

### Playbook Design
- **Keep it Simple**: Start with basic tasks and gradually add complexity
- **Use Templates**: Leverage existing templates as starting points
- **Test First**: Always test playbooks on a small subset of nodes
- **Document**: Add descriptions and tags to your playbooks

### Target Selection
- **Be Specific**: Use precise targeting to avoid unintended changes
- **Use Groups**: Create node groups for common targeting patterns
- **Test Connectivity**: Ensure SSH connectivity before execution
- **Consider Impact**: Understand the scope of changes before execution

### Execution Management
- **Monitor Progress**: Watch execution progress and logs
- **Handle Errors**: Review error messages and adjust playbooks
- **Keep History**: Maintain execution history for troubleshooting
- **Backup First**: Always backup critical systems before major changes

### Security
- **Limit Access**: Use proper user permissions and access controls
- **Validate Input**: Always validate playbook content before execution
- **Audit Trails**: Keep detailed logs of all operations
- **Secure Storage**: Protect playbook content and execution logs

## Support

For additional support:

1. **Check Documentation**: Review this guide and other documentation
2. **Review Logs**: Check application logs for error details
3. **Test Components**: Use CLI commands to test individual components
4. **Community**: Engage with the community for additional help

The Playbook Editor is designed to make Ansible automation accessible to users of all skill levels while maintaining the power and flexibility of the underlying Ansible system.
