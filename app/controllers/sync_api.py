"""
Sync API Controller
REST API endpoints for live data synchronization
"""

from flask import Blueprint, request, jsonify, current_app
from flask_cors import CORS
from functools import wraps
import secrets

from app.services.sync_service import SyncService
from app.utils.encryption import SyncToken, SyncEncryption

sync_bp = Blueprint('sync_api', __name__, url_prefix='/api/v1/sync')

# Enable CORS for sync API (allows cross-origin requests between orchestrator instances)
CORS(sync_bp, resources={r"/*": {"origins": "*", "methods": ["GET", "POST", "OPTIONS"]}})

# Token manager (in production, use Redis or database)
token_manager = SyncToken()

# Active sync sessions
active_sessions = {}


def require_sync_token(f):
    """Decorator to require valid sync token"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Missing or invalid authorization header'}), 401
        
        token = auth_header.split(' ')[1]
        
        if not token_manager.validate_token(token):
            return jsonify({'error': 'Invalid or expired token'}), 401
        
        # Add token info to request
        request.sync_token_info = token_manager.get_token_info(token)
        
        return f(*args, **kwargs)
    
    return decorated_function


@sync_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'sync-api',
        'version': '1.0.0'
    })


@sync_bp.route('/connect', methods=['POST'])
def connect():
    """
    Establish sync connection
    
    Request body:
    {
        "server_id": "unique_server_identifier",
        "password": "optional_encryption_password"
    }
    
    Returns:
    {
        "token": "sync_token",
        "expires_in": 3600,
        "server_info": {...}
    }
    """
    data = request.get_json()
    
    if not data or 'server_id' not in data:
        return jsonify({'error': 'Missing server_id'}), 400
    
    server_id = data['server_id']
    password = data.get('password')
    
    # Generate sync token
    token = token_manager.create_token(server_id, expires_in=3600)
    
    # Create sync session
    session_id = secrets.token_urlsafe(16)
    active_sessions[session_id] = {
        'server_id': server_id,
        'token': token,
        'encryption': SyncEncryption(password) if password else None
    }
    
    return jsonify({
        'success': True,
        'token': token,
        'session_id': session_id,
        'expires_in': 3600,
        'server_info': {
            'name': 'MicroK8s Orchestrator',
            'version': '1.0.0',
            'capabilities': ['nodes', 'clusters', 'ssh_keys', 'configs']
        }
    })


@sync_bp.route('/inventory', methods=['GET'])
@require_sync_token
def get_inventory():
    """
    Get server inventory
    
    Returns all nodes, clusters, and configurations
    """
    try:
        sync_service = SyncService()
        inventory = sync_service.get_local_inventory()
        
        return jsonify({
            'success': True,
            'inventory': inventory
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@sync_bp.route('/compare', methods=['POST'])
@require_sync_token
def compare():
    """
    Compare local inventory with remote
    
    Request body:
    {
        "remote_inventory": {...}
    }
    
    Returns:
    {
        "comparison": {
            "summary": {...},
            "nodes": {...},
            "clusters": {...}
        }
    }
    """
    data = request.get_json()
    
    if not data or 'remote_inventory' not in data:
        return jsonify({'error': 'Missing remote_inventory'}), 400
    
    try:
        sync_service = SyncService()
        local_inventory = sync_service.get_local_inventory()
        remote_inventory = data['remote_inventory']
        
        comparison = sync_service.compare_inventories(local_inventory, remote_inventory)
        
        return jsonify({
            'success': True,
            'comparison': comparison
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@sync_bp.route('/transfer', methods=['POST'])
@require_sync_token
def transfer():
    """
    Transfer selected items
    
    Request body:
    {
        "session_id": "session_id",
        "items": {
            "nodes": [...],
            "clusters": [...],
            "ssh_keys": [...]
        },
        "encrypted": true
    }
    
    Returns:
    {
        "package": {...},  // encrypted or plain
        "checksum": "..."
    }
    """
    data = request.get_json()
    
    if not data or 'items' not in data:
        return jsonify({'error': 'Missing items to transfer'}), 400
    
    try:
        session_id = data.get('session_id')
        items_to_sync = data['items']
        encrypted = data.get('encrypted', True)
        
        sync_service = SyncService()
        
        if encrypted and session_id and session_id in active_sessions:
            encryption = active_sessions[session_id].get('encryption')
            if encryption:
                sync_service.encryption = encryption
        
        package = sync_service.create_sync_package(items_to_sync)
        
        return jsonify({
            'success': True,
            'package': package,
            'encrypted': encrypted
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@sync_bp.route('/receive', methods=['POST'])
@require_sync_token
def receive():
    """
    Receive and apply sync package
    
    Request body:
    {
        "session_id": "session_id",
        "package": {...},
        "encrypted": true
    }
    
    Returns:
    {
        "success": true,
        "applied": {...},
        "errors": [...]
    }
    """
    data = request.get_json()
    
    if not data or 'package' not in data:
        return jsonify({'error': 'Missing package data'}), 400
    
    try:
        session_id = data.get('session_id')
        package = data['package']
        encrypted = data.get('encrypted', True)
        
        sync_service = SyncService()
        
        if encrypted and session_id and session_id in active_sessions:
            encryption = active_sessions[session_id].get('encryption')
            if encryption:
                sync_service.encryption = encryption
        
        results = sync_service.apply_sync_package(package)
        
        return jsonify(results)
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@sync_bp.route('/status', methods=['GET'])
@require_sync_token
def sync_status():
    """Get sync operation status"""
    return jsonify({
        'success': True,
        'active_sessions': len(active_sessions),
        'sessions': [
            {
                'session_id': sid,
                'server_id': session['server_id']
            }
            for sid, session in active_sessions.items()
        ]
    })


@sync_bp.route('/disconnect', methods=['POST'])
@require_sync_token
def disconnect():
    """
    Disconnect sync session
    
    Request body:
    {
        "session_id": "session_id"
    }
    """
    data = request.get_json()
    session_id = data.get('session_id')
    
    if session_id and session_id in active_sessions:
        # Revoke token
        token = active_sessions[session_id]['token']
        token_manager.revoke_token(token)
        
        # Remove session
        del active_sessions[session_id]
        
        return jsonify({
            'success': True,
            'message': 'Session disconnected'
        })
    
    return jsonify({
        'success': False,
        'error': 'Session not found'
    }), 404


@sync_bp.route('/test', methods=['GET'])
def test_endpoint():
    """Test endpoint (no auth required)"""
    return jsonify({
        'message': 'Sync API is working!',
        'endpoints': [
            'POST /api/v1/sync/connect',
            'GET  /api/v1/sync/inventory',
            'POST /api/v1/sync/compare',
            'POST /api/v1/sync/transfer',
            'POST /api/v1/sync/receive',
            'GET  /api/v1/sync/status',
            'POST /api/v1/sync/disconnect'
        ]
    })


# Error handlers
@sync_bp.errorhandler(400)
def bad_request(error):
    return jsonify({'error': 'Bad request', 'message': str(error)}), 400


@sync_bp.errorhandler(401)
def unauthorized(error):
    return jsonify({'error': 'Unauthorized', 'message': str(error)}), 401


@sync_bp.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error', 'message': str(error)}), 500

