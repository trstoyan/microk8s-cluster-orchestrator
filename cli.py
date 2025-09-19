#!/usr/bin/env python3
"""
MicroK8s Cluster Orchestrator CLI

A comprehensive tool for managing MicroK8s clusters using Ansible automation.
"""

import click
import os
import sys
import json
from datetime import datetime
from tabulate import tabulate
from colorama import init, Fore, Style

# Add app directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.models.database import get_session, init_database
from app.models.node import Node
from app.models.cluster import Cluster
from app.models.operation import Operation
from app.models.router_switch import RouterSwitch
from app.services.cli_orchestrator import CLIOrchestrationService
from app.utils.config import config

# Initialize colorama for colored output
init(autoreset=True)

def print_success(message):
    """Print success message in green."""
    click.echo(f"{Fore.GREEN}✓ {message}{Style.RESET_ALL}")

def print_error(message):
    """Print error message in red."""
    click.echo(f"{Fore.RED}✗ {message}{Style.RESET_ALL}")

def print_warning(message):
    """Print warning message in yellow."""
    click.echo(f"{Fore.YELLOW}⚠ {message}{Style.RESET_ALL}")

def print_info(message):
    """Print info message in blue."""
    click.echo(f"{Fore.BLUE}ℹ {message}{Style.RESET_ALL}")

@click.group()
@click.option('--config-file', '-c', help='Configuration file path')
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
@click.pass_context
def cli(ctx, config_file, verbose):
    """MicroK8s Cluster Orchestrator - Manage MicroK8s clusters with ease."""
    ctx.ensure_object(dict)
    ctx.obj['verbose'] = verbose
    
    if config_file:
        config.config_file = config_file
        config.load_config()
    
    # Initialize database
    init_database()

@cli.group()
def node():
    """Manage cluster nodes."""
    pass

@node.command('list')
@click.option('--format', '-f', type=click.Choice(['table', 'json']), default='table', help='Output format')
def list_nodes(format):
    """List all nodes."""
    session = get_session()
    try:
        nodes = session.query(Node).all()
        
        if format == 'json':
            click.echo(json.dumps([node.to_dict() for node in nodes], indent=2))
        else:
            if not nodes:
                print_info("No nodes found.")
                return
            
            headers = ['ID', 'Hostname', 'IP Address', 'Status', 'MicroK8s', 'Cluster', 'Last Seen']
            rows = []
            
            for node in nodes:
                cluster_name = node.cluster.name if node.cluster else 'None'
                last_seen = node.last_seen.strftime('%Y-%m-%d %H:%M') if node.last_seen else 'Never'
                
                rows.append([
                    node.id,
                    node.hostname,
                    node.ip_address,
                    node.status,
                    node.microk8s_status,
                    cluster_name,
                    last_seen
                ])
            
            click.echo(tabulate(rows, headers=headers, tablefmt='grid'))
    
    finally:
        session.close()

@node.command('add')
@click.option('--hostname', '-h', required=True, help='Node hostname')
@click.option('--ip', '-i', required=True, help='Node IP address')
@click.option('--user', '-u', default='ubuntu', help='SSH user')
@click.option('--port', '-p', default=22, help='SSH port')
@click.option('--key-path', '-k', help='SSH private key path')
@click.option('--cluster-id', type=int, help='Cluster ID to assign node to')
@click.option('--notes', help='Additional notes')
def add_node(hostname, ip, user, port, key_path, cluster_id, notes):
    """Add a new node."""
    session = get_session()
    try:
        # Check if node already exists
        existing = session.query(Node).filter_by(hostname=hostname).first()
        if existing:
            print_error(f"Node with hostname '{hostname}' already exists.")
            return
        
        # Validate cluster if specified
        if cluster_id:
            cluster = session.query(Cluster).filter_by(id=cluster_id).first()
            if not cluster:
                print_error(f"Cluster with ID {cluster_id} not found.")
                return
        
        node = Node(
            hostname=hostname,
            ip_address=ip,
            ssh_user=user,
            ssh_port=port,
            ssh_key_path=key_path,
            cluster_id=cluster_id,
            notes=notes
        )
        
        session.add(node)
        session.commit()
        
        print_success(f"Node '{hostname}' added successfully with ID {node.id}.")
    
    except Exception as e:
        session.rollback()
        print_error(f"Failed to add node: {e}")
    
    finally:
        session.close()

