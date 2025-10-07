"""Playbook service for managing playbook templates, custom playbooks, and executions."""

import json
import yaml
import tempfile
import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from flask import current_app
from sqlalchemy import and_, or_

from ..models.flask_models import (
    PlaybookTemplate, CustomPlaybook, PlaybookExecution, 
    NodeGroup, Node, Cluster, db
)


class PlaybookService:
    """Service for managing playbooks and their execution."""
    
    def __init__(self):
        self.temp_dir = Path(tempfile.gettempdir()) / "microk8s_playbooks"
        self.temp_dir.mkdir(exist_ok=True)
    
    # Template Management
    def create_template(self, name: str, description: str, category: str, 
                       yaml_content: str, variables_schema: str = None,
                       tags: str = None, is_public: bool = True, 
                       created_by: int = None) -> PlaybookTemplate:
        """Create a new playbook template."""
        template = PlaybookTemplate(
            name=name,
            description=description,
            category=category,
            yaml_content=yaml_content,
            variables_schema=variables_schema,
            tags=tags,
            is_public=is_public,
            created_by=created_by
        )
        
        db.session.add(template)
        db.session.commit()
        return template
    
    def get_templates(self, category: str = None, is_public: bool = None) -> List[PlaybookTemplate]:
        """Get playbook templates with optional filtering."""
        query = PlaybookTemplate.query
        
        if category:
            query = query.filter(PlaybookTemplate.category == category)
        if is_public is not None:
            query = query.filter(PlaybookTemplate.is_public == is_public)
        
        return query.order_by(PlaybookTemplate.name).all()
    
    def get_template(self, template_id: int) -> Optional[PlaybookTemplate]:
        """Get a specific playbook template."""
        return PlaybookTemplate.query.get(template_id)
    
    def update_template(self, template_id: int, **kwargs) -> Optional[PlaybookTemplate]:
        """Update a playbook template."""
        template = PlaybookTemplate.query.get(template_id)
        if not template:
            return None
        
        for key, value in kwargs.items():
            if hasattr(template, key):
                setattr(template, key, value)
        
        template.updated_at = datetime.utcnow()
        db.session.commit()
        return template
    
    def delete_template(self, template_id: int) -> bool:
        """Delete a playbook template (only if not system template)."""
        template = PlaybookTemplate.query.get(template_id)
        if not template or template.is_system:
            return False
        
        db.session.delete(template)
        db.session.commit()
        return True
    
    # Custom Playbook Management
    def create_custom_playbook(self, name: str, description: str, yaml_content: str,
                              visual_config: str = None, category: str = 'custom',
                              tags: str = None, is_public: bool = False,
                              created_by: int = None) -> CustomPlaybook:
        """Create a new custom playbook."""
        playbook = CustomPlaybook(
            name=name,
            description=description,
            yaml_content=yaml_content,
            visual_config=visual_config,
            category=category,
            tags=tags,
            is_public=is_public,
            created_by=created_by
        )
        
        db.session.add(playbook)
        db.session.commit()
        return playbook
    
    def get_custom_playbooks(self, created_by: int = None, is_public: bool = None) -> List[CustomPlaybook]:
        """Get custom playbooks with optional filtering."""
        query = CustomPlaybook.query
        
        if created_by:
            query = query.filter(CustomPlaybook.created_by == created_by)
        if is_public is not None:
            query = query.filter(CustomPlaybook.is_public == is_public)
        
        return query.order_by(CustomPlaybook.name).all()
    
    def get_custom_playbook(self, playbook_id: int) -> Optional[CustomPlaybook]:
        """Get a specific custom playbook."""
        return CustomPlaybook.query.get(playbook_id)
    
    def update_custom_playbook(self, playbook_id: int, **kwargs) -> Optional[CustomPlaybook]:
        """Update a custom playbook."""
        playbook = CustomPlaybook.query.get(playbook_id)
        if not playbook:
            return None
        
        for key, value in kwargs.items():
            if hasattr(playbook, key):
                setattr(playbook, key, value)
        
        playbook.updated_at = datetime.utcnow()
        db.session.commit()
        return playbook
    
    def delete_custom_playbook(self, playbook_id: int) -> bool:
        """Delete a custom playbook."""
        playbook = CustomPlaybook.query.get(playbook_id)
        if not playbook:
            return False
        
        db.session.delete(playbook)
        db.session.commit()
        return True
    
    # Node Group Management
    def create_node_group(self, name: str, description: str, group_type: str,
                         criteria: str = None, tags: str = None,
                         created_by: int = None) -> NodeGroup:
        """Create a new node group."""
        group = NodeGroup(
            name=name,
            description=description,
            group_type=group_type,
            criteria=criteria,
            tags=tags,
            created_by=created_by
        )
        
        db.session.add(group)
        db.session.commit()
        return group
    
    def get_node_groups(self, created_by: int = None) -> List[NodeGroup]:
        """Get node groups with optional filtering."""
        query = NodeGroup.query
        
        if created_by:
            query = query.filter(NodeGroup.created_by == created_by)
        
        return query.order_by(NodeGroup.name).all()
    
    def get_node_group(self, group_id: int) -> Optional[NodeGroup]:
        """Get a specific node group."""
        return NodeGroup.query.get(group_id)
    
    def update_node_group(self, group_id: int, **kwargs) -> Optional[NodeGroup]:
        """Update a node group."""
        group = NodeGroup.query.get(group_id)
        if not group:
            return None
        
        for key, value in kwargs.items():
            if hasattr(group, key):
                setattr(group, key, value)
        
        group.updated_at = datetime.utcnow()
        db.session.commit()
        return group
    
    def delete_node_group(self, group_id: int) -> bool:
        """Delete a node group."""
        group = NodeGroup.query.get(group_id)
        if not group or group.is_system:
            return False
        
        db.session.delete(group)
        db.session.commit()
        return True
    
    def resolve_targets(self, targets: List[Dict[str, Any]]) -> List[Node]:
        """Resolve target specifications to actual nodes."""
        resolved_nodes = []
        
        for target in targets:
            target_type = target.get('type')
            
            if target_type == 'all_nodes':
                nodes = Node.query.all()
                resolved_nodes.extend(nodes)
            
            elif target_type == 'cluster':
                cluster_id = target.get('cluster_id')
                if cluster_id:
                    cluster = Cluster.query.get(cluster_id)
                    if cluster:
                        resolved_nodes.extend(cluster.nodes)
            
            elif target_type == 'node_group':
                group_id = target.get('group_id')
                if group_id:
                    group = NodeGroup.query.get(group_id)
                    if group:
                        resolved_nodes.extend(group.nodes)
            
            elif target_type == 'individual_nodes':
                node_ids = target.get('node_ids', [])
                nodes = Node.query.filter(Node.id.in_(node_ids)).all()
                resolved_nodes.extend(nodes)
            
            elif target_type == 'tag':
                tag = target.get('tag')
                if tag:
                    nodes = Node.query.filter(Node.tags.contains(tag)).all()
                    resolved_nodes.extend(nodes)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_nodes = []
        for node in resolved_nodes:
            if node.id not in seen:
                seen.add(node.id)
                unique_nodes.append(node)
        
        return unique_nodes
    
    def generate_inventory(self, nodes: List[Node]) -> str:
        """Generate Ansible inventory from nodes."""
        inventory = {
            'all': {
                'hosts': {},
                'vars': {}
            }
        }
        
        for node in nodes:
            host_vars = {
                'ansible_host': node.ip_address,
                'ansible_user': node.ssh_user,
                'ansible_port': node.ssh_port,
                'ansible_ssh_private_key_file': node.ssh_key_path,
                'hostname': node.hostname,
                'microk8s_status': node.microk8s_status,
                'is_control_plane': node.is_control_plane
            }
            
            if node.cluster_id:
                host_vars['cluster_id'] = node.cluster_id
                cluster = Cluster.query.get(node.cluster_id)
                if cluster:
                    host_vars['cluster_name'] = cluster.name
            
            inventory['all']['hosts'][node.hostname] = host_vars
        
        return yaml.dump(inventory, default_flow_style=False)
    
    def validate_yaml(self, yaml_content: str) -> Tuple[bool, str]:
        """Validate YAML content."""
        try:
            yaml.safe_load(yaml_content)
            return True, "Valid YAML"
        except yaml.YAMLError as e:
            return False, f"Invalid YAML: {str(e)}"
    
    def execute_playbook(self, execution_name: str, yaml_content: str, 
                        targets: List[Dict[str, Any]], extra_vars: Dict[str, Any] = None,
                        created_by: int = None) -> PlaybookExecution:
        """Execute a playbook."""
        # Create execution record
        execution = PlaybookExecution(
            execution_name=execution_name,
            execution_type='custom',
            targets=json.dumps(targets),
            yaml_content=yaml_content,
            extra_vars=json.dumps(extra_vars) if extra_vars else None,
            status='pending',
            created_by=created_by
        )
        
        db.session.add(execution)
        db.session.commit()
        
        # Start execution in background thread
        thread = threading.Thread(
            target=self._execute_playbook_thread,
            args=(execution.id,)
        )
        thread.daemon = True
        thread.start()
        
        return execution
    
    def _execute_playbook_thread(self, execution_id: int):
        """Execute playbook in background thread."""
        execution = PlaybookExecution.query.get(execution_id)
        if not execution:
            return
        
        try:
            # Update status to running
            execution.status = 'running'
            execution.started_at = datetime.utcnow()
            db.session.commit()
            
            # Resolve targets
            targets = json.loads(execution.targets)
            nodes = self.resolve_targets(targets)
            
            if not nodes:
                execution.status = 'failed'
                execution.error_message = "No nodes found for the specified targets"
                execution.completed_at = datetime.utcnow()
                db.session.commit()
                return
            
            # Generate inventory
            inventory_content = self.generate_inventory(nodes)
            execution.inventory_content = inventory_content
            
            # Create temporary files
            playbook_file = self.temp_dir / f"playbook_{execution_id}.yml"
            inventory_file = self.temp_dir / f"inventory_{execution_id}.yml"
            
            # Write files
            playbook_file.write_text(execution.yaml_content)
            inventory_file.write_text(inventory_content)
            
            # Prepare Ansible command
            cmd = [
                'ansible-playbook',
                '-i', str(inventory_file),
                str(playbook_file)
            ]
            
            # Add extra variables
            if execution.extra_vars:
                extra_vars = json.loads(execution.extra_vars)
                for key, value in extra_vars.items():
                    cmd.extend(['-e', f'{key}={value}'])
            
            # Execute Ansible
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            output_lines = []
            while True:
                line = process.stdout.readline()
                if not line and process.poll() is not None:
                    break
                if line:
                    output_lines.append(line)
                    # Update progress (simplified)
                    if 'PLAY' in line or 'TASK' in line:
                        execution.progress_percent = min(execution.progress_percent + 5, 95)
                        db.session.commit()
            
            # Get return code
            return_code = process.poll()
            
            # Update execution with results
            execution.output = ''.join(output_lines)
            execution.completed_at = datetime.utcnow()
            execution.success = return_code == 0
            
            if return_code == 0:
                execution.status = 'completed'
            else:
                execution.status = 'failed'
                execution.error_message = f"Ansible playbook failed with return code {return_code}"
            
            # Clean up temporary files
            try:
                playbook_file.unlink()
                inventory_file.unlink()
            except:
                pass
            
            db.session.commit()
            
        except Exception as e:
            execution.status = 'failed'
            execution.error_message = str(e)
            execution.completed_at = datetime.utcnow()
            db.session.commit()
    
    def get_executions(self, created_by: int = None, status: str = None) -> List[PlaybookExecution]:
        """Get playbook executions with optional filtering."""
        query = PlaybookExecution.query
        
        if created_by:
            query = query.filter(PlaybookExecution.created_by == created_by)
        if status:
            query = query.filter(PlaybookExecution.status == status)
        
        return query.order_by(PlaybookExecution.created_at.desc()).all()
    
    def get_execution(self, execution_id: int) -> Optional[PlaybookExecution]:
        """Get a specific playbook execution."""
        return PlaybookExecution.query.get(execution_id)
    
    def cancel_execution(self, execution_id: int) -> bool:
        """Cancel a running playbook execution."""
        execution = PlaybookExecution.query.get(execution_id)
        if not execution or execution.status != 'running':
            return False
        
        execution.status = 'cancelled'
        execution.completed_at = datetime.utcnow()
        db.session.commit()
        return True
    
    # System Templates
    def create_system_templates(self):
        """Create default system templates."""
        templates = [
            {
                'name': 'Install MicroK8s',
                'description': 'Install MicroK8s on target nodes',
                'category': 'microk8s',
                'yaml_content': '''---
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
    
    - name: Wait for MicroK8s to be ready
      wait_for:
        port: 16443
        host: "{{ ansible_host }}"
        timeout: 300
      ignore_errors: yes
''',
                'variables_schema': json.dumps({
                    'type': 'object',
                    'properties': {},
                    'required': []
                }),
                'tags': 'microk8s,install,system',
                'is_system': True
            },
            {
                'name': 'Enable MicroK8s Addons',
                'description': 'Enable common MicroK8s addons',
                'category': 'microk8s',
                'yaml_content': '''---
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
      register: addon_results
    
    - name: Display addon enablement results
      debug:
        var: addon_results
''',
                'variables_schema': json.dumps({
                    'type': 'object',
                    'properties': {
                        'addons': {
                            'type': 'array',
                            'items': {'type': 'string'},
                            'default': ['dns', 'dashboard', 'storage', 'ingress', 'metrics-server'],
                            'description': 'List of addons to enable'
                        }
                    },
                    'required': []
                }),
                'tags': 'microk8s,addons,configuration',
                'is_system': True
            },
            {
                'name': 'System Health Check',
                'description': 'Perform comprehensive system health check',
                'category': 'monitoring',
                'yaml_content': '''---
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
    
    - name: Display system information
      debug:
        msg: |
          Disk Usage:
          {{ disk_usage.stdout }}
          
          Memory Usage:
          {{ memory_usage.stdout }}
          
          CPU Load:
          {{ cpu_load.stdout }}
          
          MicroK8s Status:
          {{ microk8s_status.stdout if microk8s_status.rc == 0 else 'MicroK8s not installed or not running' }}
''',
                'variables_schema': json.dumps({
                    'type': 'object',
                    'properties': {},
                    'required': []
                }),
                'tags': 'monitoring,health,system',
                'is_system': True
            }
        ]
        
        for template_data in templates:
            # Check if template already exists
            existing = PlaybookTemplate.query.filter_by(
                name=template_data['name'],
                is_system=True
            ).first()
            
            if not existing:
                template = PlaybookTemplate(**template_data)
                db.session.add(template)
        
        db.session.commit()
