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

try:
    from tabulate import tabulate
except ImportError:
    def tabulate(data, headers=None, tablefmt="grid"):
        """Fallback tabulate function for when tabulate is not installed."""
        if not data:
            return ""
        
        if headers:
            # Simple table formatting
            result = []
            # Add headers
            result.append(" | ".join(str(h) for h in headers))
            result.append("-" * len(result[0]))
            
            # Add data rows
            for row in data:
                result.append(" | ".join(str(cell) for cell in row))
            
            return "\n".join(result)
        else:
            # Simple key-value formatting
            result = []
            for row in data:
                if len(row) >= 2:
                    result.append(f"{row[0]}: {row[1]}")
            return "\n".join(result)
try:
    from colorama import init, Fore, Style
    init()  # Initialize colorama
except ImportError:
    # Fallback if colorama is not available
    class Fore:
        RED = ''
        GREEN = ''
        YELLOW = ''
        BLUE = ''
        RESET = ''
    
    class Style:
        RESET_ALL = ''
    
    def init():
        pass

# Add app directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.models.database import get_session, init_database
from app.models.flask_models import Node, Cluster, Operation, RouterSwitch
from app.models.network_lease import NetworkLease, NetworkInterface
from app.services.cli_orchestrator import CLIOrchestrationService
from app.utils.config import config

# Colorama is already initialized above if available

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
    
    # Run any pending migrations
    try:
        from app.utils.migration_manager import MigrationManager
        manager = MigrationManager()
        success, messages = manager.run_all_pending_migrations()
        
        if not success:
            print_warning("Some migrations failed. The application may not work correctly.")
            for message in messages:
                if "failed" in message.lower() or "error" in message.lower():
                    print_error(message)
                else:
                    print_info(message)
        elif messages and "No pending migrations" not in messages[0]:
            print_success("Database migrations completed successfully!")
    except Exception as e:
        print_warning(f"Failed to run migrations: {e}")
        print_info("Continuing with application startup...")

@cli.group()
def database():
    """Database management commands."""
    pass

@database.command('path')
def show_database_path():
    """Show the path to the database file."""
    from app.utils.config import config
    import os
    
    db_path = config.get('database.path', 'cluster_data.db')
    abs_path = os.path.abspath(db_path)
    
    print(f"Database path: {abs_path}")
    print(f"Database exists: {'Yes' if os.path.exists(abs_path) else 'No'}")
    
    if os.path.exists(abs_path):
        size = os.path.getsize(abs_path)
        print(f"Database size: {size:,} bytes ({size/1024/1024:.2f} MB)")

@cli.group()
def migrate():
    """Manage database migrations."""
    pass

@migrate.command('run')
@click.option('--dry-run', is_flag=True, help='Show what would be run without executing')
def run_migrations(dry_run):
    """Run all pending database migrations."""
    try:
        from app.utils.migration_manager import MigrationManager
        
        manager = MigrationManager()
        success, messages = manager.run_all_pending_migrations(dry_run)
        
        for message in messages:
            if success:
                print_success(message)
            elif "failed" in message.lower() or "error" in message.lower():
                print_error(message)
            else:
                print_info(message)
        
        if not dry_run and success:
            print_success("Database migrations completed successfully!")
        elif not dry_run:
            print_error("Some migrations failed. Check the output above for details.")
            
    except Exception as e:
        print_error(f"Failed to run migrations: {e}")

@migrate.command('status')
def migration_status():
    """Show current migration status."""
    try:
        from app.utils.migration_manager import MigrationManager
        
        manager = MigrationManager()
        status = manager.get_migration_status()
        
        print_info("Migration Status:")
        print_info(f"  Database exists: {status['database_exists']}")
        print_info(f"  Migrations table exists: {status['migrations_table_exists']}")
        print_info(f"  Applied migrations: {len(status['applied_migrations'])}")
        print_info(f"  Pending migrations: {len(status['pending_migrations'])}")
        print_info(f"  Total migrations: {status['total_migrations']}")
        print_info(f"  Status: {status['status']}")
        
        if status['applied_migrations']:
            print_info("\nApplied migrations:")
            for migration in status['applied_migrations']:
                print_success(f"  ✓ {migration}")
        
        if status['pending_migrations']:
            print_info("\nPending migrations:")
            for migration in status['pending_migrations']:
                print_warning(f"  ⏳ {migration}")
                
    except Exception as e:
        print_error(f"Failed to get migration status: {e}")

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
@click.option('--cluster-id', type=int, help='Cluster ID to assign node to')
@click.option('--notes', help='Additional notes')
@click.option('--generate-ssh-key', is_flag=True, default=True, help='Generate SSH key pair (default: True)')
def add_node(hostname, ip, user, port, cluster_id, notes, generate_ssh_key):
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
        
        # Create the node first
        node = Node(
            hostname=hostname,
            ip_address=ip,
            ssh_user=user,
            ssh_port=port,
            cluster_id=cluster_id,
            notes=notes
        )
        
        session.add(node)
        session.flush()  # Get the node ID
        
        # Generate SSH key pair if requested
        if generate_ssh_key:
            try:
                from app.services.ssh_key_manager import SSHKeyManager
                ssh_manager = SSHKeyManager()
                
                print_info(f"Generating SSH key pair for node '{hostname}'...")
                key_info = ssh_manager.generate_key_pair(node.id, node.hostname)
                
                # Update node with SSH key information
                node.ssh_key_path = key_info['private_key_path']
                node.ssh_public_key = key_info['public_key']
                node.ssh_key_fingerprint = key_info['fingerprint']
                node.ssh_key_generated = True
                node.ssh_key_status = 'generated'
                
                # Generate setup instructions
                instructions = ssh_manager.get_setup_instructions(
                    node.hostname, 
                    key_info['public_key'],
                    node.ssh_user
                )
                node.ssh_setup_instructions = instructions
                
                print_success(f"SSH key pair generated successfully.")
                print_info(f"Private key: {key_info['private_key_path']}")
                print_info(f"Public key: {key_info['public_key_path']}")
                print_info(f"Fingerprint: {key_info['fingerprint']}")
                
            except Exception as key_error:
                session.rollback()
                print_error(f"Failed to generate SSH key: {key_error}")
                return
        
        session.commit()
        
        print_success(f"Node '{hostname}' added successfully with ID {node.id}.")
        
        if generate_ssh_key:
            print_info("\n" + "="*60)
            print_info("SSH KEY SETUP INSTRUCTIONS")
            print_info("="*60)
            print_info(instructions)
            print_info("="*60)
            print_info("After completing the setup, test the connection with:")
            print_info(f"  microk8s-cluster node test-ssh {node.id}")
    
    except Exception as e:
        session.rollback()
        print_error(f"Failed to add node: {e}")
    
    finally:
        session.close()

@node.command('update')
@click.argument('node_id', type=int)
@click.option('--hostname', '-h', help='Update node hostname')
@click.option('--ip', '-i', help='Update node IP address')
@click.option('--ssh-user', '-u', help='Update SSH username')
@click.option('--ssh-port', '-p', type=int, help='Update SSH port')
@click.option('--cluster-id', '-c', type=int, help='Update cluster assignment (use 0 to remove from cluster)')
@click.option('--tags', '-t', help='Update node tags (comma-separated)')
@click.option('--notes', '-n', help='Update node notes')
def update_node(node_id, hostname, ip, ssh_user, ssh_port, cluster_id, tags, notes):
    """Update node details."""
    session = get_session()
    try:
        node = session.query(Node).filter_by(id=node_id).first()
        if not node:
            print_error(f"Node with ID {node_id} not found.")
            return
        
        print_info(f"Updating node: {node.hostname} (ID: {node_id})")
        
        # Update fields if provided
        if hostname:
            old_hostname = node.hostname
            node.hostname = hostname
            print_info(f"  - Hostname: {old_hostname} → {hostname}")
        
        if ip:
            old_ip = node.ip_address
            node.ip_address = ip
            print_info(f"  - IP Address: {old_ip} → {ip}")
        
        if ssh_user:
            old_user = node.ssh_user
            node.ssh_user = ssh_user
            print_info(f"  - SSH User: {old_user} → {ssh_user}")
        
        if ssh_port:
            old_port = node.ssh_port
            node.ssh_port = ssh_port
            print_info(f"  - SSH Port: {old_port} → {ssh_port}")
        
        if cluster_id is not None:
            old_cluster = node.cluster.name if node.cluster else 'None'
            if cluster_id == 0:
                node.cluster_id = None
                new_cluster = 'None'
            else:
                cluster = session.query(Cluster).filter_by(id=cluster_id).first()
                if not cluster:
                    print_error(f"Cluster with ID {cluster_id} not found.")
                    return
                node.cluster_id = cluster_id
                new_cluster = cluster.name
            print_info(f"  - Cluster: {old_cluster} → {new_cluster}")
        
        if tags is not None:
            old_tags = node.tags or 'None'
            node.tags = tags
            print_info(f"  - Tags: {old_tags} → {tags}")
        
        if notes is not None:
            old_notes = node.notes or 'None'
            node.notes = notes
            print_info(f"  - Notes: {old_notes} → {notes}")
        
        # Update timestamp
        node.updated_at = datetime.utcnow()
        
        session.commit()
        print_success(f"Node '{node.hostname}' updated successfully!")
        
    except Exception as e:
        session.rollback()
        print_error(f"Failed to update node: {e}")
    
    finally:
        session.close()

@node.command('test-ssh')
@click.argument('node_id', type=int)
def test_ssh_connection(node_id):
    """Test SSH connection to a node."""
    session = get_session()
    try:
        node = session.query(Node).filter_by(id=node_id).first()
        if not node:
            print_error(f"Node with ID {node_id} not found.")
            return
        
        if not node.ssh_key_ready:
            print_error("SSH key not ready for testing.")
            return
        
        print_info(f"Testing SSH connection to node '{node.hostname}' ({node.ip_address})...")
        
        from app.services.ssh_key_manager import SSHKeyManager
        ssh_manager = SSHKeyManager()
        
        test_result = ssh_manager.validate_ssh_connection(
            node.hostname,
            node.ip_address,
            node.ssh_user,
            node.ssh_port,
            node.ssh_key_path
        )
        
        # Update node with test results
        import json
        node.ssh_connection_tested = True
        node.ssh_connection_test_result = json.dumps(test_result)
        
        if test_result['success']:
            node.ssh_key_status = 'tested'
            print_success("SSH connection test successful!")
            print_info(f"SSH connection: {'✓' if test_result['ssh_connection'] else '✗'}")
            print_info(f"Sudo access: {'✓' if test_result['sudo_access'] else '✗'}")
            print_info("Node is ready for cluster operations.")
        else:
            node.ssh_key_status = 'failed'
            print_error("SSH connection test failed!")
            print_error(f"Error: {test_result.get('message', 'Unknown error')}")
        
        session.commit()
        
    except Exception as e:
        session.rollback()
        print_error(f"Error testing SSH connection: {e}")
    
    finally:
        session.close()

@node.command('regenerate-ssh-key')
@click.argument('node_id', type=int)
@click.option('--force', is_flag=True, help='Force regeneration without confirmation')
def regenerate_ssh_key(node_id, force):
    """Regenerate SSH key for a node."""
    session = get_session()
    try:
        node = session.query(Node).filter_by(id=node_id).first()
        if not node:
            print_error(f"Node with ID {node_id} not found.")
            return
        
        if not force:
            if not click.confirm(f"Regenerate SSH key for node '{node.hostname}'? This will invalidate the current key."):
                print_info("Operation cancelled.")
                return
        
        print_info(f"Regenerating SSH key for node '{node.hostname}'...")
        
        from app.services.ssh_key_manager import SSHKeyManager
        ssh_manager = SSHKeyManager()
        
        # Clean up existing key if it exists
        if node.ssh_key_path:
            ssh_manager.cleanup_key_pair(node.ssh_key_path)
        
        # Generate new key pair
        key_info = ssh_manager.generate_key_pair(node.id, node.hostname)
        
        # Update node with new SSH key information
        node.ssh_key_path = key_info['private_key_path']
        node.ssh_public_key = key_info['public_key']
        node.ssh_key_fingerprint = key_info['fingerprint']
        node.ssh_key_generated = True
        node.ssh_key_status = 'generated'
        node.ssh_connection_tested = False
        node.ssh_connection_test_result = None
        
        # Generate new setup instructions
        instructions = ssh_manager.get_setup_instructions(
            node.hostname, 
            key_info['public_key'],
            node.ssh_user
        )
        node.ssh_setup_instructions = instructions
        
        session.commit()
        
        print_success("SSH key regenerated successfully!")
        print_info(f"Private key: {key_info['private_key_path']}")
        print_info(f"Public key: {key_info['public_key_path']}")
        print_info(f"Fingerprint: {key_info['fingerprint']}")
        print_info("\n" + "="*60)
        print_info("NEW SSH KEY SETUP INSTRUCTIONS")
        print_info("="*60)
        print_info(instructions)
        print_info("="*60)
        
    except Exception as e:
        session.rollback()
        print_error(f"Error regenerating SSH key: {e}")
    
    finally:
        session.close()