@node.command('remove')
@click.argument('node_id', type=int)
@click.option('--force', is_flag=True, help='Force removal without confirmation')
def remove_node(node_id, force):
    """Remove a node."""
    session = get_session()
    try:
        node = session.query(Node).filter_by(id=node_id).first()
        if not node:
            print_error(f"Node with ID {node_id} not found.")
            return
        
        if not force:
            if not click.confirm(f"Are you sure you want to remove node '{node.hostname}'?"):
                print_info("Operation cancelled.")
                return
        
        session.delete(node)
        session.commit()
        
        print_success(f"Node '{node.hostname}' removed successfully.")
    
    except Exception as e:
        session.rollback()
        print_error(f"Failed to remove node: {e}")
    
    finally:
        session.close()

@node.command('status')
@click.argument('node_id', type=int)
def check_node_status(node_id):
    """Check node status."""
    session = get_session()
    orchestrator = CLIOrchestrationService()
    
    try:
        node = session.query(Node).filter_by(id=node_id).first()
        if not node:
            print_error(f"Node with ID {node_id} not found.")
            return
        
        print_info(f"Checking status of node '{node.hostname}'...")
        operation = orchestrator.check_node_status(node)
        
        print_info(f"Operation started with ID {operation.id}")
        print_info("Check the operations list for results.")
    
    except Exception as e:
        print_error(f"Failed to check node status: {e}")
    
    finally:
        session.close()

@node.command('install')
@click.argument('node_id', type=int)
def install_microk8s(node_id):
    """Install MicroK8s on a node."""
    session = get_session()
    orchestrator = CLIOrchestrationService()
    
    try:
        node = session.query(Node).filter_by(id=node_id).first()
        if not node:
            print_error(f"Node with ID {node_id} not found.")
            return
        
        print_info(f"Installing MicroK8s on node '{node.hostname}'...")
        operation = orchestrator.install_microk8s(node)
        
        print_info(f"Installation started with operation ID {operation.id}")
        print_info("Check the operations list for progress.")
    
    except Exception as e:
        print_error(f"Failed to start installation: {e}")
    
    finally:
        session.close()

@cli.group()
def cluster():
    """Manage clusters."""
    pass

@cluster.command('list')
@click.option('--format', '-f', type=click.Choice(['table', 'json']), default='table', help='Output format')
def list_clusters(format):
    """List all clusters."""
    session = get_session()
    try:
        clusters = session.query(Cluster).all()
        
        if format == 'json':
            click.echo(json.dumps([cluster.to_dict() for cluster in clusters], indent=2))
        else:
            if not clusters:
                print_info("No clusters found.")
                return
            
            headers = ['ID', 'Name', 'Status', 'Nodes', 'Control Planes', 'Workers', 'HA', 'Created']
            rows = []
            
            for cluster in clusters:
                created = cluster.created_at.strftime('%Y-%m-%d') if cluster.created_at else 'Unknown'
                
                rows.append([
                    cluster.id,
                    cluster.name,
                    cluster.status,
                    cluster.node_count,
                    cluster.control_plane_count,
                    cluster.worker_count,
                    'Yes' if cluster.ha_enabled else 'No',
                    created
                ])
            
            click.echo(tabulate(rows, headers=headers, tablefmt='grid'))
    
    finally:
        session.close()

