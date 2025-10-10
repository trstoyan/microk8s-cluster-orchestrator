"""
Sync Web Controller
Web interface for interactive sync operations
"""

from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, Response, stream_with_context
from flask_login import login_required
import requests
import json
import time

from app.services.sync_service import SyncService
from app.utils.progress_logger import get_progress_logger

sync_web_bp = Blueprint('sync_web', __name__, url_prefix='/sync')


@sync_web_bp.route('/')
@login_required
def index():
    """Sync dashboard - main page"""
    return render_template('sync/index.html')


@sync_web_bp.route('/connect', methods=['GET', 'POST'])
@login_required
def connect():
    """Connect to remote server"""
    if request.method == 'POST':
        data = request.get_json()
        remote_url = data.get('remote_url')
        password = data.get('password', '')
        
        if not remote_url:
            return jsonify({'error': 'Remote URL is required'}), 400
        
        try:
            # Initialize sync service
            sync_service = SyncService(remote_url=remote_url)
            
            # Test connection
            response = requests.get(f"{remote_url}/api/v1/sync/test", timeout=10)
            
            if response.status_code == 200:
                return jsonify({
                    'success': True,
                    'message': 'Successfully connected to remote server',
                    'server_info': response.json()
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Failed to connect to remote server'
                }), 400
        
        except requests.RequestException as e:
            return jsonify({
                'success': False,
                'error': f'Connection failed: {str(e)}'
            }), 500
    
    return render_template('sync/connect.html')