@node.command('ssh-status')
@click.argument('node_id', type=int)
def show_ssh_status(node_id):
    """Show SSH key status for a node."""
    session = get_session()
    try:
        node = session.query(Node).filter_by(id=node_id).first()
        if not node:
            print_error(f"Node with ID {node_id} not found.")
            return
        
        print_info(f"SSH Key Status for Node '{node.hostname}'")
        print_info("="*50)
        print_info(f"Hostname: {node.hostname}")
        print_info(f"IP Address: {node.ip_address}")
        print_info(f"SSH User: {node.ssh_user}")
        print_info(f"SSH Port: {node.ssh_port}")
        print_info(f"Key Generated: {'✓' if node.ssh_key_generated else '✗'}")
        print_info(f"Key Status: {node.ssh_key_status}")
        print_info(f"Connection Tested: {'✓' if node.ssh_connection_tested else '✗'}")
        print_info(f"Connection Ready: {'✓' if node.ssh_connection_ready else '✗'}")
        
        if node.ssh_key_fingerprint:
            print_info(f"Fingerprint: {node.ssh_key_fingerprint}")
        
        if node.ssh_key_path:
            print_info(f"Private Key: {node.ssh_key_path}")
        
        if node.ssh_connection_test_result:
            import json
            try:
                test_result = json.loads(node.ssh_connection_test_result)
                print_info("\nLast Connection Test Result:")
                print_info(f"  Success: {'✓' if test_result.get('success') else '✗'}")
                print_info(f"  SSH Connection: {'✓' if test_result.get('ssh_connection') else '✗'}")
                print_info(f"  Sudo Access: {'✓' if test_result.get('sudo_access') else '✗'}")
                if not test_result.get('success'):
                    print_info(f"  Error: {test_result.get('message', 'Unknown error')}")
            except json.JSONDecodeError:
                print_info(f"Test Result: {node.ssh_connection_test_result}")
        
        print_info(f"\nStatus Description: {node.get_ssh_status_description()}")
        
    except Exception as e:
        print_error(f"Error showing SSH status: {e}")
    
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

@cluster.command('configure-hosts')
@click.argument('cluster_id', type=int)
@click.option('--backup', is_flag=True, default=True, help='Backup original /etc/hosts file (default: True)')
def configure_hosts_file(cluster_id, backup):
    """Configure /etc/hosts file on all cluster nodes for proper hostname resolution."""
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
        
        print_info(f"Configuring /etc/hosts file for cluster '{cluster.name}'...")
        print_info(f"Nodes to configure: {len(cluster.nodes)}")
        
        # Display nodes that will be configured
        print_info("Cluster nodes:")
        for node in cluster.nodes:
            print_info(f"  - {node.hostname} ({node.ip_address})")
        
        if backup:
            print_info("Original /etc/hosts files will be backed up before modification.")
        
        # Confirm before proceeding
        if not click.confirm("Do you want to proceed with /etc/hosts configuration?"):
            print_info("Operation cancelled.")
            return
        
        operation = orchestrator.configure_hosts_file(cluster)
        
        print_info(f"Hosts file configuration started with operation ID {operation.id}")
        print_info("Check the operations list for progress.")
        print_info("This operation will:")
        print_info("  - Backup original /etc/hosts files")
        print_info("  - Add hostname-to-IP mappings for all cluster nodes")
        print_info("  - Verify hostname resolution works correctly")
        print_info("  - Test DNS resolution for all nodes")
    
    except Exception as e:
        print_error(f"Failed to configure hosts file: {e}")
    
    finally:
        session.close()

@node.command('configure-hosts')
@click.option('--backup', is_flag=True, default=True, help='Backup original /etc/hosts file (default: True)')
def configure_all_nodes_hosts(backup):
    """Configure /etc/hosts file on all nodes for proper hostname resolution."""
    session = get_session()
    orchestrator = CLIOrchestrationService()
    
    try:
        nodes = session.query(Node).all()
        
        if not nodes:
            print_error("No nodes found to configure.")
            return
        
        print_info(f"Configuring /etc/hosts file for all {len(nodes)} nodes...")
        print_info("This will add hostname-to-IP mappings for all nodes to ensure proper cluster communication.")
        
        if backup:
            print_info("Original /etc/hosts files will be backed up before modification.")
        
        # Show which nodes will be configured
        print_info("\nNodes to be configured:")
        for node in nodes:
            cluster_name = node.cluster.name if node.cluster else 'No cluster'
            print_info(f"  - {node.hostname} ({node.ip_address}) - {cluster_name}")
        
        # Confirm before proceeding
        if not click.confirm("\nDo you want to proceed with /etc/hosts configuration?"):
            print_info("Operation cancelled.")
            return
        
        # Create a temporary cluster-like object for the operation
        class TempCluster:
            def __init__(self, nodes):
                self.name = "All Nodes"
                self.nodes = nodes
        
        temp_cluster = TempCluster(nodes)
        operation = orchestrator.configure_hosts_file(temp_cluster)
        
        print_info(f"Hosts file configuration started with operation ID {operation.id}")
        print_info("Check the operations list for progress.")
        print_info("This operation will:")
        print_info("  - Backup original /etc/hosts files")
        print_info("  - Add hostname-to-IP mappings for all nodes")
        print_info("  - Verify hostname resolution works correctly")
        print_info("  - Test DNS resolution for all nodes")
    
    except Exception as e:
        print_error(f"Failed to configure hosts file: {e}")
    
    finally:
        session.close()

@cluster.command('shutdown')
@click.argument('cluster_id', type=int)
@click.option('--force', is_flag=True, help='Force shutdown (immediate termination)')
@click.option('--graceful', is_flag=True, default=True, help='Graceful shutdown (default)')
def shutdown_cluster(cluster_id, force, graceful):
    """Shutdown a cluster gracefully or forcefully."""
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
        
        # Determine shutdown type
        is_graceful = graceful and not force
        
        shutdown_type = "graceful" if is_graceful else "force"
        print_info(f"Starting {shutdown_type} shutdown of cluster '{cluster.name}'...")
        
        operation = orchestrator.shutdown_cluster(cluster, graceful=is_graceful)
        
        print_info(f"Cluster shutdown started with operation ID {operation.id}")
        print_info("Check the operations list for progress.")
        
        if is_graceful:
            print_info("Graceful shutdown will safely stop all services and workloads.")
        else:
            print_warning("Force shutdown will immediately terminate all services.")
    
    except Exception as e:
        print_error(f"Failed to shutdown cluster: {e}")
    
    finally:
        session.close()

@cli.group()
def system():
    """System management commands."""
    pass

@system.command('check-prerequisites')
@click.argument('node_id', type=int)
def check_prerequisites(node_id):
    """Check system prerequisites for a node."""
    session = get_session()
    orchestrator = CLIOrchestrationService()
    
    try:
        node = session.query(Node).filter_by(id=node_id).first()
        if not node:
            print_error(f"Node with ID {node_id} not found.")
            return
        
        print_info(f"Checking prerequisites for node '{node.hostname}'...")
        
        # Create a temporary operation for prerequisites check
        operation = orchestrator._create_operation(
            operation_type='prerequisites',
            operation_name='Check Prerequisites',
            description=f'Check system prerequisites for node {node.hostname}',
            node=node,
            playbook_path='playbooks/check_prerequisites.yml'
        )
        
        try:
            orchestrator._update_operation_status(operation, 'running')
            
            # Generate inventory and run playbook
            inventory_file = orchestrator._generate_inventory([node])
            playbook_path = os.path.join(orchestrator.playbooks_dir, 'check_prerequisites.yml')
            
            success, output = orchestrator._run_ansible_playbook(playbook_path, inventory_file)
            
            if success:
                orchestrator._update_operation_status(operation, 'completed', success=True, output=output)
                print_success("Prerequisites check completed successfully!")
                print_info("Check the operation details for full report.")
            else:
                orchestrator._update_operation_status(operation, 'failed', success=False, output=output)
                print_error("Prerequisites check failed. Check the operation details for errors.")
        
        except Exception as e:
            orchestrator._update_operation_status(operation, 'failed', success=False, error_message=str(e))
            print_error(f"Failed to check prerequisites: {e}")
    
    except Exception as e:
        print_error(f"Failed to check prerequisites: {e}")
    
    finally:
        session.close()

@system.command('install-prerequisites')
@click.argument('node_id', type=int)
def install_prerequisites(node_id):
    """Install missing prerequisites on a node."""
    session = get_session()
    orchestrator = CLIOrchestrationService()
    
    try:
        node = session.query(Node).filter_by(id=node_id).first()
        if not node:
            print_error(f"Node with ID {node_id} not found.")
            return
        
        print_info(f"Installing prerequisites on node '{node.hostname}'...")
        
        # Create a temporary operation for prerequisites installation
        operation = orchestrator._create_operation(
            operation_type='prerequisites',
            operation_name='Install Prerequisites',
            description=f'Install missing prerequisites on node {node.hostname}',
            node=node,
            playbook_path='playbooks/install_prerequisites.yml'
        )
        
        try:
            orchestrator._update_operation_status(operation, 'running')
            
            # Generate inventory and run playbook
            inventory_file = orchestrator._generate_inventory([node])
            playbook_path = os.path.join(orchestrator.playbooks_dir, 'install_prerequisites.yml')
            
            success, output = orchestrator._run_ansible_playbook(playbook_path, inventory_file)
            
            if success:
                orchestrator._update_operation_status(operation, 'completed', success=True, output=output)
                print_success("Prerequisites installation completed successfully!")
                print_info("System is now ready for MicroK8s installation.")
            else:
                orchestrator._update_operation_status(operation, 'failed', success=False, output=output)
                print_error("Prerequisites installation failed. Check the operation details for errors.")
        
        except Exception as e:
            orchestrator._update_operation_status(operation, 'failed', success=False, error_message=str(e))
            print_error(f"Failed to install prerequisites: {e}")
    
    except Exception as e:
        print_error(f"Failed to install prerequisites: {e}")
    
    finally:
        session.close()

@system.command('setup-privileges')
def setup_orchestrator_privileges():
    """Setup orchestrator privileges for system operations."""
    import subprocess
    import sys
    import os
    
    script_path = os.path.join(os.path.dirname(__file__), 'scripts', 'setup_orchestrator_privileges.py')
    
    if not os.path.exists(script_path):
        print_error(f"Setup script not found: {script_path}")
        return
    
    print_info("Setting up orchestrator privileges...")
    print_info("This will configure sudo access for system operations like NUT management.")
    
    try:
        # Run the setup script with sudo
        result = subprocess.run(['sudo', 'python3', script_path], 
                              capture_output=False, text=True)
        
        if result.returncode == 0:
            print_success("Privilege setup completed successfully!")
            print_info("The orchestrator can now perform system-level operations.")
        else:
            print_error("Privilege setup failed. Please check the output above.")
    
    except Exception as e:
        print_error(f"Failed to run privilege setup: {e}")

