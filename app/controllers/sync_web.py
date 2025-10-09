"""
Sync Web Controller
Web interface for interactive sync operations
"""

from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required
import requests

from app.services.sync_service import SyncService

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
    data = request.get_json()
    remote_url = data.get('remote_url')
    
    if not remote_url:
        return jsonify({'error': 'Remote URL is required'}), 400
    
    try:
        sync_service = SyncService(remote_url=remote_url)
        
        # Get local inventory
        local_inv = sync_service.get_local_inventory()
        
        # Get remote inventory
        remote_inv = sync_service.get_remote_inventory()
        
        # Compare
        comparison = sync_service.compare_inventories(local_inv, remote_inv)
        
        return jsonify({
            'success': True,
            'comparison': comparison
        })
    
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