@cluster.command('add')
@click.option('--name', '-n', required=True, help='Cluster name')
@click.option('--description', '-d', help='Cluster description')
@click.option('--ha', is_flag=True, help='Enable high availability')
@click.option('--network-cidr', default='10.1.0.0/16', help='Network CIDR')
@click.option('--service-cidr', default='10.152.183.0/24', help='Service CIDR')
def add_cluster(name, description, ha, network_cidr, service_cidr):
    """Add a new cluster."""
    session = get_session()
    try:
        # Check if cluster already exists
        existing = session.query(Cluster).filter_by(name=name).first()
        if existing:
            print_error(f"Cluster with name '{name}' already exists.")
            return
        
        cluster = Cluster(
            name=name,
            description=description,
            ha_enabled=ha,
            network_cidr=network_cidr,
            service_cidr=service_cidr
        )
        
        session.add(cluster)
        session.commit()
        
        print_success(f"Cluster '{name}' added successfully with ID {cluster.id}.")
    
    except Exception as e:
        session.rollback()
        print_error(f"Failed to add cluster: {e}")
    
    finally:
        session.close()

@cluster.command('setup')
@click.argument('cluster_id', type=int)
def setup_cluster(cluster_id):
    """Setup a cluster."""
    session = get_session()
    orchestrator = CLIOrchestrationService()
    
    try:
        cluster = session.query(Cluster).filter_by(id=cluster_id).first()
        if not cluster:
            print_error(f"Cluster with ID {cluster_id} not found.")
            return
        
        if not cluster.nodes:
            print_error(f"Cluster '{cluster.name}' has no nodes assigned.")
            return
        
        print_info(f"Setting up cluster '{cluster.name}'...")
        operation = orchestrator.setup_cluster(cluster)
        
        print_info(f"Cluster setup started with operation ID {operation.id}")
        print_info("Check the operations list for progress.")
    
    except Exception as e:
        print_error(f"Failed to setup cluster: {e}")
    
    finally:
        session.close()

@cli.group()
def router():
    """Manage router switches."""
    pass

@router.command('list')
@click.option('--format', '-f', type=click.Choice(['table', 'json']), default='table', help='Output format')
def list_router_switches(format):
    """List all router switches."""
    session = get_session()
    try:
        router_switches = session.query(RouterSwitch).all()
        
        if format == 'json':
            click.echo(json.dumps([rs.to_dict() for rs in router_switches], indent=2))
        else:
            if not router_switches:
                print_info("No router switches found.")
                return
            
            headers = ['ID', 'Hostname', 'IP', 'Type', 'Model', 'Status', 'Health', 'Uptime', 'Location']
            rows = []
            
            for rs in router_switches:
                uptime = f"{rs.uptime_days}d {rs.uptime_hours}h" if rs.uptime_days > 0 else f"{rs.uptime_hours}h"
                
                rows.append([
                    rs.id,
                    rs.hostname,
                    rs.ip_address,
                    rs.device_type.title(),
                    rs.model or 'Unknown',
                    rs.status,
                    f"{rs.health_score}%",
                    uptime,
                    rs.location or '-'
                ])
            
            click.echo(tabulate(rows, headers=headers, tablefmt='grid'))
    
    finally:
        session.close()

@router.command('add')
@click.option('--hostname', '-h', required=True, help='Router hostname')
@click.option('--ip', '-i', required=True, help='Router IP address')
@click.option('--device-type', '-t', default='mikrotik', help='Device type (mikrotik, cisco, ubiquiti, etc.)')
@click.option('--model', '-m', help='Device model')
@click.option('--serial', '-s', help='Serial number')
@click.option('--mac', help='MAC address')
@click.option('--port', '-p', default=22, help='Management port')
@click.option('--cluster-id', type=int, help='Associated cluster ID')
@click.option('--location', help='Physical location')
@click.option('--contact', help='Contact person')
@click.option('--notes', help='Additional notes')
def add_router_switch(hostname, ip, device_type, model, serial, mac, port, cluster_id, location, contact, notes):
    """Add a new router switch."""
    session = get_session()
    try:
        # Check if router switch already exists
        existing = session.query(RouterSwitch).filter_by(hostname=hostname).first()
        if existing:
            print_error(f"Router switch with hostname '{hostname}' already exists.")
            return
        
        router_switch = RouterSwitch(
            hostname=hostname,
            ip_address=ip,
            device_type=device_type,
            model=model,
            serial_number=serial,
            mac_address=mac,
            management_port=port,
            cluster_id=cluster_id,
            location=location,
            contact_person=contact,
            notes=notes
        )
        
        session.add(router_switch)
        session.commit()
        
        print_success(f"Router switch '{hostname}' added successfully with ID {router_switch.id}.")
    
    except Exception as e:
        session.rollback()
        print_error(f"Failed to add router switch: {e}")
    
    finally:
        session.close()