@system.command('check-privileges')
def check_orchestrator_privileges():
    """Check if orchestrator has required privileges."""
    import subprocess
    
    print_info("Checking orchestrator privileges...")
    
    # Test commands that require sudo
    test_commands = [
        ('sudo -n systemctl status ssh', 'System service management'),
        ('sudo -n apt --version', 'Package management'),
        ('sudo -n chown --version', 'File ownership management'),
        ('sudo -n ls /etc/nut', 'NUT configuration access'),
        ('sudo -n microk8s version', 'MicroK8s management'),
        ('sudo -n ufw status', 'Firewall management'),
    ]
    
    all_passed = True
    
    for command, description in test_commands:
        try:
            result = subprocess.run(command.split(), capture_output=True, text=True)
            if result.returncode == 0:
                print_success(f"✅ {description}: OK")
            else:
                print_error(f"❌ {description}: FAILED")
                all_passed = False
        except Exception as e:
            print_error(f"❌ {description}: ERROR - {e}")
            all_passed = False
    
    if all_passed:
        print_success("All privilege checks passed! Orchestrator is ready.")
    else:
        print_error("Some privilege checks failed. Run 'system setup-privileges' to fix.")
    
    return all_passed

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

@operation.command('cleanup')
@click.option('--timeout-hours', default=2, help='Consider operations stuck after this many hours')
@click.option('--force', is_flag=True, help='Force cleanup without confirmation')
def cleanup_stuck_operations(timeout_hours, force):
    """Clean up operations that have been running too long."""
    session = get_session()
    orchestrator = CLIOrchestrationService()
    
    try:
        # First, show what would be cleaned
        from datetime import datetime, timedelta
        cutoff_time = datetime.utcnow() - timedelta(hours=timeout_hours)
        
        stuck_ops = session.query(Operation).filter(
            Operation.status == 'running',
            Operation.started_at < cutoff_time
        ).all()
        
        if not stuck_ops:
            print_info("No stuck operations found.")
            return
        
        print_info(f"Found {len(stuck_ops)} stuck operation(s):")
        for op in stuck_ops:
            runtime = datetime.utcnow() - op.started_at if op.started_at else None
            target = "Unknown"
            if op.router_switch:
                target = f"Router: {op.router_switch.hostname}"
            elif op.node:
                target = f"Node: {op.node.hostname}"
            elif op.cluster:
                target = f"Cluster: {op.cluster.name}"
            
            print(f"  - ID {op.id}: {op.operation_name} ({target}) - Running for {runtime}")
        
        if not force:
            if not click.confirm(f"\nCleanup {len(stuck_ops)} stuck operations?"):
                print_info("Cleanup cancelled.")
                return
        
        # Perform cleanup
        result = orchestrator.cleanup_stuck_operations(timeout_hours)
        
        if result['success']:
            print_success(result['message'])
        else:
            print_error(f"Cleanup failed: {result['error']}")
    
    except Exception as e:
        print_error(f"Failed to cleanup operations: {e}")
    
    finally:
        session.close()

@cluster.command('scan')
@click.argument('cluster_id', type=int)
def scan_cluster_state(cluster_id):
    """Scan cluster to validate configuration and detect drift."""
    session = get_session()
    orchestrator = CLIOrchestrationService()
    
    try:
        cluster = session.query(Cluster).filter_by(id=cluster_id).first()
        if not cluster:
            print_error(f"Cluster with ID {cluster_id} not found.")
            return
        
        if not cluster.nodes:
            print_error(f"Cluster '{cluster.name}' has no nodes to scan.")
            return
        
        print_info(f"Scanning cluster '{cluster.name}' for configuration drift...")
        operation = orchestrator.scan_cluster_state(cluster)
        
        print_info(f"Cluster scan started with operation ID {operation.id}")
        print_info("Check the operations list for detailed results.")
        print_info("The scan will validate:")
        print("  • Node readiness and MicroK8s status")
        print("  • Required addon availability") 
        print("  • Network configuration compliance")
        print("  • System resource status")
        print("  • Configuration drift detection")
    
    except Exception as e:
        print_error(f"Failed to scan cluster: {e}")
    
    finally:
        session.close()

@cli.group()
def network():
    """Manage network leases and interfaces."""
    pass

@network.command('scan-leases')
@click.argument('router_switch_id', type=int)
def scan_network_leases(router_switch_id):
    """Scan router for DHCP leases."""
    session = get_session()
    orchestrator = CLIOrchestrationService()
    
    try:
        router_switch = session.query(RouterSwitch).filter_by(id=router_switch_id).first()
        if not router_switch:
            print_error(f"Router switch with ID {router_switch_id} not found.")
            return
        
        print_info(f"Scanning DHCP leases on '{router_switch.hostname}'...")
        operation = orchestrator.scan_dhcp_leases(router_switch)
        
        print_info(f"Lease scan started with operation ID {operation.id}")
        print_info("Check the operations list for results.")
    
    except Exception as e:
        print_error(f"Failed to scan leases: {e}")
    
    finally:
        session.close()

@network.command('scan-interfaces')
@click.argument('router_switch_id', type=int)
def scan_network_interfaces(router_switch_id):
    """Scan router for network interfaces."""
    session = get_session()
    orchestrator = CLIOrchestrationService()
    
    try:
        router_switch = session.query(RouterSwitch).filter_by(id=router_switch_id).first()
        if not router_switch:
            print_error(f"Router switch with ID {router_switch_id} not found.")
            return
        
        print_info(f"Scanning network interfaces on '{router_switch.hostname}'...")
        operation = orchestrator.scan_network_interfaces(router_switch)
        
        print_info(f"Interface scan started with operation ID {operation.id}")
        print_info("Check the operations list for results.")
    
    except Exception as e:
        print_error(f"Failed to scan interfaces: {e}")
    
    finally:
        session.close()

@network.command('list-leases')
@click.option('--router-id', type=int, help='Filter by router switch ID')
@click.option('--status', help='Filter by status')
@click.option('--cluster-nodes-only', is_flag=True, help='Show only cluster node leases')
@click.option('--format', '-f', type=click.Choice(['table', 'json']), default='table', help='Output format')
def list_network_leases(router_id, status, cluster_nodes_only, format):
    """List network leases."""
    session = get_session()
    try:
        query = session.query(NetworkLease).order_by(NetworkLease.last_activity.desc())
        
        if router_id:
            query = query.filter_by(router_switch_id=router_id)
        if status:
            query = query.filter_by(status=status)
        if cluster_nodes_only:
            query = query.filter(NetworkLease.node_id.isnot(None))
        
        leases = query.all()
        
        if format == 'json':
            click.echo(json.dumps([lease.to_dict() for lease in leases], indent=2))
        else:
            if not leases:
                print_info("No network leases found.")
                return
            
            headers = ['ID', 'MAC Address', 'IP Address', 'Hostname', 'Router', 'Status', 'Node', 'Remaining', 'Last Seen']
            rows = []
            
            for lease in leases:
                router_name = lease.router_switch.hostname if lease.router_switch else 'Unknown'
                node_name = lease.node.hostname if lease.node else '-'
                remaining = f"{lease.time_remaining // 3600}h {(lease.time_remaining % 3600) // 60}m" if lease.time_remaining > 0 else 'Expired'
                last_seen = lease.last_seen.strftime('%m-%d %H:%M') if lease.last_seen else 'Never'
                
                rows.append([
                    lease.id,
                    lease.mac_address,
                    lease.ip_address,
                    lease.hostname or '-',
                    router_name,
                    lease.status,
                    node_name,
                    remaining,
                    last_seen
                ])
            
            click.echo(tabulate(rows, headers=headers, tablefmt='grid'))
            
            # Show summary
            active_count = len([l for l in leases if l.is_active])
            cluster_count = len([l for l in leases if l.is_cluster_node])
            expired_count = len([l for l in leases if l.is_expired])
            
            click.echo(f"\nSummary: {len(leases)} total, {active_count} active, {cluster_count} cluster nodes, {expired_count} expired")
    
    finally:
        session.close()

@network.command('match-nodes')
def match_leases_to_nodes():
    """Match network leases to cluster nodes by IP address."""
    session = get_session()
    orchestrator = CLIOrchestrationService()
    
    try:
        print_info("Matching network leases to cluster nodes...")
        result = orchestrator.match_leases_to_nodes()
        
        if result.get('success'):
            matched_count = result.get('matched_count', 0)
            print_success(f"Successfully matched {matched_count} leases to cluster nodes.")
        else:
            print_error(f"Failed to match leases: {result.get('error')}")
    
    except Exception as e:
        print_error(f"Failed to match leases to nodes: {e}")
    
    finally:
        session.close()

@network.command('show-lease')
@click.argument('lease_id', type=int)
def show_network_lease(lease_id):
    """Show network lease details."""
    session = get_session()
    try:
        lease = session.query(NetworkLease).filter_by(id=lease_id).first()
        if not lease:
            print_error(f"Network lease with ID {lease_id} not found.")
            return
        
        click.echo(f"\n{Fore.CYAN}Network Lease Details:{Style.RESET_ALL}")
        click.echo(f"ID: {lease.id}")
        click.echo(f"MAC Address: {lease.mac_address}")
        click.echo(f"IP Address: {lease.ip_address}")
        click.echo(f"Hostname: {lease.hostname or 'Unknown'}")
        click.echo(f"Status: {lease.status}")
        click.echo(f"Active: {'Yes' if lease.is_active else 'No'}")
        click.echo(f"Static: {'Yes' if lease.is_static else 'No'}")
        click.echo(f"Expired: {'Yes' if lease.is_expired else 'No'}")
        
        if lease.router_switch:
            click.echo(f"Router Switch: {lease.router_switch.hostname} ({lease.router_switch.ip_address})")
        
        if lease.node:
            click.echo(f"Cluster Node: {lease.node.hostname} ({lease.node.ip_address})")
            click.echo(f"Control Plane: {'Yes' if lease.node.is_control_plane else 'No'}")
        
        click.echo(f"Lease Start: {lease.lease_start}")
        click.echo(f"Lease End: {lease.lease_end}")
        click.echo(f"Duration: {lease.lease_duration_seconds // 3600}h {(lease.lease_duration_seconds % 3600) // 60}m")
        
        if lease.time_remaining > 0:
            click.echo(f"Time Remaining: {lease.time_remaining // 3600}h {(lease.time_remaining % 3600) // 60}m")
        else:
            click.echo(f"Time Remaining: Expired")
        
        click.echo(f"First Seen: {lease.first_seen}")
        click.echo(f"Last Seen: {lease.last_seen}")
        click.echo(f"Last Activity: {lease.last_activity}")
        click.echo(f"Connection Count: {lease.connection_count}")
        click.echo(f"Uptime: {lease.uptime_hours} hours")
        
        if lease.vlan_id:
            click.echo(f"VLAN ID: {lease.vlan_id}")
        if lease.subnet:
            click.echo(f"Subnet: {lease.subnet}")
        if lease.gateway:
            click.echo(f"Gateway: {lease.gateway}")
        
        if lease.device_type:
            click.echo(f"Device Type: {lease.device_type}")
        if lease.os_version:
            click.echo(f"OS Version: {lease.os_version}")
        if lease.vendor_class:
            click.echo(f"Vendor Class: {lease.vendor_class}")
        
        click.echo(f"Discovered By: {lease.discovered_by}")
        
        if lease.notes:
            click.echo(f"\n{Fore.CYAN}Notes:{Style.RESET_ALL}")
            click.echo(lease.notes)
    
    finally:
        session.close()

