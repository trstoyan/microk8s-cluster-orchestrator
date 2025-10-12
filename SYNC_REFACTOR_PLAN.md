# Live Sync Refactor Plan
## JWT Token-Based Authentication

### Current State Analysis

#### Two Parallel Systems Exist:
1. **`sync_api.py`** - Token-based API (JWT) ✅
   - Has `@require_sync_token` decorator
   - Uses `SyncToken` class from `app/utils/encryption.py`
   - Endpoints: `/api/v1/sync/*`
   - NOT currently used by web UI

2. **`sync_web.py`** - Username/Password based ❌
   - Uses Flask session login
   - Endpoints: `/sync/*`
   - Currently used by web UI
   - Less secure (password in POST body)

### Problems with Current `sync_web.py`:
1. ❌ Passwords transmitted in requests
2. ❌ No token expiration
3. ❌ No single-use tokens
4. ❌ Uses regular login (not sync-specific)
5. ❌ Timeout issues (10s connect timeout)
6. ❌ Complex session management

### Proposed Solution: Unify on Token-Based Auth

## Phase 1: Token Generation UI

### 1.1 Add Token Management Endpoint
**File:** `app/controllers/api.py`

```python
@api_bp.route('/sync/generate-token', methods=['POST'])
@login_required
def generate_sync_token():
    """
    Generate a one-time sync token
    
    Returns:
    {
        "token": "eyJ...",
        "expires_in": 3600,
        "expires_at": "2025-10-12T18:00:00",
        "uses_remaining": 1  # Single use
    }
    """
    from app.utils.encryption import SyncToken
    token_manager = SyncToken()
    
    # Generate single-use token valid for 1 hour
    token = token_manager.create_token(
        server_id=f"orchestrator-{current_user.username}",
        expires_in=3600,
        max_uses=1  # Single use only
    )
    
    return jsonify({
        'success': True,
        'token': token,
        'expires_in': 3600,
        'expires_at': (datetime.now() + timedelta(hours=1)).isoformat(),
        'uses_remaining': 1
    })
```

### 1.2 Token Display UI
**File:** `app/templates/system_management.html` (add to Live Sync tab)

```html
<div class="card mb-4">
    <div class="card-header">
        <h5><i class="fas fa-key"></i> Sync Token Generator</h5>
    </div>
    <div class="card-body">
        <p>Generate a one-time token to allow OTHER servers to sync FROM this server.</p>
        
        <button id="generateTokenBtn" class="btn btn-primary">
            <i class="fas fa-plus"></i> Generate Sync Token
        </button>
        
        <div id="tokenDisplay" class="mt-3" style="display: none;">
            <div class="alert alert-success">
                <h6>✅ Token Generated!</h6>
                <p>Copy this token and paste it in the OTHER server's sync form.</p>
                <div class="input-group">
                    <input type="text" id="syncTokenValue" class="form-control font-monospace" readonly>
                    <button class="btn btn-outline-secondary" onclick="copyToken()">
                        <i class="fas fa-copy"></i> Copy
                    </button>
                </div>
                <small class="text-muted">
                    • Expires in: <span id="tokenExpiry">1 hour</span><br>
                    • Single use only<br>
                    • Automatically revoked after use
                </small>
            </div>
        </div>
    </div>
</div>
```

## Phase 2: Update Sync Web UI

### 2.1 Modify Sync Form
**File:** `app/templates/sync/interactive_content.html`

**BEFORE:**
```html
<input type="text" id="remoteUsername" placeholder="admin">
<input type="password" id="remotePassword" placeholder="Password">
```

**AFTER:**
```html
<input type="text" id="syncToken" class="form-control font-monospace" 
       placeholder="Paste sync token from remote server">
<small class="text-muted">
    Get token from remote server: System Management → Live Sync → Generate Token
</small>
```

### 2.2 Update JavaScript
**File:** `app/templates/sync/interactive_content.html`