@router.command('remove')
@click.argument('router_switch_id', type=int)
@click.option('--force', is_flag=True, help='Force removal without confirmation')
def remove_router_switch(router_switch_id, force):
    """Remove a router switch."""
    session = get_session()
    try:
        router_switch = session.query(RouterSwitch).filter_by(id=router_switch_id).first()
        if not router_switch:
            print_error(f"Router switch with ID {router_switch_id} not found.")
            return
        
        if not force:
            if not click.confirm(f"Are you sure you want to remove router switch '{router_switch.hostname}'?"):
                print_info("Operation cancelled.")
                return
        
        session.delete(router_switch)
        session.commit()
        
        print_success(f"Router switch '{router_switch.hostname}' removed successfully.")
    
    except Exception as e:
        session.rollback()
        print_error(f"Failed to remove router switch: {e}")
    
    finally:
        session.close()

@router.command('status')
@click.argument('router_switch_id', type=int)
def check_router_status(router_switch_id):
    """Check router switch status."""
    session = get_session()
    orchestrator = CLIOrchestrationService()
    
    try:
        router_switch = session.query(RouterSwitch).filter_by(id=router_switch_id).first()
        if not router_switch:
            print_error(f"Router switch with ID {router_switch_id} not found.")
            return
        
        print_info(f"Checking status of router switch '{router_switch.hostname}'...")
        operation = orchestrator.check_router_status(router_switch)
        
        print_info(f"Status check started with operation ID {operation.id}")
        print_info("Check the operations list for results.")
    
    except Exception as e:
        print_error(f"Failed to check router status: {e}")
    
    finally:
        session.close()

@router.command('backup')
@click.argument('router_switch_id', type=int)
def backup_router_config(router_switch_id):
    """Backup router switch configuration."""
    session = get_session()
    orchestrator = CLIOrchestrationService()
    
    try:
        router_switch = session.query(RouterSwitch).filter_by(id=router_switch_id).first()
        if not router_switch:
            print_error(f"Router switch with ID {router_switch_id} not found.")
            return
        
        print_info(f"Backing up configuration for router switch '{router_switch.hostname}'...")
        operation = orchestrator.backup_router_config(router_switch)
        
        print_info(f"Backup started with operation ID {operation.id}")
        print_info("Check the operations list for results.")
    
    except Exception as e:
        print_error(f"Failed to start backup: {e}")
    
    finally:
        session.close()

@router.command('update-firmware')
@click.argument('router_switch_id', type=int)
@click.option('--version', help='Specific firmware version to install (default: latest)')
def update_router_firmware(router_switch_id, version):
    """Update router switch firmware."""
    session = get_session()
    orchestrator = CLIOrchestrationService()
    
    try:
        router_switch = session.query(RouterSwitch).filter_by(id=router_switch_id).first()
        if not router_switch:
            print_error(f"Router switch with ID {router_switch_id} not found.")
            return
        
        target_version = version if version else "latest"
        print_info(f"Updating firmware for router switch '{router_switch.hostname}' to {target_version}...")
        operation = orchestrator.update_router_firmware(router_switch, version)
        
        print_info(f"Firmware update started with operation ID {operation.id}")
        print_info("Check the operations list for progress.")
        print_warning("Note: The device will reboot after firmware update.")
    
    except Exception as e:
        print_error(f"Failed to start firmware update: {e}")
    
    finally:
        session.close()

@router.command('restore')
@click.argument('router_switch_id', type=int)
@click.argument('backup_path', type=click.Path(exists=True))
def restore_router_config(router_switch_id, backup_path):
    """Restore router switch configuration from backup."""
    session = get_session()
    orchestrator = CLIOrchestrationService()
    
    try:
        router_switch = session.query(RouterSwitch).filter_by(id=router_switch_id).first()
        if not router_switch:
            print_error(f"Router switch with ID {router_switch_id} not found.")
            return
        
        print_info(f"Restoring configuration for router switch '{router_switch.hostname}' from {backup_path}...")
        operation = orchestrator.restore_router_config(router_switch, backup_path)
        
        print_info(f"Configuration restore started with operation ID {operation.id}")
        print_info("Check the operations list for progress.")
        print_warning("Note: The device will reboot after configuration restore.")
    
    except Exception as e:
        print_error(f"Failed to start configuration restore: {e}")
    
    finally:
        session.close()