@cli.command('check-longhorn-prerequisites')
@click.option('--node-id', type=int, help='Check prerequisites for specific node ID')
@click.option('--hostname', help='Check prerequisites for specific hostname')
@click.option('--all', 'check_all', is_flag=True, help='Check prerequisites for all nodes')
def check_longhorn_prerequisites(node_id, hostname, check_all):
    """Check Longhorn prerequisites on nodes."""
    try:
        from app.models.database import db
        from app.models.flask_models import Node
        from app.services.orchestrator import OrchestrationService
        
        session = db.create_session()
        orchestrator = OrchestrationService()
        
        try:
            if node_id:
                nodes = [session.query(Node).filter(Node.id == node_id).first()]
                if not nodes[0]:
                    print_error(f"Node with ID {node_id} not found")
                    return
            elif hostname:
                nodes = [session.query(Node).filter(Node.hostname == hostname).first()]
                if not nodes[0]:
                    print_error(f"Node with hostname {hostname} not found")
                    return
            elif check_all:
                nodes = session.query(Node).all()
            else:
                print_error("Please specify --node-id, --hostname, or --all")
                return
            
            if not nodes:
                print_warning("No nodes found")
                return
            
            print_info(f"Checking Longhorn prerequisites for {len(nodes)} node(s)...")
            
            for node in nodes:
                print_info(f"Checking prerequisites for {node.hostname} ({node.ip_address})...")
                
                # Create operation record
                from app.models.flask_models import Operation
                operation = Operation(
                    operation_type='check_longhorn_prerequisites',
                    operation_name='Check Longhorn Prerequisites',
                    description=f'Check Longhorn prerequisites on node {node.hostname}',
                    playbook_path='ansible/playbooks/check_longhorn_prerequisites.yml',
                    node_id=node.id,
                    user_id=1  # System user
                )
                session.add(operation)
                session.commit()
                
                # Run the operation
                result = orchestrator.run_operation(operation.id)
                
                if result:
                    print_success(f"Prerequisites check started for {node.hostname} (Operation ID: {operation.id})")
                else:
                    print_error(f"Failed to start prerequisites check for {node.hostname}")
        
        finally:
            session.close()
    
    except Exception as e:
        print_error(f"Error checking Longhorn prerequisites: {e}")

@cli.command('install-longhorn-prerequisites')
@click.option('--node-id', type=int, help='Install prerequisites for specific node ID')
@click.option('--hostname', help='Install prerequisites for specific hostname')
@click.option('--all', 'install_all', is_flag=True, help='Install prerequisites for all nodes')
def install_longhorn_prerequisites(node_id, hostname, install_all):
    """Install Longhorn prerequisites on nodes."""
    try:
        from app.models.database import db
        from app.models.flask_models import Node
        from app.services.orchestrator import OrchestrationService
        
        session = db.create_session()
        orchestrator = OrchestrationService()
        
        try:
            if node_id:
                nodes = [session.query(Node).filter(Node.id == node_id).first()]
                if not nodes[0]:
                    print_error(f"Node with ID {node_id} not found")
                    return
            elif hostname:
                nodes = [session.query(Node).filter(Node.hostname == hostname).first()]
                if not nodes[0]:
                    print_error(f"Node with hostname {hostname} not found")
                    return
            elif install_all:
                nodes = session.query(Node).all()
            else:
                print_error("Please specify --node-id, --hostname, or --all")
                return
            
            if not nodes:
                print_warning("No nodes found")
                return
            
            print_info(f"Installing Longhorn prerequisites for {len(nodes)} node(s)...")
            
            for node in nodes:
                print_info(f"Installing prerequisites for {node.hostname} ({node.ip_address})...")
                
                # Create operation record
                from app.models.flask_models import Operation
                operation = Operation(
                    operation_type='install_longhorn_prerequisites',
                    operation_name='Install Longhorn Prerequisites',
                    description=f'Install Longhorn prerequisites on node {node.hostname}',
                    playbook_path='ansible/playbooks/install_longhorn_prerequisites.yml',
                    node_id=node.id,
                    user_id=1  # System user
                )
                session.add(operation)
                session.commit()
                
                # Run the operation
                result = orchestrator.run_operation(operation.id)
                
                if result:
                    print_success(f"Prerequisites installation started for {node.hostname} (Operation ID: {operation.id})")
                else:
                    print_error(f"Failed to start prerequisites installation for {node.hostname}")
        
        finally:
            session.close()
    
    except Exception as e:
        print_error(f"Error installing Longhorn prerequisites: {e}")

@cli.command('setup-new-node')
@click.option('--node-id', type=int, required=True, help='Node ID to setup')
def setup_new_node(node_id):
    """Setup a new node with all prerequisites and MicroK8s."""
    try:
        from app.models.database import db
        from app.models.flask_models import Node
        from app.services.orchestrator import OrchestrationService
        
        session = db.create_session()
        orchestrator = OrchestrationService()
        
        try:
            node = session.query(Node).filter(Node.id == node_id).first()
            if not node:
                print_error(f"Node with ID {node_id} not found")
                return
            
            print_info(f"Setting up new node: {node.hostname} ({node.ip_address})")
            print_warning("This will install all prerequisites, MicroK8s, and configure Longhorn support.")
            print_warning("This process may take 10-15 minutes.")
            
            if not click.confirm("Do you want to continue?"):
                print_info("Setup cancelled")
                return
            
            # Create operation record
            from app.models.flask_models import Operation
            operation = Operation(
                operation_type='setup_new_node',
                operation_name='Setup New Node',
                description=f'Complete setup of new node {node.hostname} with MicroK8s and Longhorn prerequisites',
                playbook_path='ansible/playbooks/setup_new_node.yml',
                node_id=node.id,
                user_id=1  # System user
            )
            session.add(operation)
            session.commit()
            
            # Run the operation
            result = orchestrator.run_operation(operation.id)
            
            if result:
                print_success(f"Node setup started for {node.hostname} (Operation ID: {operation.id})")
                print_info("Check the operations page in the web interface for progress updates.")
            else:
                print_error(f"Failed to start node setup for {node.hostname}")
        
        finally:
            session.close()
    
    except Exception as e:
        print_error(f"Error setting up new node: {e}")

@cli.command('web')
@click.option('--host', default='0.0.0.0', help='Host to bind to')
@click.option('--port', default=5000, help='Port to bind to')
@click.option('--debug', is_flag=True, help='Enable debug mode')
@click.option('--production', is_flag=True, help='Start in production mode using Gunicorn')
def start_web(host, port, debug, production):
    """Start the web interface."""
    try:
        if production:
            # Start with Gunicorn for production
            import subprocess
            import sys
            
            # Check if Gunicorn is installed
            try:
                import gunicorn
            except ImportError:
                print_error("Gunicorn not found. Install it with: pip install gunicorn")
                return
            
            # Build Gunicorn command
            cmd = [
                sys.executable, '-m', 'gunicorn',
                '--bind', f'{host}:{port}',
                '--workers', '4',
                '--timeout', '30',
                '--access-logfile', '-',
                '--error-logfile', '-',
                '--log-level', 'info',
                'wsgi:application'
            ]
            
            if debug:
                cmd.extend(['--reload', '--log-level', 'debug'])
            
            print_info(f"Starting production web server on http://{host}:{port}")
            print_info("Using Gunicorn WSGI server")
            subprocess.run(cmd)
        else:
            # Development mode with Flask dev server
            from app import create_app
            
            app = create_app()
            print_info(f"Starting development web interface on http://{host}:{port}")
            print_warning("WARNING: This is a development server. Use --production for production deployment.")
            app.run(host=host, port=port, debug=debug)
    
    except ImportError as e:
        print_error(f"Failed to import Flask app: {e}")
        print_info("Make sure Flask and other web dependencies are installed.")

