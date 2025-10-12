"""
Sync Web Controller
Web interface for interactive sync operations
"""

from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, Response, stream_with_context
from flask_login import login_required
import requests
import json
import time
import traceback

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
        logger.info(f"[SYNC] Nodes response headers: {dict(nodes_response.headers)}")
        
        # Fetch clusters from remote  
        clusters_response = session.get(f"{remote_url}/api/clusters", timeout=30)
        logger.info(f"[SYNC] Clusters response: {clusters_response.status_code}")
        
        if nodes_response.status_code == 200 and clusters_response.status_code == 200:
            try:
                # Log response content for debugging
                logger.info(f"[SYNC] Nodes response content length: {len(nodes_response.content)}")
                logger.info(f"[SYNC] Nodes response content type: {nodes_response.headers.get('Content-Type')}")
                logger.info(f"[SYNC] Nodes response first 500 chars: {nodes_response.text[:500]}")
                
                # Try to parse JSON
                try:
                    remote_nodes = nodes_response.json()
                    logger.info(f"[SYNC] ✅ Parsed {len(remote_nodes)} nodes from remote")
                except ValueError as json_err:
                    logger.error(f"[SYNC] Failed to parse nodes JSON: {json_err}")
                    logger.error(f"[SYNC] Full response text: {nodes_response.text}")
                    raise
                
                remote_clusters = clusters_response.json()
                logger.info(f"[SYNC] ✅ Parsed {len(remote_clusters)} clusters from remote")
                
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
            except ValueError as e:
                logger.error(f"[SYNC] JSON parsing error: {str(e)}")
                logger.error(f"[SYNC] Response content: {nodes_response.text[:500]}")
                return jsonify({
                    'success': False,
                    'error': f'Failed to parse remote data: {str(e)}'
                }), 500
        else:
            logger.error(f"[SYNC] Failed to fetch inventory. Nodes: {nodes_response.status_code}, Clusters: {clusters_response.status_code}")
            logger.error(f"[SYNC] Nodes response: {nodes_response.text[:200]}")
            logger.error(f"[SYNC] Clusters response: {clusters_response.text[:200]}")
            return jsonify({
                'success': False,
                'error': f'Failed to fetch remote data (Nodes: {nodes_response.status_code}, Clusters: {clusters_response.status_code})'
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
        logger.error(f"[SYNC] Connection error: {str(e)}")
        logger.error(f"[SYNC] Traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': f'Connection error: {str(e)}'
        }), 500
    except Exception as e:
        logger.error(f"[SYNC] Unexpected error: {str(e)}")
        logger.error(f"[SYNC] Traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': f'Connection error: {str(e)}'
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


@sync_web_bp.route('/interactive-bare')
@login_required
def interactive_bare():
    """Interactive sync page without base layout (for iframe embedding)"""
    return render_template('sync/interactive_bare.html')


@sync_web_bp.route('/api/transfer', methods=['POST', 'OPTIONS'])
def api_transfer():
    """
    Transfer selected items to remote server with progress logging.
    Runs in background thread to allow live progress streaming.
    Note: Manually checks authentication instead of @login_required decorator
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # Handle OPTIONS request for CORS preflight
    if request.method == 'OPTIONS':
        logger.info("[SYNC] Handling OPTIONS preflight request")
        return '', 204
    
    # Manual authentication check (instead of @login_required which causes 302 redirect)
    from flask_login import current_user
    if not current_user.is_authenticated:
        logger.warning(f"[SYNC] Unauthenticated transfer attempt from {request.remote_addr}")
        return jsonify({'success': False, 'error': 'Authentication required'}), 401
    
    logger.info(f"[SYNC] Authenticated user: {current_user.username}")
    
    import threading
    progress = get_progress_logger()
    
    data = request.get_json()
    logger.info(f"[SYNC] Received transfer request data: {list(data.keys()) if data else 'None'}")
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
    
    logger.info(f"[SYNC] Starting transfer operation {operation_id}")
    logger.info(f"[SYNC] Remote URL: {remote_url}, Username: {remote_username}")
    logger.info(f"[SYNC] Selected items: {len(selected_items.get('nodes', []))} nodes, {len(selected_items.get('clusters', []))} clusters")
    progress.info(f'🚀 Starting sync operation {operation_id}...')
    
    # Get Flask app for background thread
    app = current_app._get_current_object()
    
    # Run transfer in background thread
    def run_transfer():
        logger.info(f"[SYNC] Background thread started for operation {operation_id}")
        try:
            _execute_transfer(app, operation_id, remote_url, remote_username, remote_password, selected_items, progress, logger)
        except Exception as e:
            logger.error(f"[SYNC] Background transfer exception: {str(e)}")
            logger.error(f"[SYNC] Traceback:", exc_info=True)
            progress.error(f'❌ Transfer failed: {str(e)}')
    
    thread = threading.Thread(target=run_transfer, daemon=True, name=f"sync-{operation_id}")
    thread.start()
    logger.info(f"[SYNC] Background thread started: {thread.name}, is_alive={thread.is_alive()}")
    
    # Return immediately so client can start listening to SSE
    return jsonify({
        'success': True,
        'operation_id': operation_id,
        'message': 'Transfer started - connect to progress stream to monitor'
    })


def _execute_transfer(app, operation_id, remote_url, remote_username, remote_password, selected_items, progress, logger):
    """Execute the actual transfer logic in background"""
    logger.info(f"[SYNC-THREAD] Thread executing for operation {operation_id}")
    
    # Need to work within Flask app context for database access
    from app.models.database import db
    
    with app.app_context():
        try:
            logger.info(f"[SYNC-THREAD] Entered app context")
            
            # Ensure URL has protocol and no trailing slash
            if not remote_url.startswith('http://') and not remote_url.startswith('https://'):
                remote_url = 'http://' + remote_url
            remote_url = remote_url.rstrip('/')
            
            logger.info(f"[SYNC-THREAD] Normalized remote URL: {remote_url}")
            progress.info(f'📦 Preparing to transfer {len(selected_items.get("nodes", []))} nodes, {len(selected_items.get("clusters", []))} clusters')
            
            # Login to remote server
            progress.info(f'🔐 Connecting to {remote_url}...')
            session = requests.Session()
            
            login_url = f"{remote_url}/auth/login"
            logger.info(f"[SYNC-THREAD] Attempting login to: {login_url}")
            
            login_response = session.post(
                login_url,
                data={'username': remote_username, 'password': remote_password},
                timeout=10,
                allow_redirects=False
            )
            
            logger.info(f"[SYNC-THREAD] Login response: {login_response.status_code}")
            
            if login_response.status_code not in [200, 302]:
                progress.error(f'❌ Login failed (status {login_response.status_code})')
                logger.error(f"[SYNC-THREAD] Login failed with status {login_response.status_code}")
                return
            
            progress.success('✅ Connected and authenticated')
            logger.info(f"[SYNC-THREAD] Successfully authenticated")
            
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
            
            progress.complete(f'🎉 Transfer completed! {len(sync_data["nodes"])} nodes, {len(sync_data["clusters"])} clusters')
            logger.info(f"[SYNC] Transfer operation {operation_id} completed successfully")
            
        except Exception as e:
            logger.error(f"[SYNC] Transfer error in operation {operation_id}: {str(e)}")
            progress.error(f'❌ Transfer failed: {str(e)}')


@sync_web_bp.route('/api/sync-status')
@login_required
def get_sync_status():
    """
    Get current sync operation status
    """
    progress = get_progress_logger()
    status = progress.get_status()
    
    return jsonify({
        'success': True,
        'sync_in_progress': status['is_running'],
        'operation_id': status['operation_id'],
        'status': status['status'],
        'duration': status['duration'],
        'log_count': status['log_count']
    })


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