@router.command('show')
@click.argument('router_switch_id', type=int)
def show_router_switch(router_switch_id):
    """Show router switch details."""
    session = get_session()
    try:
        router_switch = session.query(RouterSwitch).filter_by(id=router_switch_id).first()
        if not router_switch:
            print_error(f"Router switch with ID {router_switch_id} not found.")
            return
        
        click.echo(f"\n{Fore.CYAN}Router Switch Details:{Style.RESET_ALL}")
        click.echo(f"ID: {router_switch.id}")
        click.echo(f"Hostname: {router_switch.hostname}")
        click.echo(f"IP Address: {router_switch.ip_address}")
        click.echo(f"Device Type: {router_switch.device_type}")
        click.echo(f"Model: {router_switch.model or 'Unknown'}")
        click.echo(f"Serial Number: {router_switch.serial_number or 'Unknown'}")
        click.echo(f"MAC Address: {router_switch.mac_address or 'Unknown'}")
        click.echo(f"Management Port: {router_switch.management_port}")
        click.echo(f"Status: {router_switch.status}")
        click.echo(f"Health Score: {router_switch.health_score}%")
        click.echo(f"Uptime: {router_switch.uptime_days} days, {router_switch.uptime_hours} hours")
        click.echo(f"Last Seen: {router_switch.last_seen}")
        click.echo(f"Location: {router_switch.location or 'Not specified'}")
        click.echo(f"Contact Person: {router_switch.contact_person or 'Not specified'}")
        
        if router_switch.firmware_version:
            click.echo(f"Firmware Version: {router_switch.firmware_version}")
        if router_switch.routeros_version:
            click.echo(f"RouterOS Version: {router_switch.routeros_version}")
        if router_switch.cpu_model:
            click.echo(f"CPU Model: {router_switch.cpu_model}")
        if router_switch.total_memory_mb:
            click.echo(f"Total Memory: {router_switch.total_memory_mb} MB")
        if router_switch.port_count:
            click.echo(f"Port Count: {router_switch.port_count}")
        
        if router_switch.notes:
            click.echo(f"\n{Fore.CYAN}Notes:{Style.RESET_ALL}")
            click.echo(router_switch.notes)
        
        if router_switch.tags:
            click.echo(f"\n{Fore.CYAN}Tags:{Style.RESET_ALL}")
            click.echo(router_switch.tags)
    
    finally:
        session.close()

@cli.group()
def operation():
    """Manage operations."""
    pass

@operation.command('list')
@click.option('--limit', '-l', default=20, help='Limit number of results')
@click.option('--status', help='Filter by status')
@click.option('--format', '-f', type=click.Choice(['table', 'json']), default='table', help='Output format')
def list_operations(limit, status, format):
    """List operations."""
    session = get_session()
    try:
        query = session.query(Operation).order_by(Operation.created_at.desc())
        
        if status:
            query = query.filter_by(status=status)
        
        operations = query.limit(limit).all()
        
        if format == 'json':
            click.echo(json.dumps([op.to_dict() for op in operations], indent=2))
        else:
            if not operations:
                print_info("No operations found.")
                return
            
            headers = ['ID', 'Type', 'Name', 'Target', 'Status', 'Success', 'Duration', 'Created']
            rows = []
            
            for op in operations:
                if op.node:
                    target = f"Node {op.node.hostname}"
                elif op.cluster:
                    target = f"Cluster {op.cluster.name}"
                elif op.router_switch:
                    target = f"Router {op.router_switch.hostname}"
                else:
                    target = "Unknown"
                
                created = op.created_at.strftime('%Y-%m-%d %H:%M') if op.created_at else 'Unknown'
                duration = f"{op.duration:.1f}s" if op.duration else 'N/A'
                success = '✓' if op.success else ('✗' if op.success is False else '-')
                
                rows.append([
                    op.id,
                    op.operation_type,
                    op.operation_name,
                    target,
                    op.status,
                    success,
                    duration,
                    created
                ])
            
            click.echo(tabulate(rows, headers=headers, tablefmt='grid'))
    
    finally:
        session.close()