**BEFORE:**
```javascript
const username = document.getElementById('remoteUsername').value;
const password = document.getElementById('remotePassword').value;
```

**AFTER:**
```javascript
const syncToken = document.getElementById('syncToken').value.trim();

// Validate token format (JWT)
if (!syncToken || !syncToken.startsWith('eyJ')) {
    showError('Invalid token format');
    return;
}
```

## Phase 3: Update Backend Logic

### 3.1 Modify `sync_web.py` to Use Tokens
**File:** `app/controllers/sync_web.py`

**Current flow:**
```python
# Login with username/password
login_response = session.post(
    f"{remote_url}/auth/login",
    data={'username': remote_username, 'password': remote_password},
    timeout=10
)
```

**New flow:**
```python
# Use token for authentication
headers = {
    'Authorization': f'Bearer {sync_token}',
    'Content-Type': 'application/json'
}

# Get inventory with token
response = session.get(
    f"{remote_url}/api/v1/sync/inventory",
    headers=headers,
    timeout=30  # Increased timeout
)
```

### 3.2 Update `/sync/compare` endpoint
```python
@sync_web_bp.route('/compare', methods=['POST'])
@login_required
def compare():
    data = request.get_json()
    remote_url = data.get('remote_url')
    sync_token = data.get('sync_token')  # Changed from username/password
    
    if not sync_token:
        return jsonify({'error': 'Sync token is required'}), 400
    
    # Use token-based API
    headers = {'Authorization': f'Bearer {sync_token}'}
    
    # Get remote inventory
    inventory_response = requests.get(
        f"{remote_url}/api/v1/sync/inventory",
        headers=headers,
        timeout=30
    )
    
    # Compare inventories
    ...
```

### 3.3 Update `/sync/api/transfer` endpoint
```python
def _execute_transfer(app, operation_id, remote_url, sync_token, selected_items, progress, logger):
    """Execute transfer using token auth"""
    
    with app.app_context():
        try:
            import requests
            
            headers = {
                'Authorization': f'Bearer {sync_token}',
                'Content-Type': 'application/json'
            }
            
            progress.info(f'🔐 Connecting to {remote_url}...')
            
            # Validate token first
            test_response = requests.get(
                f"{remote_url}/api/v1/sync/test",
                timeout=10
            )
            
            if test_response.status_code != 200:
                progress.error(f'❌ Remote server not responding')
                return
            
            progress.success('✅ Connected to remote server')
            
            # Get selected items from local database
            from app.models.flask_models import Node, Cluster
            
            sync_data = {'nodes': [], 'clusters': []}
            
            # Fetch nodes
            if selected_items.get('nodes'):
                progress.info(f'📤 Fetching {len(selected_items["nodes"])} nodes...')
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
                progress.success(f'✅ Prepared {len(sync_data["nodes"])} nodes')
            
            # Send data using token auth
            progress.info(f'⬆️ Transferring data to {remote_url}...')
            
            transfer_response = requests.post(
                f"{remote_url}/api/v1/sync/receive",
                headers=headers,
                json={'package': sync_data},
                timeout=60  # Longer timeout for data transfer
            )
            
            if transfer_response.status_code == 200:
                result = transfer_response.json()
                progress.success(f'✅ Transfer completed!')
                progress.success(f'   • Nodes: {len(sync_data["nodes"])}')
                progress.success(f'   • Clusters: {len(sync_data["clusters"])}')
            else:
                progress.error(f'❌ Transfer failed: HTTP {transfer_response.status_code}')
                progress.error(f'   {transfer_response.text[:200]}')
                
        except requests.exceptions.ConnectionError as e:
            progress.error(f'❌ Cannot connect to remote server')
            progress.error(f'   Server may be offline or unreachable')
            logger.error(f"[SYNC-THREAD] Connection error: {str(e)}")
        except requests.exceptions.Timeout:
            progress.error(f'❌ Connection timeout to {remote_url}')
            progress.error(f'   Server took too long to respond')
            logger.error(f"[SYNC-THREAD] Timeout")
        except Exception as e:
            progress.error(f'❌ Transfer failed: {str(e)}')
            logger.error(f"[SYNC-THREAD] Error: {str(e)}")
```