@cli.command('web-stop')
@click.option('--force', is_flag=True, help='Force kill all web server processes')
def web_stop(force):
    """Stop the web interface server."""
    try:
        import subprocess
        import signal
        import os
        
        # Find web server processes
        try:
            # Try to find processes by command line
            result = subprocess.run([
                'pgrep', '-f', 'python.*cli.py web'
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                pids = result.stdout.strip().split('\n')
                pids = [pid for pid in pids if pid]  # Remove empty strings
                
                if pids:
                    print_info(f"Found {len(pids)} web server process(es): {', '.join(pids)}")
                    
                    for pid in pids:
                        try:
                            if force:
                                print_info(f"Force killing process {pid}...")
                                os.kill(int(pid), signal.SIGKILL)
                            else:
                                print_info(f"Stopping process {pid} gracefully...")
                                os.kill(int(pid), signal.SIGTERM)
                            
                            print_success(f"Process {pid} stopped successfully")
                            
                        except ProcessLookupError:
                            print_warning(f"Process {pid} not found (may have already stopped)")
                        except PermissionError:
                            print_error(f"Permission denied to stop process {pid}")
                        except Exception as e:
                            print_error(f"Failed to stop process {pid}: {e}")
                    
                    if not force:
                        print_info("Waiting 3 seconds for graceful shutdown...")
                        import time
                        time.sleep(3)
                        
                        # Check if processes are still running
                        result = subprocess.run([
                            'pgrep', '-f', 'python.*cli.py web'
                        ], capture_output=True, text=True)
                        
                        if result.returncode == 0:
                            remaining_pids = result.stdout.strip().split('\n')
                            remaining_pids = [pid for pid in remaining_pids if pid]
                            
                            if remaining_pids:
                                print_warning(f"Some processes are still running: {', '.join(remaining_pids)}")
                                print_info("Use --force to kill them forcefully")
                            else:
                                print_success("All web server processes stopped successfully")
                        else:
                            print_success("All web server processes stopped successfully")
                else:
                    print_info("No web server processes found")
            else:
                print_info("No web server processes found")
                
        except FileNotFoundError:
            # pgrep not available, try alternative method
            print_info("Using alternative method to find processes...")
            
            try:
                result = subprocess.run([
                    'ps', 'aux'
                ], capture_output=True, text=True)
                
                if result.returncode == 0:
                    lines = result.stdout.split('\n')
                    web_processes = []
                    
                    for line in lines:
                        if 'python' in line and 'cli.py web' in line and 'grep' not in line:
                            parts = line.split()
                            if len(parts) >= 2:
                                pid = parts[1]
                                web_processes.append(pid)
                    
                    if web_processes:
                        print_info(f"Found {len(web_processes)} web server process(es): {', '.join(web_processes)}")
                        
                        for pid in web_processes:
                            try:
                                if force:
                                    print_info(f"Force killing process {pid}...")
                                    os.kill(int(pid), signal.SIGKILL)
                                else:
                                    print_info(f"Stopping process {pid} gracefully...")
                                    os.kill(int(pid), signal.SIGTERM)
                                
                                print_success(f"Process {pid} stopped successfully")
                                
                            except ProcessLookupError:
                                print_warning(f"Process {pid} not found (may have already stopped)")
                            except PermissionError:
                                print_error(f"Permission denied to stop process {pid}")
                            except Exception as e:
                                print_error(f"Failed to stop process {pid}: {e}")
                    else:
                        print_info("No web server processes found")
                else:
                    print_error("Failed to list processes")
                    
            except Exception as e:
                print_error(f"Failed to find processes: {e}")
        
    except Exception as e:
        print_error(f"Failed to stop web server: {e}")

@cli.command('web-status')
def web_status():
    """Check the status of the web interface server."""
    try:
        import subprocess
        
        # Find web server processes
        try:
            result = subprocess.run([
                'pgrep', '-f', 'python.*cli.py web'
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                pids = result.stdout.strip().split('\n')
                pids = [pid for pid in pids if pid]  # Remove empty strings
                
                if pids:
                    print_success(f"Web server is running with {len(pids)} process(es):")
                    for pid in pids:
                        print_info(f"  Process ID: {pid}")
                    
                    # Try to get more details about the processes
                    try:
                        for pid in pids:
                            result = subprocess.run([
                                'ps', '-p', pid, '-o', 'pid,ppid,cmd,etime'
                            ], capture_output=True, text=True)
                            
                            if result.returncode == 0:
                                lines = result.stdout.strip().split('\n')
                                if len(lines) > 1:  # Skip header
                                    print_info(f"  Details: {lines[1]}")
                    except:
                        pass  # Ignore errors getting process details
                        
                else:
                    print_info("Web server is not running")
            else:
                print_info("Web server is not running")
                
        except FileNotFoundError:
            # pgrep not available, try alternative method
            try:
                result = subprocess.run([
                    'ps', 'aux'
                ], capture_output=True, text=True)
                
                if result.returncode == 0:
                    lines = result.stdout.split('\n')
                    web_processes = []
                    
                    for line in lines:
                        if 'python' in line and 'cli.py web' in line and 'grep' not in line:
                            web_processes.append(line.strip())
                    
                    if web_processes:
                        print_success(f"Web server is running with {len(web_processes)} process(es):")
                        for process in web_processes:
                            print_info(f"  {process}")
                    else:
                        print_info("Web server is not running")
                else:
                    print_error("Failed to check process status")
                    
            except Exception as e:
                print_error(f"Failed to check web server status: {e}")
        
    except Exception as e:
        print_error(f"Failed to check web server status: {e}")

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

# ============================================================================
# User Management Commands
# ============================================================================

@cli.group()
def user():
    """User management commands."""
    pass

@user.command('create-admin')
@click.option('--username', '-u', prompt=True, help='Admin username')
@click.option('--email', '-e', prompt=True, help='Admin email address')
@click.option('--password', '-p', prompt=True, hide_input=True, confirmation_prompt=True, help='Admin password')
@click.option('--first-name', '-f', help='First name')
@click.option('--last-name', '-l', help='Last name')
def create_admin(username, email, password, first_name, last_name):
    """Create a new admin user."""
    try:
        # Import here to avoid circular imports
        from app import create_app
        from app.models.flask_models import User
        from app.models.database import db
        
        app = create_app()
        with app.app_context():
            # Check if user already exists
            existing_user = User.query.filter_by(username=username).first()
            if existing_user:
                print_error(f"User '{username}' already exists!")
                return
            
            existing_email = User.query.filter_by(email=email).first()
            if existing_email:
                print_error(f"Email '{email}' is already registered!")
                return
            
            # Create new admin user
            user = User(
                username=username,
                email=email,
                first_name=first_name or '',
                last_name=last_name or '',
                is_admin=True,
                is_active=True
            )
            user.set_password(password)
            
            db.session.add(user)
            db.session.commit()
            
            print_success(f"Admin user '{username}' created successfully!")
            print_info(f"Full name: {user.full_name}")
            print_info(f"Email: {email}")
            print_info("The user can now log in to the web interface.")
            
    except Exception as e:
        print_error(f"Failed to create admin user: {e}")

@user.command('list')
@click.option('--format', '-f', type=click.Choice(['table', 'json']), default='table', help='Output format')
def list_users(format):
    """List all users."""
    try:
        from app import create_app
        from app.models.flask_models import User
        
        app = create_app()
        with app.app_context():
            users = User.query.order_by(User.created_at.desc()).all()
            
            if format == 'json':
                users_data = [user.to_dict() for user in users]
                click.echo(json.dumps(users_data, indent=2, default=str))
            else:
                if not users:
                    print_info("No users found.")
                    return
                
                headers = ['ID', 'Username', 'Full Name', 'Email', 'Role', 'Status', 'Last Login', 'Created']
                rows = []
                
                for user in users:
                    role = 'Admin' if user.is_admin else 'User'
                    status = 'Active' if user.is_active else 'Inactive'
                    last_login = user.last_login.strftime('%Y-%m-%d %H:%M') if user.last_login else 'Never'
                    created = user.created_at.strftime('%Y-%m-%d %H:%M')
                    
                    rows.append([
                        user.id,
                        user.username,
                        user.full_name,
                        user.email,
                        role,
                        status,
                        last_login,
                        created
                    ])
                
                click.echo(tabulate(rows, headers=headers, tablefmt='grid'))
                print_info(f"Total users: {len(users)}")
                
    except Exception as e:
        print_error(f"Failed to list users: {e}")

@user.command('toggle-admin')
@click.argument('username')
def toggle_admin(username):
    """Toggle admin status for a user."""
    try:
        from app import create_app
        from app.models.flask_models import User
        from app.models.database import db
        
        app = create_app()
        with app.app_context():
            user = User.query.filter_by(username=username).first()
            if not user:
                print_error(f"User '{username}' not found!")
                return
            
            user.is_admin = not user.is_admin
            db.session.commit()
            
            status = 'granted' if user.is_admin else 'revoked'
            print_success(f"Admin privileges {status} for user '{username}'")
            
    except Exception as e:
        print_error(f"Failed to toggle admin status: {e}")

@user.command('deactivate')
@click.argument('username')
@click.option('--confirm', is_flag=True, help='Skip confirmation prompt')
def deactivate_user(username, confirm):
    """Deactivate a user account."""
    try:
        from app import create_app
        from app.models.flask_models import User
        from app.models.database import db
        
        app = create_app()
        with app.app_context():
            user = User.query.filter_by(username=username).first()
            if not user:
                print_error(f"User '{username}' not found!")
                return
            
            if not user.is_active:
                print_warning(f"User '{username}' is already inactive.")
                return
            
            if not confirm:
                if not click.confirm(f"Are you sure you want to deactivate user '{username}'?"):
                    print_info("Operation cancelled.")
                    return
            
            user.is_active = False
            db.session.commit()
            
            print_success(f"User '{username}' has been deactivated.")
            
    except Exception as e:
        print_error(f"Failed to deactivate user: {e}")

@user.command('activate')
@click.argument('username')
def activate_user(username):
    """Activate a user account."""
    try:
        from app import create_app
        from app.models.flask_models import User
        from app.models.database import db
        
        app = create_app()
        with app.app_context():
            user = User.query.filter_by(username=username).first()
            if not user:
                print_error(f"User '{username}' not found!")
                return
            
            if user.is_active:
                print_warning(f"User '{username}' is already active.")
                return
            
            user.is_active = True
            db.session.commit()
            
            print_success(f"User '{username}' has been activated.")
            
    except Exception as e:
        print_error(f"Failed to activate user: {e}")

# Hardware report commands
@cli.group()
def hardware_report():
    """Hardware report management commands."""
    pass

@hardware_report.command()
@click.option('--cluster-id', type=int, help='Collect for specific cluster only')
@click.option('--node-id', type=int, help='Collect for specific node only')
@click.option('--output', '-o', type=click.Choice(['table', 'json', 'csv']), default='table', 
              help='Output format')
def collect(cluster_id, node_id, output):
    """Collect hardware information from nodes."""
    from app.services.orchestrator import OrchestrationService
    
    try:
        orchestrator = OrchestrationService()
        
        print_info("Starting hardware report collection...")
        result = orchestrator.collect_hardware_report(cluster_id=cluster_id, node_id=node_id)
        
        if result['success']:
            print_success(f"Hardware report collection started successfully!")
            print(f"Operation ID: {result['operation_id']}")
            print(f"Nodes being processed: {result.get('nodes_updated', 0)}")
            print("\nYou can monitor the operation progress with:")
            print(f"  python cli.py operation status {result['operation_id']}")
        else:
            print_error(f"Failed to start hardware collection: {result['error']}")
            
    except Exception as e:
        print_error(f"Failed to collect hardware report: {e}")

@hardware_report.command()
@click.option('--cluster-id', type=int, help='Show report for specific cluster only')
@click.option('--node-id', type=int, help='Show report for specific node only')
@click.option('--output', '-o', type=click.Choice(['table', 'json', 'csv']), default='table', 
              help='Output format')
@click.option('--detailed', '-d', is_flag=True, help='Show detailed hardware information')
def show(cluster_id, node_id, output, detailed):
    """Show hardware report for nodes."""
    try:
        with get_db_session() as session:
            # Build query
            query = session.query(Node)
            
            if node_id:
                query = query.filter(Node.id == node_id)
            elif cluster_id:
                query = query.filter(Node.cluster_id == cluster_id)
            
            nodes = query.all()
            
            if not nodes:
                print_warning("No nodes found matching criteria.")
                return
            
            if output == 'json':
                import json
                nodes_data = []
                for node in nodes:
                    node_dict = node.to_dict()
                    if detailed:
                        # Parse JSON fields
                        try:
                            if node.cpu_info:
                                node_dict['cpu_info_parsed'] = json.loads(node.cpu_info)
                            if node.memory_info:
                                node_dict['memory_info_parsed'] = json.loads(node.memory_info)
                            if node.disk_info:
                                node_dict['disk_info_parsed'] = json.loads(node.disk_info)
                            if node.network_info:
                                node_dict['network_info_parsed'] = json.loads(node.network_info)
                            if node.gpu_info:
                                node_dict['gpu_info_parsed'] = json.loads(node.gpu_info)
                            if node.thermal_info:
                                node_dict['thermal_info_parsed'] = json.loads(node.thermal_info)
                        except json.JSONDecodeError:
                            pass
                    nodes_data.append(node_dict)
                
                print(json.dumps(nodes_data, indent=2, default=str))
                
            elif output == 'csv':
                import csv
                import sys
                
                fieldnames = ['hostname', 'ip_address', 'status', 'cpu_cores', 'memory_gb', 
                             'disk_gb', 'cpu_usage_percent', 'memory_usage_percent', 
                             'disk_usage_percent', 'load_average', 'uptime_seconds', 'last_seen']
                
                writer = csv.DictWriter(sys.stdout, fieldnames=fieldnames)
                writer.writeheader()
                
                for node in nodes:
                    row = {field: getattr(node, field) for field in fieldnames}
                    writer.writerow(row)
                    
            else:  # table format
                
                if detailed:
                    # Detailed view - show one node at a time
                    for i, node in enumerate(nodes):
                        if i > 0:
                            print("\n" + "="*80 + "\n")
                        
                        print(f"Node: {node.hostname} ({node.ip_address})")
                        print("-" * 40)
                        
                        basic_info = [
                            ["Status", node.status or 'Unknown'],
                            ["OS Version", node.os_version or 'Unknown'],
                            ["Kernel", node.kernel_version or 'Unknown'],
                            ["Last Seen", node.last_seen.strftime('%Y-%m-%d %H:%M:%S') if node.last_seen else 'Never'],
                        ]
                        
                        hardware_info = [
                            ["CPU Cores", node.cpu_cores or 'Unknown'],
                            ["Memory (GB)", f"{node.memory_gb:.1f}" if node.memory_gb else 'Unknown'],
                            ["Disk (GB)", f"{node.disk_gb:.1f}" if node.disk_gb else 'Unknown'],
                        ]
                        
                        usage_info = [
                            ["CPU Usage", f"{node.cpu_usage_percent}%" if node.cpu_usage_percent is not None else 'N/A'],
                            ["Memory Usage", f"{node.memory_usage_percent}%" if node.memory_usage_percent is not None else 'N/A'],
                            ["Disk Usage", f"{node.disk_usage_percent}%" if node.disk_usage_percent is not None else 'N/A'],
                            ["Load Average", node.load_average or 'N/A'],
                            ["Uptime", f"{node.uptime_seconds / 86400:.1f} days" if node.uptime_seconds else 'N/A'],
                        ]
                        
                        print("Basic Information:")
                        print(tabulate(basic_info, tablefmt="grid"))
                        print("\nHardware Information:")
                        print(tabulate(hardware_info, tablefmt="grid"))
                        print("\nCurrent Usage:")
                        print(tabulate(usage_info, tablefmt="grid"))
                        
                        # Show GPU and thermal status
                        features = []
                        if node.gpu_info and 'present": true' in node.gpu_info.lower():
                            features.append("GPU Present")
                        if node.thermal_info and 'sensors_available": true' in node.thermal_info.lower():
                            features.append("Thermal Sensors")
                        
                        if features:
                            print(f"\nFeatures: {', '.join(features)}")
                else:
                    # Summary table view
                    headers = ['Hostname', 'IP Address', 'Status', 'CPU Cores', 'Memory (GB)', 
                              'Disk (GB)', 'CPU %', 'Memory %', 'Disk %', 'GPU', 'Thermal', 'Last Seen']
                    
                    rows = []
                    for node in nodes:
                        gpu_status = "Yes" if (node.gpu_info and 'present": true' in node.gpu_info.lower()) else "No"
                        thermal_status = "Yes" if (node.thermal_info and 'sensors_available": true' in node.thermal_info.lower()) else "No"
                        
                        rows.append([
                            node.hostname,
                            node.ip_address,
                            node.status or 'Unknown',
                            node.cpu_cores or 'Unknown',
                            f"{node.memory_gb:.1f}" if node.memory_gb else 'Unknown',
                            f"{node.disk_gb:.1f}" if node.disk_gb else 'Unknown',
                            f"{node.cpu_usage_percent}%" if node.cpu_usage_percent is not None else 'N/A',
                            f"{node.memory_usage_percent}%" if node.memory_usage_percent is not None else 'N/A',
                            f"{node.disk_usage_percent}%" if node.disk_usage_percent is not None else 'N/A',
                            gpu_status,
                            thermal_status,
                            node.last_seen.strftime('%Y-%m-%d %H:%M') if node.last_seen else 'Never'
                        ])
                    
                    print(tabulate(rows, headers=headers, tablefmt="grid"))
                    
                    # Show summary
                    total_cores = sum(node.cpu_cores or 0 for node in nodes)
                    total_memory = sum(node.memory_gb or 0 for node in nodes)
                    total_disk = sum(node.disk_gb or 0 for node in nodes)
                    nodes_with_usage = [n for n in nodes if n.cpu_usage_percent is not None]
                    
                    print(f"\nSummary:")
                    print(f"  Total Nodes: {len(nodes)}")
                    print(f"  Total CPU Cores: {total_cores}")
                    print(f"  Total Memory: {total_memory:.1f} GB")
                    print(f"  Total Disk: {total_disk:.1f} GB")
                    print(f"  Nodes with Usage Data: {len(nodes_with_usage)}")
                    
                    if nodes_with_usage:
                        avg_cpu = sum(n.cpu_usage_percent for n in nodes_with_usage) / len(nodes_with_usage)
                        avg_memory = sum(n.memory_usage_percent for n in nodes_with_usage if n.memory_usage_percent is not None) / len([n for n in nodes_with_usage if n.memory_usage_percent is not None])
                        avg_disk = sum(n.disk_usage_percent for n in nodes_with_usage if n.disk_usage_percent is not None) / len([n for n in nodes_with_usage if n.disk_usage_percent is not None])
                        
                        print(f"  Average CPU Usage: {avg_cpu:.1f}%")
                        if avg_memory:
                            print(f"  Average Memory Usage: {avg_memory:.1f}%")
                        if avg_disk:
                            print(f"  Average Disk Usage: {avg_disk:.1f}%")
            
    except Exception as e:
        print_error(f"Failed to show hardware report: {e}")

@hardware_report.command()
@click.option('--cluster-id', type=int, help='Export for specific cluster only')
@click.option('--node-id', type=int, help='Export for specific node only')
@click.option('--output-file', '-f', help='Output file path', required=True)
@click.option('--format', type=click.Choice(['json', 'csv', 'html']), default='json', 
              help='Export format')
def export(cluster_id, node_id, output_file, format):
    """Export hardware report to file."""
    try:
        with get_db_session() as session:
            # Build query
            query = session.query(Node)
            
            if node_id:
                query = query.filter(Node.id == node_id)
            elif cluster_id:
                query = query.filter(Node.cluster_id == cluster_id)
            
            nodes = query.all()
            
            if not nodes:
                print_warning("No nodes found matching criteria.")
                return
            
            if format == 'json':
                import json
                nodes_data = [node.to_dict() for node in nodes]
                
                with open(output_file, 'w') as f:
                    json.dump({
                        'timestamp': datetime.now().isoformat(),
                        'total_nodes': len(nodes),
                        'nodes': nodes_data
                    }, f, indent=2, default=str)
                    
            elif format == 'csv':
                import csv
                
                fieldnames = ['hostname', 'ip_address', 'status', 'os_version', 'kernel_version',
                             'cpu_cores', 'memory_gb', 'disk_gb', 'cpu_usage_percent', 
                             'memory_usage_percent', 'disk_usage_percent', 'load_average', 
                             'uptime_seconds', 'last_seen', 'created_at']
                
                with open(output_file, 'w', newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    
                    for node in nodes:
                        row = {field: getattr(node, field) for field in fieldnames}
                        writer.writerow(row)
                        
            elif format == 'html':
                html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Hardware Report - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        .summary {{ background-color: #f9f9f9; padding: 15px; margin-bottom: 20px; border-radius: 5px; }}
    </style>
</head>
<body>
    <h1>Hardware Report</h1>
    <div class="summary">
        <h3>Summary</h3>
        <p><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p><strong>Total Nodes:</strong> {len(nodes)}</p>
        <p><strong>Total CPU Cores:</strong> {sum(node.cpu_cores or 0 for node in nodes)}</p>
        <p><strong>Total Memory:</strong> {sum(node.memory_gb or 0 for node in nodes):.1f} GB</p>
        <p><strong>Total Disk:</strong> {sum(node.disk_gb or 0 for node in nodes):.1f} GB</p>
    </div>
    
    <table>
        <tr>
            <th>Hostname</th>
            <th>IP Address</th>
            <th>Status</th>
            <th>CPU Cores</th>
            <th>Memory (GB)</th>
            <th>Disk (GB)</th>
            <th>CPU Usage</th>
            <th>Memory Usage</th>
            <th>Disk Usage</th>
            <th>Last Seen</th>
        </tr>
"""
                
                for node in nodes:
                    html_content += f"""
        <tr>
            <td>{node.hostname}</td>
            <td>{node.ip_address}</td>
            <td>{node.status or 'Unknown'}</td>
            <td>{node.cpu_cores or 'Unknown'}</td>
            <td>{node.memory_gb:.1f if node.memory_gb else 'Unknown'}</td>
            <td>{node.disk_gb:.1f if node.disk_gb else 'Unknown'}</td>
            <td>{node.cpu_usage_percent}% if node.cpu_usage_percent is not None else 'N/A'</td>
            <td>{node.memory_usage_percent}% if node.memory_usage_percent is not None else 'N/A'</td>
            <td>{node.disk_usage_percent}% if node.disk_usage_percent is not None else 'N/A'</td>
            <td>{node.last_seen.strftime('%Y-%m-%d %H:%M') if node.last_seen else 'Never'}</td>
        </tr>
"""
                
                html_content += """
    </table>
</body>
</html>
"""
                
                with open(output_file, 'w') as f:
                    f.write(html_content)
            
            print_success(f"Hardware report exported to: {output_file}")
            print(f"Format: {format.upper()}")
            print(f"Nodes included: {len(nodes)}")
            
    except Exception as e:
        print_error(f"Failed to export hardware report: {e}")

# =============================================================================
# UPS Management Commands
# =============================================================================

@cli.group()
def ups():
    """UPS (Uninterruptible Power Supply) management commands."""
    pass

@ups.command()
@click.option('--json-output', is_flag=True, help='Output in JSON format')
def scan(json_output):
    """Scan for connected UPS devices and configure them automatically."""
    from app import create_app
    from app.services.ups_controller import UPSController
    
    print_info("🔍 Scanning for UPS devices...")
    
    try:
        app = create_app()
        with app.app_context():
            controller = UPSController()
            ups_devices = controller.scan_and_configure_ups()
        
        if not ups_devices:
            print_warning("No UPS devices found")
            return
        
        if json_output:
            print(json.dumps(ups_devices, indent=2))
        else:
            print_success(f"Found and configured {len(ups_devices)} UPS device(s):")
            
            # Create table data
            table_data = []
            for ups in ups_devices:
                table_data.append([
                    ups['name'],
                    ups['model'],
                    f"{ups['vendor_id']}:{ups['product_id']}",
                    ups['driver'],
                    ups['connection_type'],
                    "✅" if ups['nut_configured'] else "❌"
                ])
            
            headers = ['Name', 'Model', 'USB ID', 'Driver', 'Connection', 'Configured']
            print(tabulate(table_data, headers=headers, tablefmt="grid"))
            
    except Exception as e:
        print_error(f"Failed to scan for UPS devices: {e}")

@ups.command()
@click.option('--json-output', is_flag=True, help='Output in JSON format')
def list(json_output):
    """List all configured UPS devices."""
    from app import create_app
    from app.services.ups_controller import UPSController
    
    try:
        app = create_app()
        with app.app_context():
            controller = UPSController()
            ups_devices = controller.get_all_ups()
        
        if not ups_devices:
            print_warning("No UPS devices configured")
            return
        
        if json_output:
            print(json.dumps(ups_devices, indent=2))
        else:
            print_info(f"Configured UPS devices ({len(ups_devices)}):")
            
            # Create table data
            table_data = []
            for ups in ups_devices:
                status_color = "✅" if ups.get('status') == 'OL' else ("🔋" if ups.get('status') == 'OB' else "❓")
                table_data.append([
                    ups['name'],
                    ups['model'] or 'Unknown',
                    ups.get('status', 'Unknown'),
                    f"{ups.get('battery_charge', 'N/A')}%" if ups.get('battery_charge') else 'N/A',
                    f"{ups.get('load_percentage', 'N/A')}%" if ups.get('load_percentage') else 'N/A',
                    "✅" if ups['nut_services_running'] else "❌"
                ])
            
            headers = ['Name', 'Model', 'Status', 'Battery', 'Load', 'Services']
            print(tabulate(table_data, headers=headers, tablefmt="grid"))
            
    except Exception as e:
        print_error(f"Failed to list UPS devices: {e}")

@ups.command()
@click.argument('ups_id', type=int)
@click.option('--json-output', is_flag=True, help='Output in JSON format')
def status(ups_id, json_output):
    """Get detailed status of a specific UPS."""
    from app import create_app
    from app.services.ups_controller import UPSController
    
    try:
        app = create_app()
        with app.app_context():
            controller = UPSController()
            status_info = controller.get_ups_status(ups_id)
        
        if 'error' in status_info:
            print_error(f"Error getting UPS status: {status_info['error']}")
            return
        
        if json_output:
            print(json.dumps(status_info, indent=2))
        else:
            ups = status_info['ups']
            status = status_info['status']
            
            print_info(f"UPS Status: {ups['name']}")
            print(f"Model: {ups['model']}")
            print(f"Status: {status.get('ups.status', 'Unknown')}")
            print(f"Battery Charge: {status.get('battery.charge', 'N/A')}%")
            print(f"Battery Voltage: {status.get('battery.voltage', 'N/A')}V")
            print(f"Runtime: {status.get('battery.runtime', 'N/A')} seconds")
            print(f"Input Voltage: {status.get('input.voltage', 'N/A')}V")
            print(f"Output Voltage: {status.get('output.voltage', 'N/A')}V")
            print(f"Load: {status.get('ups.load', 'N/A')}%")
            print(f"Temperature: {status.get('ups.temperature', 'N/A')}°C")
            
    except Exception as e:
        print_error(f"Failed to get UPS status: {e}")

@ups.command()
@click.argument('ups_id', type=int)
def test(ups_id):
    """Test connection to a UPS."""
    from app import create_app
    from app.services.ups_controller import UPSController
    
    try:
        app = create_app()
        with app.app_context():
            controller = UPSController()
            result = controller.test_ups_connection(ups_id)
        
        if result['success']:
            print_success(f"UPS connection test: {result['message']}")
        else:
            print_error(f"UPS connection test failed: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        print_error(f"Failed to test UPS connection: {e}")

@ups.command()
@click.argument('ups_id', type=int)
def remove(ups_id):
    """Remove UPS configuration."""
    from app import create_app
    from app.services.ups_controller import UPSController
    
    if not click.confirm('Are you sure you want to remove this UPS configuration?'):
        print_info("Operation cancelled")
        return
    
    try:
        app = create_app()
        with app.app_context():
            controller = UPSController()
            result = controller.remove_ups(ups_id)
        
        if result['success']:
            print_success(result['message'])
        else:
            print_error(f"Failed to remove UPS: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        print_error(f"Failed to remove UPS: {e}")

@ups.group()
def rules():
    """Power management rules for UPS-cluster integration."""
    pass

@rules.command()
@click.argument('ups_id', type=int)
@click.argument('cluster_id', type=int)
@click.argument('power_event', type=click.Choice(['power_loss', 'low_battery', 'critical_battery', 'power_restored']))
@click.argument('cluster_action', type=click.Choice(['graceful_shutdown', 'force_shutdown', 'startup', 'scale_down', 'scale_up', 'pause', 'resume']))
@click.option('--name', help='Rule name')
@click.option('--description', help='Rule description')
@click.option('--battery-threshold', type=float, help='Battery threshold percentage for low_battery events')
@click.option('--action-delay', type=int, default=0, help='Delay in seconds before executing action')
@click.option('--priority', type=int, default=100, help='Rule priority (lower = higher priority)')
@click.option('--disable', is_flag=True, help='Create rule in disabled state')
def create(ups_id, cluster_id, power_event, cluster_action, name, description, battery_threshold, action_delay, priority, disable):
    """Create a power management rule."""
    from app import create_app
    from app.services.ups_controller import UPSController
    
    try:
        app = create_app()
        with app.app_context():
            controller = UPSController()
        
        rule_kwargs = {
            'name': name or f"Rule_{power_event}_{cluster_action}",
            'description': description or '',
            'battery_threshold': battery_threshold,
            'action_delay': action_delay,
            'priority': priority,
            'enabled': not disable
        }
        
        result = controller.create_power_rule(ups_id, cluster_id, power_event, cluster_action, **rule_kwargs)
        
        if result['success']:
            print_success(result['message'])
            print(f"Rule ID: {result['rule']['id']}")
        else:
            print_error(f"Failed to create power rule: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        print_error(f"Failed to create power rule: {e}")

@rules.command('list')
@click.option('--ups-id', type=int, help='Filter by UPS ID')
@click.option('--cluster-id', type=int, help='Filter by cluster ID')
@click.option('--json-output', is_flag=True, help='Output in JSON format')
def list_rules(ups_id, cluster_id, json_output):
    """List power management rules."""
    from app import create_app
    from app.services.ups_controller import UPSController
    
    try:
        app = create_app()
        with app.app_context():
            controller = UPSController()
            rules = controller.get_power_rules(ups_id, cluster_id)
        
        if not rules:
            print_warning("No power management rules found")
            return
        
        if json_output:
            print(json.dumps(rules, indent=2))
        else:
            print_info(f"Power Management Rules ({len(rules)}):")
            
            # Create table data
            table_data = []
            for rule in rules:
                table_data.append([
                    rule['id'],
                    rule['name'],
                    rule['power_event'],
                    rule['cluster_action'],
                    rule['priority'],
                    "✅" if rule['enabled'] else "❌",
                    f"{rule['success_rate']:.1f}%" if rule['execution_count'] > 0 else 'N/A'
                ])
            
            headers = ['ID', 'Name', 'Event', 'Action', 'Priority', 'Enabled', 'Success Rate']
            print(tabulate(table_data, headers=headers, tablefmt="grid"))
            
    except Exception as e:
        print_error(f"Failed to list power rules: {e}")

@rules.command()
@click.argument('rule_id', type=int)
def delete(rule_id):
    """Delete a power management rule."""
    from app import create_app
    from app.services.ups_controller import UPSController
    
    if not click.confirm('Are you sure you want to delete this power management rule?'):
        print_info("Operation cancelled")
        return
    
    try:
        app = create_app()
        with app.app_context():
            controller = UPSController()
            result = controller.delete_power_rule(rule_id)
        
        if result['success']:
            print_success(result['message'])
        else:
            print_error(f"Failed to delete power rule: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        print_error(f"Failed to delete power rule: {e}")

@ups.command()
def install_nut():
    """Install and configure NUT packages."""
    from app import create_app
    from app.services.nut_configurator import NUTConfigurator
    
    try:
        print_info("Installing NUT packages...")
        configurator = NUTConfigurator()
        
        # Install NUT packages
        if configurator.install_nut():
            print_success("NUT packages installed successfully")
            
            # Create NUT configuration directory
            configurator.create_config_directory()
            print_success("NUT configuration directory created")
            
            print_info("NUT installation completed!")
            print_info("Run 'python cli.py ups scan' to detect and configure UPS devices")
        else:
            print_error("Failed to install NUT packages")
            
    except Exception as e:
        print_error(f"Failed to install NUT: {e}")

@ups.command()
def setup_nut():
    """Complete NUT setup (install + configure)."""
    from app import create_app
    from app.services.nut_configurator import NUTConfigurator
    from app.services.ups_controller import UPSController
    
    try:
        print_info("Starting complete NUT setup...")
        
        # Install NUT
        configurator = NUTConfigurator()
        if not configurator.install_nut():
            print_error("Failed to install NUT packages")
            return
        
        print_success("NUT packages installed")
        
        # Create config directory
        configurator.create_config_directory()
        print_success("NUT configuration directory created")
        
        # Scan and configure UPS
        app = create_app()
        with app.app_context():
            controller = UPSController(app)
            ups_devices = controller.scan_and_configure_ups()
            
            if ups_devices:
                print_success(f"Found and configured {len(ups_devices)} UPS device(s)")
                
                # Start NUT services
                if configurator.start_nut_services():
                    print_success("NUT services started")
                    print_success("NUT setup completed successfully!")
                    print_info("You can now:")
                    print_info("  - View UPS status: python cli.py ups list")
                    print_info("  - Create power rules: python cli.py ups rules create")
                    print_info("  - Start monitoring: python cli.py ups monitor start")
                else:
                    print_error("Failed to start NUT services")
            else:
                print_warning("No UPS devices found")
                print_info("Connect a UPS device and run 'python cli.py ups scan'")
                
    except Exception as e:
        print_error(f"Failed to setup NUT: {e}")

@ups.group()
def monitor():
    """Power monitoring commands."""
    pass

@monitor.command()
def start():
    """Start power event monitoring."""
    from app import create_app
    from app.services.ups_controller import UPSController
    
    try:
        app = create_app()
        with app.app_context():
            controller = UPSController()
            result = controller.start_power_monitoring()
        
        if result['success']:
            print_success(result['message'])
        else:
            print_error(f"Failed to start monitoring: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        print_error(f"Failed to start power monitoring: {e}")

@monitor.command()
def stop():
    """Stop power event monitoring."""
    from app import create_app
    from app.services.ups_controller import UPSController
    
    try:
        app = create_app()
        with app.app_context():
            controller = UPSController()
            result = controller.stop_power_monitoring()
        
        if result['success']:
            print_success(result['message'])
        else:
            print_error(f"Failed to stop monitoring: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        print_error(f"Failed to stop power monitoring: {e}")

@monitor.command()
@click.option('--json-output', is_flag=True, help='Output in JSON format')
def status(json_output):
    """Get power monitoring status."""
    from app import create_app
    from app.services.ups_controller import UPSController
    
    try:
        app = create_app()
        with app.app_context():
            controller = UPSController()
            status = controller.get_power_monitoring_status()
        
        if json_output:
            print(json.dumps(status, indent=2))
        else:
            print_info("Power Monitoring Status:")
            print(f"Monitoring Active: {'✅ Yes' if status['monitoring_active'] else '❌ No'}")
            print(f"Monitoring Interval: {status['monitoring_interval']} seconds")
            
    except Exception as e:
        print_error(f"Failed to get monitoring status: {e}")

@ups.command()
def services():
    """Check NUT service status."""
    from app import create_app
    from app.services.ups_controller import UPSController
    
    try:
        app = create_app()
        with app.app_context():
            controller = UPSController()
            result = controller.get_nut_service_status()
        
        if result['success']:
            print_info("NUT Service Status:")
            for service, running in result['services'].items():
                status = "✅ Running" if running else "❌ Stopped"
                print(f"{service.title()}: {status}")
        else:
            print_error(f"Failed to get service status: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        print_error(f"Failed to get NUT service status: {e}")

@ups.command()
def restart():
    """Restart NUT services."""
    from app import create_app
    from app.services.ups_controller import UPSController
    
    try:
        app = create_app()
        with app.app_context():
            controller = UPSController()
            result = controller.restart_nut_services()
        
        if result['success']:
            print_success(result['message'])
        else:
            print_error(f"Failed to restart services: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        print_error(f"Failed to restart NUT services: {e}")

# Wake-on-LAN commands
@cli.group()
def wol():
    """Wake-on-LAN operations for cluster nodes."""
    pass

@wol.command('wake-node')
@click.argument('node_id', type=int)
@click.option('--retries', default=3, help='Number of retry attempts')
@click.option('--delay', default=1.0, help='Delay between retries in seconds')
def wake_node(node_id, retries, delay):
    """Send Wake-on-LAN packet to a specific node."""
    try:
        from app.services.wake_on_lan import WakeOnLANService
        from app.models.database import db
        from app.models.flask_models import Node
        
        init_database()
        session = db.session
        
        node = session.query(Node).filter(Node.id == node_id).first()
        if not node:
            print_error(f"Node with ID {node_id} not found")
            return
        
        print_info(f"Waking node: {node.hostname} ({node.ip_address})")
        
        wol_service = WakeOnLANService()
        result = wol_service.wake_node(node, retries, delay)
        
        if result.get('success', False):
            packets_sent = result.get('packets_sent', 0)
            print_success(f"Successfully sent {packets_sent} Wake-on-LAN packets to {node.hostname}")
        else:
            print_error(f"Failed to wake {node.hostname}: {result.get('error', 'Unknown error')}")
        
        session.close()
        
    except Exception as e:
        print_error(f"Failed to wake node: {e}")

@wol.command('wake-cluster')
@click.argument('cluster_id', type=int)
@click.option('--retries', default=3, help='Number of retry attempts per node')
@click.option('--delay', default=1.0, help='Delay between retries in seconds')
def wake_cluster(cluster_id, retries, delay):
    """Send Wake-on-LAN packets to all nodes in a cluster."""
    try:
        from app.services.wake_on_lan import WakeOnLANService
        from app.models.database import db
        from app.models.flask_models import Cluster
        
        init_database()
        session = db.session
        
        cluster = session.query(Cluster).filter(Cluster.id == cluster_id).first()
        if not cluster:
            print_error(f"Cluster with ID {cluster_id} not found")
            return
        
        print_info(f"Waking cluster: {cluster.name}")
        
        wol_service = WakeOnLANService()
        result = wol_service.wake_cluster(cluster_id, retries, delay)
        
        if result.get('success', False):
            successful_nodes = result.get('successful_nodes', 0)
            total_nodes = result.get('total_nodes', 0)
            print_success(f"Successfully woke {successful_nodes}/{total_nodes} nodes in cluster {cluster.name}")
            
            # Show detailed results
            results = result.get('results', {})
            for hostname, node_result in results.items():
                if node_result.get('success', False):
                    packets_sent = node_result.get('packets_sent', 0)
                    print_info(f"  {hostname}: {packets_sent} packets sent")
                else:
                    error = node_result.get('error', 'Unknown error')
                    print_warning(f"  {hostname}: Failed - {error}")
        else:
            print_error(f"Failed to wake cluster {cluster.name}: {result.get('error', 'Unknown error')}")
        
        session.close()
        
    except Exception as e:
        print_error(f"Failed to wake cluster: {e}")

@wol.command('status')
@click.argument('node_id', type=int)
def wol_status(node_id):
    """Get Wake-on-LAN status for a node."""
    try:
        from app.services.wake_on_lan import WakeOnLANService
        from app.models.database import db
        from app.models.flask_models import Node
        
        init_database()
        session = db.session
        
        node = session.query(Node).filter(Node.id == node_id).first()
        if not node:
            print_error(f"Node with ID {node_id} not found")
            return
        
        print_info(f"Wake-on-LAN status for {node.hostname}:")
        
        wol_service = WakeOnLANService()
        status = wol_service.get_wol_status(node)
        
        if 'error' in status:
            print_error(f"Error getting status: {status['error']}")
            return
        
        # Display status information
        print_info(f"  Hostname: {status['hostname']}")
        print_info(f"  WoL Enabled: {'Yes' if status['wol_enabled'] else 'No'}")
        print_info(f"  WoL Configured: {'Yes' if status['wol_configured'] else 'No'}")
        print_info(f"  Description: {status['wol_description']}")
        
        if status['mac_address']:
            print_info(f"  MAC Address: {status['mac_address']}")
        
        if status['method']:
            print_info(f"  Method: {status['method']}")
        
        if status['port']:
            print_info(f"  Port: {status['port']}")
        
        if status['broadcast_address']:
            print_info(f"  Broadcast Address: {status['broadcast_address']}")
        
        if status['is_virtual_node']:
            print_warning("  Virtual Node: Yes (Proxmox VM)")
            if status.get('proxmox_vm_id'):
                print_info(f"  Proxmox VM ID: {status['proxmox_vm_id']}")
            if status.get('proxmox_host_id'):
                print_info(f"  Proxmox Host ID: {status['proxmox_host_id']}")
        
        session.close()
        
    except Exception as e:
        print_error(f"Failed to get WoL status: {e}")

@wol.command('enable')
@click.argument('node_id', type=int)
def enable_wol(node_id):
    """Enable Wake-on-LAN on a node."""
    try:
        from app.services.wake_on_lan import WakeOnLANService
        from app.models.database import db
        from app.models.flask_models import Node
        
        init_database()
        session = db.session
        
        node = session.query(Node).filter(Node.id == node_id).first()
        if not node:
            print_error(f"Node with ID {node_id} not found")
            return
        
        print_info(f"Enabling Wake-on-LAN on {node.hostname}...")
        
        wol_service = WakeOnLANService()
        result = wol_service.enable_wol_on_node(node)
        
        if result.get('success', False):
            print_success(result['message'])
        else:
            print_error(f"Failed to enable WoL: {result.get('error', 'Unknown error')}")
        
        session.close()
        
    except Exception as e:
        print_error(f"Failed to enable WoL: {e}")

@wol.command('disable')
@click.argument('node_id', type=int)
def disable_wol(node_id):
    """Disable Wake-on-LAN on a node."""
    try:
        from app.services.wake_on_lan import WakeOnLANService
        from app.models.database import db
        from app.models.flask_models import Node
        
        init_database()
        session = db.session
        
        node = session.query(Node).filter(Node.id == node_id).first()
        if not node:
            print_error(f"Node with ID {node_id} not found")
            return
        
        print_info(f"Disabling Wake-on-LAN on {node.hostname}...")
        
        wol_service = WakeOnLANService()
        result = wol_service.disable_wol_on_node(node)
        
        if result.get('success', False):
            print_success(result['message'])
        else:
            print_error(f"Failed to disable WoL: {result.get('error', 'Unknown error')}")
        
        session.close()
        
    except Exception as e:
        print_error(f"Failed to disable WoL: {e}")

@wol.command('collect-mac')
@click.option('--node-ids', help='Comma-separated list of node IDs (default: all nodes)')
def collect_mac_addresses(node_ids):
    """Collect MAC addresses from nodes."""
    try:
        from app.services.wake_on_lan import WakeOnLANService
        from app.models.database import db
        from app.models.flask_models import Node
        
        init_database()
        session = db.session
        
        # Parse node IDs
        if node_ids:
            try:
                node_id_list = [int(id.strip()) for id in node_ids.split(',')]
                nodes = session.query(Node).filter(Node.id.in_(node_id_list)).all()
            except ValueError:
                print_error("Invalid node IDs format. Use comma-separated integers.")
                return
        else:
            nodes = session.query(Node).all()
        
        if not nodes:
            print_warning("No nodes found")
            return
        
        print_info(f"Collecting MAC addresses from {len(nodes)} nodes...")
        
        wol_service = WakeOnLANService()
        result = wol_service.collect_mac_addresses(nodes)
        
        # Display results
        for hostname, node_result in result.items():
            if node_result.get('success', False):
                mac_addresses = node_result.get('mac_addresses', [])
                print_success(f"{hostname}: Found {len(mac_addresses)} interfaces")
                
                for mac_info in mac_addresses:
                    interface = mac_info.get('interface', 'Unknown')
                    mac = mac_info.get('mac_address', 'Unknown')
                    print_info(f"  {interface}: {mac}")
            else:
                error = node_result.get('error', 'Unknown error')
                print_error(f"{hostname}: Failed - {error}")
        
        session.close()
        
    except Exception as e:
        print_error(f"Failed to collect MAC addresses: {e}")

@wol.command('configure')
@click.argument('node_id', type=int)
@click.option('--mac-address', help='MAC address for Wake-on-LAN')
@click.option('--method', default='ethernet', help='Wake method (ethernet, wifi, pci, usb)')
@click.option('--port', default=9, help='UDP port for Wake-on-LAN packets')
@click.option('--broadcast', help='Broadcast address (default: 255.255.255.255)')
@click.option('--enable/--disable', default=None, help='Enable or disable Wake-on-LAN')
@click.option('--virtual/--physical', default=None, help='Mark as virtual or physical node')
@click.option('--proxmox-vm-id', help='Proxmox VM ID (for virtual nodes)')
@click.option('--proxmox-host-id', help='Proxmox host ID (for virtual nodes)')
def configure_wol(node_id, mac_address, method, port, broadcast, enable, virtual, proxmox_vm_id, proxmox_host_id):
    """Configure Wake-on-LAN settings for a node."""
    try:
        from app.models.database import db
        from app.models.flask_models import Node
        
        init_database()
        session = db.session
        
        node = session.query(Node).filter(Node.id == node_id).first()
        if not node:
            print_error(f"Node with ID {node_id} not found")
            return
        
        print_info(f"Configuring Wake-on-LAN for {node.hostname}...")
        
        # Update configuration
        if mac_address is not None:
            node.wol_mac_address = mac_address
            print_info(f"  Set MAC address: {mac_address}")
        
        if method is not None:
            node.wol_method = method
            print_info(f"  Set method: {method}")
        
        if port is not None:
            node.wol_port = port
            print_info(f"  Set port: {port}")
        
        if broadcast is not None:
            node.wol_broadcast_address = broadcast
            print_info(f"  Set broadcast address: {broadcast}")
        
        if enable is not None:
            node.wol_enabled = enable
            print_info(f"  {'Enabled' if enable else 'Disabled'} Wake-on-LAN")
        
        if virtual is not None:
            node.is_virtual_node = virtual
            print_info(f"  Marked as {'virtual' if virtual else 'physical'} node")
        
        if proxmox_vm_id is not None:
            node.proxmox_vm_id = proxmox_vm_id
            print_info(f"  Set Proxmox VM ID: {proxmox_vm_id}")
        
        if proxmox_host_id is not None:
            node.proxmox_host_id = proxmox_host_id
            print_info(f"  Set Proxmox host ID: {proxmox_host_id}")
        
        # Commit changes
        session.commit()
        
        print_success(f"Wake-on-LAN configuration updated for {node.hostname}")
        
        # Show current configuration
        print_info("Current configuration:")
        print_info(f"  WoL Enabled: {node.wol_enabled}")
        print_info(f"  WoL Configured: {node.wol_configured}")
        print_info(f"  Description: {node.wol_description}")
        
        session.close()
        
    except Exception as e:
        print_error(f"Failed to configure WoL: {e}")
        session.rollback()

# Playbook Management Commands
@cli.group()
def playbook():
    """Manage playbooks and templates."""
    pass

@playbook.command()
def list_templates():
    """List available playbook templates."""
    try:
        from app import create_app
        from app.services.playbook_service import PlaybookService
        
        app = create_app()
        with app.app_context():
            service = PlaybookService()
            templates = service.get_templates()
            
            if not templates:
                print_info("No templates found.")
                return
            
            data = []
            for template in templates:
                data.append([
                    template.id,
                    template.name,
                    template.category,
                    template.version,
                    template.usage_count,
                    "System" if template.is_system else "User"
                ])
            
            headers = ["ID", "Name", "Category", "Version", "Uses", "Type"]
            print(tabulate(data, headers=headers, tablefmt="grid"))
            
    except Exception as e:
        print_error(f"Failed to list templates: {e}")

@playbook.command()
@click.argument('template_id', type=int)
def show_template(template_id):
    """Show details of a specific template."""
    try:
        from app import create_app
        from app.services.playbook_service import PlaybookService
        
        app = create_app()
        with app.app_context():
            service = PlaybookService()
            template = service.get_template(template_id)
            
            if not template:
                print_error(f"Template {template_id} not found.")
                return
            
            print_info(f"Template: {template.name}")
            print_info(f"Category: {template.category}")
            print_info(f"Description: {template.description or 'No description'}")
            print_info(f"Version: {template.version}")
            print_info(f"Usage Count: {template.usage_count}")
            print_info(f"Type: {'System' if template.is_system else 'User'}")
            print_info(f"Created: {template.created_at}")
            
            if template.tags:
                print_info(f"Tags: {template.tags}")
            
            print_info("\nYAML Content:")
            print(template.yaml_content)
            
    except Exception as e:
        print_error(f"Failed to show template: {e}")

@playbook.command()
def list_custom():
    """List custom playbooks."""
    try:
        from app import create_app
        from app.services.playbook_service import PlaybookService
        
        app = create_app()
        with app.app_context():
            service = PlaybookService()
            playbooks = service.get_custom_playbooks()
            
            if not playbooks:
                print_info("No custom playbooks found.")
                return
            
            data = []
            for playbook in playbooks:
                data.append([
                    playbook.id,
                    playbook.name,
                    playbook.category,
                    playbook.execution_count,
                    f"{playbook.success_rate:.1f}%" if playbook.success_rate > 0 else "N/A",
                    playbook.created_at.strftime("%Y-%m-%d")
                ])
            
            headers = ["ID", "Name", "Category", "Executions", "Success Rate", "Created"]
            print(tabulate(data, headers=headers, tablefmt="grid"))
            
    except Exception as e:
        print_error(f"Failed to list custom playbooks: {e}")

@playbook.command()
def list_executions():
    """List playbook executions."""
    try:
        from app import create_app
        from app.services.playbook_service import PlaybookService
        
        app = create_app()
        with app.app_context():
            service = PlaybookService()
            executions = service.get_executions()
            
            if not executions:
                print_info("No executions found.")
                return
            
            data = []
            for execution in executions:
                status_color = {
                    'pending': Fore.YELLOW,
                    'running': Fore.BLUE,
                    'completed': Fore.GREEN,
                    'failed': Fore.RED,
                    'cancelled': Fore.YELLOW
                }.get(execution.status, '')
                
                status_text = f"{status_color}{execution.status}{Style.RESET_ALL}"
                
                data.append([
                    execution.id,
                    execution.execution_name,
                    execution.execution_type,
                    status_text,
                    f"{execution.progress_percent}%" if execution.progress_percent > 0 else "N/A",
                    execution.created_at.strftime("%Y-%m-%d %H:%M")
                ])
            
            headers = ["ID", "Name", "Type", "Status", "Progress", "Created"]
            print(tabulate(data, headers=headers, tablefmt="grid"))
            
    except Exception as e:
        print_error(f"Failed to list executions: {e}")

@playbook.command()
@click.argument('execution_id', type=int)
def show_execution(execution_id):
    """Show details of a specific execution."""
    try:
        from app import create_app
        from app.services.playbook_service import PlaybookService
        
        app = create_app()
        with app.app_context():
            service = PlaybookService()
            execution = service.get_execution(execution_id)
            
            if not execution:
                print_error(f"Execution {execution_id} not found.")
                return
            
            print_info(f"Execution: {execution.execution_name}")
            print_info(f"Type: {execution.execution_type}")
            print_info(f"Status: {execution.status}")
            print_info(f"Progress: {execution.progress_percent}%")
            print_info(f"Created: {execution.created_at}")
            
            if execution.started_at:
                print_info(f"Started: {execution.started_at}")
            if execution.completed_at:
                print_info(f"Completed: {execution.completed_at}")
            if execution.duration:
                print_info(f"Duration: {execution.duration:.1f} seconds")
            
            if execution.error_message:
                print_error(f"Error: {execution.error_message}")
            
            if execution.output:
                print_info("\nOutput:")
                print(execution.output)
            
    except Exception as e:
        print_error(f"Failed to show execution: {e}")

@playbook.command()
def init_templates():
    """Initialize system templates."""
    try:
        from app import create_app
        from app.services.playbook_service import PlaybookService
        
        app = create_app()
        with app.app_context():
            service = PlaybookService()
            service.create_system_templates()
            print_success("System templates initialized successfully.")
            
    except Exception as e:
        print_error(f"Failed to initialize templates: {e}")

if __name__ == '__main__':
    cli()