@operation.command('show')
@click.argument('operation_id', type=int)
def show_operation(operation_id):
    """Show operation details."""
    session = get_session()
    try:
        operation = session.query(Operation).filter_by(id=operation_id).first()
        if not operation:
            print_error(f"Operation with ID {operation_id} not found.")
            return
        
        click.echo(f"\n{Fore.CYAN}Operation Details:{Style.RESET_ALL}")
        click.echo(f"ID: {operation.id}")
        click.echo(f"Type: {operation.operation_type}")
        click.echo(f"Name: {operation.operation_name}")
        click.echo(f"Description: {operation.description or 'N/A'}")
        click.echo(f"Status: {operation.status}")
        click.echo(f"Success: {'Yes' if operation.success else ('No' if operation.success is False else 'Pending')}")
        
        if operation.node:
            click.echo(f"Target Node: {operation.node.hostname} ({operation.node.ip_address})")
        elif operation.cluster:
            click.echo(f"Target Cluster: {operation.cluster.name}")
        elif operation.router_switch:
            click.echo(f"Target Router Switch: {operation.router_switch.hostname} ({operation.router_switch.ip_address})")
        
        click.echo(f"Created: {operation.created_at}")
        click.echo(f"Started: {operation.started_at or 'Not started'}")
        click.echo(f"Completed: {operation.completed_at or 'Not completed'}")
        
        if operation.duration:
            click.echo(f"Duration: {operation.duration:.1f} seconds")
        
        if operation.output:
            click.echo(f"\n{Fore.CYAN}Output:{Style.RESET_ALL}")
            click.echo(operation.output)
        
        if operation.error_message:
            click.echo(f"\n{Fore.RED}Error:{Style.RESET_ALL}")
            click.echo(operation.error_message)
    
    finally:
        session.close()

@cli.command('web')
@click.option('--host', default='0.0.0.0', help='Host to bind to')
@click.option('--port', default=5000, help='Port to bind to')
@click.option('--debug', is_flag=True, help='Enable debug mode')
def start_web(host, port, debug):
    """Start the web interface."""
    try:
        from app import create_app
        
        app = create_app()
        print_info(f"Starting web interface on http://{host}:{port}")
        app.run(host=host, port=port, debug=debug)
    
    except ImportError as e:
        print_error(f"Failed to import Flask app: {e}")
        print_info("Make sure Flask and other web dependencies are installed.")

@cli.command('init')
@click.option('--force', is_flag=True, help='Force initialization even if database exists')
def init_system(force):
    """Initialize the orchestrator system."""
    try:
        # Create directories
        directories = ['logs', 'ansible/inventory', 'config']
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
            print_success(f"Created directory: {directory}")
        
        # Initialize database using the proper script
        import subprocess
        script_path = os.path.join(os.path.dirname(__file__), 'scripts', 'init_db.py')
        if force or not os.path.exists(config.get('database.path', 'cluster_data.db')):
            cmd = [sys.executable, script_path]
            if force:
                cmd.append('--force')
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                print_success("Database initialized.")
            else:
                print_error(f"Database initialization failed: {result.stderr}")
        else:
            print_warning("Database already exists. Use --force to reinitialize.")
        
        # Create sample configuration if it doesn't exist
        config_file = 'config/local.yml'
        if not os.path.exists(config_file):
            config.save_config(config_file)
            print_success(f"Created configuration file: {config_file}")
        
        print_success("System initialization completed!")
        print_info("You can now add nodes and clusters using the CLI commands.")
        print_info("Run 'python cli.py web' to start the web interface.")
    
    except Exception as e:
        print_error(f"Failed to initialize system: {e}")

if __name__ == '__main__':
    cli()