## Phase 4: Update `sync_api.py` Receive Endpoint

### 4.1 Fix `/api/v1/sync/receive` to Handle Nodes
**File:** `app/controllers/sync_api.py`

```python
@sync_bp.route('/receive', methods=['POST'])
@require_sync_token
def receive():
    """
    Receive and apply sync package
    """
    import logging
    logger = logging.getLogger(__name__)
    
    data = request.get_json()
    
    if not data or 'package' not in data:
        return jsonify({'error': 'Missing package data'}), 400
    
    try:
        package = data['package']
        
        from app.models.flask_models import Node, Cluster
        from app.models.database import db
        
        results = {
            'success': True,
            'nodes_created': 0,
            'nodes_updated': 0,
            'clusters_created': 0,
            'clusters_updated': 0,
            'errors': []
        }
        
        # Process nodes
        if 'nodes' in package:
            for node_data in package['nodes']:
                try:
                    # Check if node exists by hostname
                    existing_node = Node.query.filter_by(
                        hostname=node_data['hostname']
                    ).first()
                    
                    if existing_node:
                        # Update existing node
                        for key, value in node_data.items():
                            if hasattr(existing_node, key):
                                setattr(existing_node, key, value)
                        results['nodes_updated'] += 1
                        logger.info(f"[SYNC-API] Updated node: {node_data['hostname']}")
                    else:
                        # Create new node
                        new_node = Node(**node_data)
                        db.session.add(new_node)
                        results['nodes_created'] += 1
                        logger.info(f"[SYNC-API] Created node: {node_data['hostname']}")
                        
                except Exception as e:
                    error_msg = f"Failed to sync node {node_data.get('hostname', 'unknown')}: {str(e)}"
                    results['errors'].append(error_msg)
                    logger.error(f"[SYNC-API] {error_msg}")
        
        # Process clusters
        if 'clusters' in package:
            for cluster_data in package['clusters']:
                try:
                    existing_cluster = Cluster.query.filter_by(
                        name=cluster_data['name']
                    ).first()
                    
                    if existing_cluster:
                        for key, value in cluster_data.items():
                            if hasattr(existing_cluster, key):
                                setattr(existing_cluster, key, value)
                        results['clusters_updated'] += 1
                        logger.info(f"[SYNC-API] Updated cluster: {cluster_data['name']}")
                    else:
                        new_cluster = Cluster(**cluster_data)
                        db.session.add(new_cluster)
                        results['clusters_created'] += 1
                        logger.info(f"[SYNC-API] Created cluster: {cluster_data['name']}")
                        
                except Exception as e:
                    error_msg = f"Failed to sync cluster {cluster_data.get('name', 'unknown')}: {str(e)}"
                    results['errors'].append(error_msg)
                    logger.error(f"[SYNC-API] {error_msg}")
        
        # Commit all changes
        db.session.commit()
        
        logger.info(f"[SYNC-API] Sync complete: {results}")
        return jsonify(results)
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"[SYNC-API] Sync failed: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
```

## Phase 5: Update SyncToken for Single-Use