@sync_web_bp.route('/compare', methods=['POST'])
@login_required
def compare():
    """Compare inventories"""
    import logging
    logger = logging.getLogger(__name__)
    
    data = request.get_json()
    remote_url = data.get('remote_url')
    remote_username = data.get('username', '')
    remote_password = data.get('password', '')
    
    logger.info(f"[SYNC] Starting comparison with remote: {remote_url}")
    logger.info(f"[SYNC] Remote username: {remote_username}")
    
    if not remote_url:
        logger.error("[SYNC] No remote URL provided")
        return jsonify({'error': 'Remote URL is required'}), 400
    
    if not remote_username or not remote_password:
        logger.error("[SYNC] Missing authentication credentials")
        return jsonify({'error': 'Remote server username and password required'}), 400
    
    # Create a session for requests to remote server
    session = requests.Session()
    
    try:
        # Step 1: Login to remote server
        logger.info(f"[SYNC] Step 1: Logging in to {remote_url}/auth/login")
        login_response = session.post(
            f"{remote_url}/auth/login",
            data={
                'username': remote_username,
                'password': remote_password
            },
            timeout=10,
            allow_redirects=False
        )
        logger.info(f"[SYNC] Login response status: {login_response.status_code}")
        
        if login_response.status_code not in [200, 302]:
            logger.error(f"[SYNC] Login failed: {login_response.status_code}")
            return jsonify({
                'success': False,
                'error': f'Failed to login to remote server (status: {login_response.status_code}). Check username/password.'
            }), 401
        
        logger.info("[SYNC] ✅ Logged in successfully to remote server")
        
        # Step 2: Get remote inventory (using session cookies)
        logger.info(f"[SYNC] Step 2: Fetching remote inventory from {remote_url}/api/system/nodes")
        
        # Fetch nodes from remote
        nodes_response = session.get(f"{remote_url}/api/nodes", timeout=30)
        logger.info(f"[SYNC] Nodes response: {nodes_response.status_code}")
        
        # Fetch clusters from remote  
        clusters_response = session.get(f"{remote_url}/api/clusters", timeout=30)
        logger.info(f"[SYNC] Clusters response: {clusters_response.status_code}")
        
        if nodes_response.status_code == 200 and clusters_response.status_code == 200:
            remote_nodes = nodes_response.json()
            remote_clusters = clusters_response.json()
            
            remote_inv = {
                'metadata': {
                    'server_url': remote_url,
                    'timestamp': None
                },
                'nodes': remote_nodes if isinstance(remote_nodes, list) else [],
                'clusters': remote_clusters if isinstance(remote_clusters, list) else [],
                'ssh_keys': [],
                'stats': {
                    'total_nodes': len(remote_nodes) if isinstance(remote_nodes, list) else 0,
                    'total_clusters': len(remote_clusters) if isinstance(remote_clusters, list) else 0,
                    'total_ssh_keys': 0
                }
            }
            logger.info(f"[SYNC] Remote inventory: {remote_inv.get('stats', {})}")
        else:
            logger.error(f"[SYNC] Failed to fetch inventory")
            return jsonify({
                'success': False,
                'error': f'Failed to fetch remote data'
            }), 500
        
        # Step 3: Get local inventory
        logger.info("[SYNC] Step 3: Getting local inventory")
        sync_service = SyncService(remote_url=remote_url)
        local_inv = sync_service.get_local_inventory()
        logger.info(f"[SYNC] Local inventory: {local_inv.get('stats', {})}")
        
        # Step 4: Compare
        logger.info("[SYNC] Step 4: Comparing inventories")
        comparison = sync_service.compare_inventories(local_inv, remote_inv)
        logger.info(f"[SYNC] Comparison summary: {comparison.get('summary', {})}")
        
        return jsonify({
            'success': True,
            'comparison': comparison,
            'logs': [
                f"✅ Logged in to {remote_url} as {remote_username}",
                f"✅ Retrieved {len(remote_inv.get('nodes', []))} nodes, {len(remote_inv.get('clusters', []))} clusters from remote",
                f"✅ Local: {len(local_inv.get('nodes', []))} nodes, {len(local_inv.get('clusters', []))} clusters",
                f"✅ Comparison complete: {comparison.get('summary', {}).get('different', 0)} differences found"
            ]
        })
    
    except requests.RequestException as e:
        return jsonify({
            'success': False,
            'error': f'Connection error: {str(e)}'
        }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@sync_web_bp.route('/transfer', methods=['POST'])
@login_required
def transfer():
    """Transfer selected items"""
    data = request.get_json()
    remote_url = data.get('remote_url')
    selected_items = data.get('selected_items', {})
    
    if not remote_url:
        return jsonify({'error': 'Remote URL is required'}), 400
    
    try:
        sync_service = SyncService(remote_url=remote_url)
        
        # Create sync package
        package = sync_service.create_sync_package(selected_items)
        
        # Send to remote server
        response = requests.post(
            f"{remote_url}/api/v1/sync/receive",
            json={'package': package, 'encrypted': True},
            headers={'Authorization': f'Bearer {sync_service.api_token}'},
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            return jsonify({
                'success': True,
                'message': 'Sync completed successfully',
                'results': result
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Transfer failed'
            }), 500
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@sync_web_bp.route('/interactive')
@login_required
def interactive():
    """Interactive sync page with comparison and selection"""
    return render_template('sync/interactive.html')


@sync_web_bp.route('/api/transfer', methods=['POST'])
@login_required
def api_transfer():
    """
    Transfer selected items to remote server with progress logging
    """
    import logging
    logger = logging.getLogger(__name__)
    progress = get_progress_logger()
    
    data = request.get_json()
    remote_url = data.get('remote_url', '').strip()
    remote_username = data.get('remote_username')
    remote_password = data.get('remote_password')
    selected_items = data.get('selected_items', {})
    
    if not remote_url:
        return jsonify({'success': False, 'error': 'Remote URL required'}), 400
    
    # Start operation with unique ID
    import uuid
    operation_id = str(uuid.uuid4())[:8]
    progress.start_operation(operation_id)
    
    try:
        # Ensure URL has protocol
        if not remote_url.startswith('http://') and not remote_url.startswith('https://'):
            remote_url = 'http://' + remote_url
        remote_url = remote_url.rstrip('/')
        
        progress.info(f'📦 Preparing to transfer {len(selected_items.get("nodes", []))} nodes, {len(selected_items.get("clusters", []))} clusters')
        
        # Login to remote server
        progress.info(f'🔐 Connecting to {remote_url}...')
        session = requests.Session()
        
        login_response = session.post(
            f"{remote_url}/auth/login",
            data={'username': remote_username, 'password': remote_password},
            timeout=10,
            allow_redirects=False
        )
        
        if login_response.status_code not in [200, 302]:
            progress.error(f'❌ Login failed (status {login_response.status_code})')
            return jsonify({'success': False, 'error': 'Authentication failed'}), 401
        
        progress.success('✅ Connected and authenticated')
        
        # Get selected items from local database
        from app.models.flask_models import Node, Cluster
        
        sync_data = {
            'nodes': [],
            'clusters': []
        }
        
        # Fetch selected nodes
        if selected_items.get('nodes'):
            progress.info(f'📤 Fetching {len(selected_items["nodes"])} nodes from local database...')
            for node_id in selected_items['nodes']:
                node = Node.query.get(int(node_id))
                if node:
                    sync_data['nodes'].append({
                        'hostname': node.hostname,
                        'ip_address': node.ip_address,
                        'ssh_user': node.ssh_user,
                        'ssh_port': node.ssh_port,
                        'cluster_id': node.cluster_id,
                        'notes': node.notes,
                        'tags': node.tags
                    })
            progress.success(f'✅ Prepared {len(sync_data["nodes"])} nodes for transfer')
        
        # Fetch selected clusters
        if selected_items.get('clusters'):
            progress.info(f'📤 Fetching {len(selected_items["clusters"])} clusters from local database...')
            for cluster_id in selected_items['clusters']:
                cluster = Cluster.query.get(int(cluster_id))
                if cluster:
                    sync_data['clusters'].append({
                        'name': cluster.name,
                        'description': cluster.description,
                        'ha_enabled': cluster.ha_enabled,
                        'network_cidr': cluster.network_cidr,
                        'service_cidr': cluster.service_cidr
                    })
            progress.success(f'✅ Prepared {len(sync_data["clusters"])} clusters for transfer')
        
        # Transfer nodes to remote
        if sync_data['nodes']:
            progress.info(f'⬆️ Transferring {len(sync_data["nodes"])} nodes to remote server...')
            for idx, node_data in enumerate(sync_data['nodes'], 1):
                progress.info(f'  └─ [{idx}/{len(sync_data["nodes"])}] Transferring node: {node_data["hostname"]}')
                try:
                    response = session.post(
                        f"{remote_url}/api/nodes",
                        json=node_data,
                        timeout=30
                    )
                    if response.status_code in [200, 201]:
                        progress.success(f'    ✅ {node_data["hostname"]} transferred')
                    else:
                        progress.warning(f'    ⚠️ {node_data["hostname"]} may already exist (status {response.status_code})')
                except Exception as e:
                    progress.error(f'    ❌ Failed to transfer {node_data["hostname"]}: {str(e)}')
        
        # Transfer clusters to remote
        if sync_data['clusters']:
            progress.info(f'⬆️ Transferring {len(sync_data["clusters"])} clusters to remote server...')
            for idx, cluster_data in enumerate(sync_data['clusters'], 1):
                progress.info(f'  └─ [{idx}/{len(sync_data["clusters"])}] Transferring cluster: {cluster_data["name"]}')
                try:
                    response = session.post(
                        f"{remote_url}/api/clusters",
                        json=cluster_data,
                        timeout=30
                    )
                    if response.status_code in [200, 201]:
                        progress.success(f'    ✅ {cluster_data["name"]} transferred')
                    else:
                        progress.warning(f'    ⚠️ {cluster_data["name"]} may already exist (status {response.status_code})')
                except Exception as e:
                    progress.error(f'    ❌ Failed to transfer {cluster_data["name"]}: {str(e)}')
        
        progress.complete(f'Transfer completed! {len(sync_data["nodes"])} nodes, {len(sync_data["clusters"])} clusters')
        
        return jsonify({
            'success': True,
            'transferred': {
                'nodes': len(sync_data['nodes']),
                'clusters': len(sync_data['clusters'])
            }
        })
        
    except Exception as e:
        logger.error(f"[SYNC] Transfer error: {str(e)}")
        progress.error(f'❌ Transfer failed: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500


@sync_web_bp.route('/api/progress-stream')
@login_required
def progress_stream():
    """
    Server-Sent Events endpoint for live progress updates
    """
    def generate():
        progress = get_progress_logger()
        client_queue = progress.subscribe()
        
        try:
            while True:
                # Wait for new log entry (with timeout)
                try:
                    log_entry = client_queue.get(timeout=30)
                    yield f"data: {json.dumps(log_entry)}\n\n"
                except:
                    # Send keepalive
                    yield f": keepalive\n\n"
        finally:
            progress.unsubscribe(client_queue)
    
    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no'
        }
    )