### 5.1 Enhance `app/utils/encryption.py`
```python
class SyncToken:
    def __init__(self):
        self.tokens = {}  # In production, use Redis
        self.secret_key = os.getenv('SECRET_KEY', 'fallback-secret-key')
    
    def create_token(self, server_id, expires_in=3600, max_uses=1):
        """
        Create a JWT token with usage tracking
        
        Args:
            server_id: Unique identifier for the server
            expires_in: Token lifetime in seconds (default 1 hour)
            max_uses: Maximum times token can be used (default 1)
        """
        token_id = secrets.token_urlsafe(16)
        expires_at = time.time() + expires_in
        
        payload = {
            'token_id': token_id,
            'server_id': server_id,
            'expires_at': expires_at,
            'iat': time.time()
        }
        
        token = jwt.encode(payload, self.secret_key, algorithm='HS256')
        
        # Store token metadata
        self.tokens[token_id] = {
            'server_id': server_id,
            'expires_at': expires_at,
            'max_uses': max_uses,
            'uses': 0,
            'revoked': False
        }
        
        return token
    
    def validate_token(self, token):
        """Validate token and increment use counter"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])
            token_id = payload.get('token_id')
            
            if not token_id or token_id not in self.tokens:
                return False
            
            token_info = self.tokens[token_id]
            
            # Check if revoked
            if token_info['revoked']:
                return False
            
            # Check expiration
            if time.time() > token_info['expires_at']:
                return False
            
            # Check usage limit
            if token_info['uses'] >= token_info['max_uses']:
                return False
            
            # Increment use counter
            token_info['uses'] += 1
            
            # Auto-revoke if max uses reached
            if token_info['uses'] >= token_info['max_uses']:
                token_info['revoked'] = True
            
            return True
            
        except jwt.ExpiredSignatureError:
            return False
        except jwt.InvalidTokenError:
            return False
    
    def revoke_token(self, token):
        """Manually revoke a token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])
            token_id = payload.get('token_id')
            
            if token_id in self.tokens:
                self.tokens[token_id]['revoked'] = True
                return True
        except:
            pass
        return False
    
    def get_token_info(self, token):
        """Get token metadata"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])
            token_id = payload.get('token_id')
            
            if token_id in self.tokens:
                info = self.tokens[token_id].copy()
                info['token_id'] = token_id
                return info
        except:
            pass
        return None
```

## Testing Plan

### Test 1: Token Generation
1. Go to System Management → Live Sync
2. Click "Generate Sync Token"
3. Verify token is displayed
4. Copy token

### Test 2: Token-Based Sync
1. On remote server (10.25.8.14): Generate token
2. On local server (10.25.8.16): 
   - Enter remote URL: http://10.25.8.14:5000
   - Paste token
   - Click "Connect & Compare"
3. Verify comparison works
4. Select items to sync
5. Click "Start Sync"
6. Verify live progress
7. Verify data transferred

### Test 3: Token Security
1. Try using same token twice → Should fail
2. Try using expired token → Should fail
3. Try using invalid token → Should fail

### Test 4: Error Handling
1. Enter invalid token → Clear error message
2. Remote server down → Graceful timeout
3. Network error → User-friendly error

## Benefits of New Design

✅ **Security:**
- No passwords in transit
- Single-use tokens
- Token expiration
- Token revocation

✅ **User Experience:**
- Simpler UI (just paste token)
- No password management
- Clear token lifecycle
- Better error messages

✅ **Reliability:**
- Longer timeouts for data transfer
- Better error handling
- Connection error recovery
- Progress streaming

✅ **Maintainability:**
- Unified on one auth system (tokens)
- Cleaner code
- Better logging
- Easier debugging

## Implementation Order

1. ✅ Fix deadlock (RLock) - DONE
2. ✅ Add error handling - DONE
3. ✅ Fix recursive backups - DONE
4. 🔄 Add token generation UI
5. 🔄 Update sync form to use tokens
6. 🔄 Update backend to use token API
7. 🔄 Fix receive endpoint
8. 🔄 Test end-to-end
9. 🔄 Document for users
10. 🔄 Deploy and verify

## Rollout Strategy

### Phase A: Add token option (keep password as fallback)
- Add token field to UI
- If token provided, use token auth
- If username/password provided, use old method
- Both work side-by-side

### Phase B: Make token default
- Token field is primary
- Username/password is "advanced" option
- Encourage token use

### Phase C: Token only
- Remove username/password option
- Only token-based auth
- Clean up old code

