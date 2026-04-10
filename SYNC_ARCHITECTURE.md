# Live Sync Architecture & Flow Diagrams

## Current System Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────────┐
│                    MicroK8s Orchestrator                        │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    Web UI Layer                          │  │
│  │  • System Management (with Live Sync tab)                │  │
│  │  • Embedded iframe: /sync/interactive-bare               │  │
│  └──────────────────────────────────────────────────────────┘  │
│                            ↓                                    │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              Web Controllers (Flask)                     │  │
│  │                                                          │  │
│  │  ┌────────────────┐         ┌────────────────┐         │  │
│  │  │  sync_web.py   │         │  sync_api.py   │         │  │
│  │  │ /sync/*        │         │ /api/v1/sync/* │         │  │
│  │  │ (PASSWORD)     │         │ (JWT TOKEN)    │         │  │
│  │  │ ❌ CURRENT UI  │         │ ✅ NOT USED    │         │  │
│  │  └────────────────┘         └────────────────┘         │  │
│  └──────────────────────────────────────────────────────────┘  │
│                            ↓                                    │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              Service Layer                               │  │
│  │  • sync_service.py (comparison logic)                    │  │
│  │  • progress_logger.py (SSE streaming)                    │  │
│  └──────────────────────────────────────────────────────────┘  │
│                            ↓                                    │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              Data Layer                                  │  │
│  │  • Node, Cluster, SSHKey models                          │  │
│  │  • SQLite database                                       │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Current Flow: Password-Based Sync (sync_web.py)

### Flow Diagram

```
┌──────────────────────┐                        ┌──────────────────────┐
│  Local Server        │                        │  Remote Server       │
│  (192.0.2.16)        │                        │  (192.0.2.14)        │
│  "SENDER"            │                        │  "RECEIVER"          │
└──────────────────────┘                        └──────────────────────┘
         │                                                  │
         │  1. User enters remote URL + credentials        │
         │     URL: http://192.0.2.14:5000                │
         │     User: admin                                 │
         │     Pass: stoyan93Nina                          │
         │                                                  │
         ├─────────── [CONNECT & COMPARE] ────────────────>│
         │  POST /sync/compare                             │
         │  {                                              │
         │    remote_url: "...",                           │
         │    username: "admin",                           │
         │    password: "..."                              │
         │  }                                              │
         │                                                  │
         │            ┌─────────────────────┐              │
         │            │  Backend Process    │              │
         │            └─────────────────────┘              │
         │                                                  │
         │  2. Create Session                              │
         │     session = requests.Session()                │
         │                                                  │
         │  3. Login to Remote ──────────────────────────>│
         │     POST /auth/login                            │
         │     data: {username, password}                  │
         │                                                  │
         │                                      4. Flask    │
         │                                         Login    │
         │                                         Auth     │
         │<───────────────────────────────────────────────│
         │     302 Redirect + Session Cookie               │
         │                                                  │
         │  5. Get Remote Inventory ──────────────────────>│
         │     GET /api/nodes                              │
         │     Cookie: session=xxx                         │
         │                                                  │
         │<───────────────────────────────────────────────│
         │     200 OK                                      │
         │     [list of nodes]                             │
         │                                                  │
         │  6. Get Remote Clusters ────────────────────────>│
         │     GET /api/clusters                           │
         │     Cookie: session=xxx                         │
         │                                                  │
         │<───────────────────────────────────────────────│
         │     200 OK                                      │
         │     [list of clusters]                          │
         │                                                  │
         │  7. Get Local Inventory                         │
         │     Query: Node.query.all()                     │
         │     Query: Cluster.query.all()                  │
         │                                                  │
         │  8. Compare                                     │
         │     SyncService.compare_inventories()           │
         │     Returns:                                    │
         │     • identical                                 │
         │     • different                                 │
         │     • missing_on_remote                         │
         │     • missing_on_local                          │
         │                                                  │
         │<───────────────────────────────────────────────│
         │     Response: comparison results                │
         │                                                  │
         │  9. Display Results in UI                       │
         │     • Show tables (identical, different, etc.)  │
         │     • User selects items to sync                │
         │     • User clicks "Start Sync"                  │
         │                                                  │
         ├─────────── [START TRANSFER] ───────────────────>│
         │  POST /sync/api/transfer                        │
         │  {                                              │
         │    remote_url: "...",                           │
         │    remote_username: "admin",                    │
         │    remote_password: "...",                      │
         │    selected_items: {                            │
         │      nodes: ["3", "4", "5"],                    │
         │      clusters: ["1"]                            │
         │    }                                            │
         │  }                                              │
         │                                                  │
         │     ┌────────────────────────────────┐          │
         │     │  10. Background Thread Starts  │          │
         │     │  (No more deadlock!)           │          │
         │     └────────────────────────────────┘          │
         │                                                  │
         │<───────────────────────────────────────────────│
         │     200 OK (immediately!)                       │
         │     {                                           │
         │       operation_id: "9155128d",                 │
         │       message: "Transfer started"               │
         │     }                                           │
         │                                                  │
         │  11. UI Connects to Progress Stream             │
         │     EventSource: /sync/api/progress-stream      │
         │     (Server-Sent Events)                        │
         │                                                  │
         │     ┌────────────────────────────────┐          │
         │     │  Background Thread Executes:   │          │
         │     │                                │          │
         │     │  12. Login to Remote ──────────┼─────────>│
         │     │      POST /auth/login          │          │
         │     │      timeout=10s ⏱️            │          │
         │     │                                │          │
         │     │  13. Fetch Local Nodes         │          │
         │     │      for node_id in selected:  │          │
         │     │        Node.query.get(id)      │          │
         │     │                                │          │
         │     │  14. Transfer Each Node ───────┼─────────>│
         │     │      POST /api/nodes           │          │
         │     │      timeout=30s ⏱️            │          │
         │     │      json: node_data           │          │
         │     │                                │  CREATE  │
         │     │                                │  or      │
         │     │                                │  UPDATE  │
         │     │                                │  Node    │
         │     │<───────────────────────────────┼─────────│
         │     │      201 Created               │          │
         │     │                                │          │
         │     │  15. Transfer Clusters ────────┼─────────>│
         │     │      POST /api/clusters        │          │
         │     │      timeout=30s ⏱️            │          │
         │     │                                │  CREATE  │
         │     │                                │  or      │
         │     │                                │  UPDATE  │
         │     │<───────────────────────────────┼─────────│
         │     │      201 Created               │          │
         │     │                                │          │
         │     │  16. Complete                  │          │
         │     │      progress.complete()       │          │
         │     └────────────────────────────────┘          │
         │                                                  │
         │  17. UI Shows Progress                          │
         │      • 🔐 Connecting...                         │
         │      • ✅ Connected                             │
         │      • 📤 Fetching nodes...                     │
         │      • ⬆️ Transferring node 1/3...              │
         │      • ✅ Transfer complete!                    │
         │                                                  │
         │  18. Auto-refresh comparison                    │
         │      (Shows updated state)                      │
         │                                                  │
```

## Data Flow Detail

### Step-by-Step Data Transfer

```
┌─────────────────────────────────────────────────────────────────┐
│  STEP 1: Comparison Phase                                      │
└─────────────────────────────────────────────────────────────────┘

Local Server              Compare Logic              Remote Server
─────────────            ──────────────            ──────────────

Local Inventory:         Process:                  Remote Inventory:
  Nodes:                   1. Match by              Nodes:
    [1] devmod-42           hostname                 [1] devmod-master-1
    [2] devmod-43         2. Compare                 [2] devmod-41
    [3] devmod-02           attributes
    [4] devmod-05         3. Categorize:
    [5] devmod-09            • identical
    [6] devmod-44            • different
    [7] devmod-master-2      • missing_on_remote
    [8] devmod-master-1      • missing_on_local
    [9] devmod-41
                          
  Clusters:                                        Clusters:
    [1] baremetal-lab                               [1] baremetal-lab
        ha_enabled: false                               ha_enabled: true


Result:
  Nodes:
    identical: [devmod-master-1, devmod-41]
    missing_on_remote: [devmod-42, devmod-43, devmod-02, 
                        devmod-05, devmod-09, devmod-44, 
                        devmod-master-2]
    missing_on_local: []
    different: []
    
  Clusters:
    identical: []
    different: [baremetal-lab]  ← ha_enabled differs
    missing_on_remote: []
    missing_on_local: []


┌─────────────────────────────────────────────────────────────────┐
│  STEP 2: User Selection                                        │
└─────────────────────────────────────────────────────────────────┘

UI Table:
  ☑ devmod-42      192.0.2.28    Missing on Remote
  ☐ devmod-43      192.0.2.30    Missing on Remote
  ☐ devmod-02      192.0.2.68    Missing on Remote
  ☐ devmod-05      192.0.2.76    Missing on Remote
  
User selects: [devmod-42]  (node ID: 3)


┌─────────────────────────────────────────────────────────────────┐
│  STEP 3: Data Preparation                                      │
└─────────────────────────────────────────────────────────────────┘

Query Database:
  node = Node.query.get(3)
  
Extract Data:
  {
    "hostname": "devmod-42",
    "ip_address": "192.0.2.28",
    "ssh_user": "sumix",
    "ssh_port": 22,
    "cluster_id": 1,
    "notes": "proxmox",
    "tags": null
  }


┌─────────────────────────────────────────────────────────────────┐
│  STEP 4: Transfer                                              │
└─────────────────────────────────────────────────────────────────┘

HTTP Request:
  POST http://192.0.2.14:5000/api/nodes
  Headers:
    Cookie: session=xxx
    Content-Type: application/json
  Body:
    {
      "hostname": "devmod-42",
      "ip_address": "192.0.2.28",
      ...
    }

Remote Server Processing:
  1. Authenticate (check session)
  2. Validate data
  3. Check if node exists:
       Node.query.filter_by(hostname="devmod-42").first()
  4. If exists: UPDATE
     If not: CREATE
       new_node = Node(**data)
       db.session.add(new_node)
  5. db.session.commit()
  
Response:
  201 Created
  {
    "id": 4,
    "hostname": "devmod-42",
    "message": "Node created successfully"
  }
```

## Problems in Current Implementation

### Issue 1: Timeout During Transfer

```
Timeline:
  T+0s    : User clicks "Start Sync"
  T+0.02s : POST /sync/api/transfer returns (✅ Fixed!)
  T+0.5s  : Background thread starts
  T+1s    : Thread: POST /auth/login to 192.0.2.14
  T+11s   : ❌ TIMEOUT! (connect timeout=10s)
  
Why?
  • 10s is too short for some networks
  • Connection might be slow
  • Network latency
  
Current Code:
  login_response = session.post(
      f"{remote_url}/auth/login",
      timeout=10  ← Too short!
  )
```

### Issue 2: Password in Transit

```
Security Risk:
  ┌─────────────┐                      ┌─────────────┐
  │   Browser   │  HTTP POST Body:     │   Server    │
  │             │  {                    │             │
  │  User       │    "remote_username": │   Flask     │
  │  Types      │      "admin",         │   Receives  │
  │  Password   │    "remote_password": │   Password  │
  │             │      "stoyan93Nina"   │             │
  │             │  }                    │             │
  └─────────────┘                      └─────────────┘
       ↓                                      ↓
  Password exposed in:                 Password logged in:
  • Browser memory                     • Access logs
  • Browser dev tools                  • Error logs
  • Network packets (if HTTP)          • Application logs
  • Proxy logs                         
  • Load balancer logs
  
Problems:
  • Password can be reused indefinitely
  • Password compromise affects all access
  • No audit trail per-sync operation
  • Can't revoke a single sync session
```

### Issue 3: No Single-Use Guarantee

```
Scenario:
  1. User syncs from Server A to Server B
     • Credentials sent, sync completes
  
  2. Days later, credentials still valid
     • Anyone with credentials can sync again
     • No way to limit to one-time use
  
  3. Password leaked
     • Attacker can sync any time
     • No way to revoke just sync access
     • Must change main password
```

## Proposed Architecture: Token-Based

### New Flow Diagram

```
┌──────────────────────┐                        ┌──────────────────────┐
│  Local Server        │                        │  Remote Server       │
│  (Sender)            │                        │  (Receiver)          │
└──────────────────────┘                        └──────────────────────┘
         │                                                  │
         │  ┌───────────────────────────────────────────┐  │
         │  │  STEP 0: Generate Token on REMOTE        │  │
         │  │  (Done BEFORE sync)                      │  │
         │  └───────────────────────────────────────────┘  │
         │                                                  │
         │              Admin logs into Remote ────────────>│
         │                                                  │
         │              Goes to: System Management         │
         │                → Live Sync → Generate Token     │
         │                                                  │
         │                       POST /api/sync/generate-token
         │                                                  │
         │                       Server generates:         │
         │                       • JWT Token               │
         │                       • Valid 1 hour            │
         │                       • Single use only         │
         │                                                  │
         │<─────────────────────────────────────────────────
         │     Response:                                   │
         │     {                                           │
         │       "token": "eyJhbGc...",                   │
         │       "expires_in": 3600,                      │
         │       "uses_remaining": 1                      │
         │     }                                           │
         │                                                  │
         │     Admin COPIES token                          │
         │                                                  │
         │  ┌───────────────────────────────────────────┐  │
         │  │  STEP 1: Use Token on LOCAL               │  │
         │  └───────────────────────────────────────────┘  │
         │                                                  │
         │  User pastes token in Local Server UI           │
         │  Token: eyJhbGc...                              │
         │                                                  │
         ├─────────── [TEST CONNECTION] ──────────────────>│
         │  GET /api/v1/sync/test                          │
         │  (No auth required)                             │
         │                                                  │
         │<───────────────────────────────────────────────│
         │     200 OK                                      │
         │     {                                           │
         │       "message": "Sync API working",           │
         │       "version": "1.2.0"                       │
         │     }                                           │
         │                                                  │
         ├─────────── [GET INVENTORY] ────────────────────>│
         │  GET /api/v1/sync/inventory                     │
         │  Authorization: Bearer eyJhbGc...               │
         │                                                  │
         │              Server:                            │
         │              1. Decode JWT                      │
         │              2. Validate signature              │
         │              3. Check expiration                │
         │              4. Check uses (0 < 1) ✅          │
         │              5. Increment uses (0 → 1)         │
         │              6. Return inventory                │
         │                                                  │
         │<───────────────────────────────────────────────│
         │     200 OK                                      │
         │     {                                           │
         │       "inventory": {                           │
         │         "nodes": [...],                        │
         │         "clusters": [...]                      │
         │       }                                         │
         │     }                                           │
         │                                                  │
         │  [LOCAL COMPARISON]                             │
         │  Display results, user selects items            │
         │                                                  │
         ├─────────── [SEND DATA] ─────────────────────────>│
         │  POST /api/v1/sync/receive                      │
         │  Authorization: Bearer eyJhbGc...               │
         │  {                                              │
         │    "package": {                                │
         │      "nodes": [...],                           │
         │      "clusters": [...]                         │
         │    }                                            │
         │  }                                              │
         │                                                  │
         │              Server:                            │
         │              1. Validate token ✅               │
         │              2. Check uses (1 ≥ 1) ❌          │
         │              3. REJECT (max uses reached)       │
         │                 OR                              │
         │              4. Token is single-use:           │
         │                 Accept ONCE, then revoke        │
         │                                                  │
         │<───────────────────────────────────────────────│
         │     200 OK                                      │
         │     {                                           │
         │       "nodes_created": 1,                      │
         │       "clusters_updated": 0                    │
         │     }                                           │
         │                                                  │
         │  ⚠️ Token now REVOKED automatically             │
         │                                                  │
```

### Token Data Structure

```
JWT Payload:
{
  "token_id": "abc123...",        // Unique token identifier
  "server_id": "orchestrator-1",  // Which server generated it
  "expires_at": 1728756000,       // Unix timestamp
  "iat": 1728752400               // Issued at
}

Token Metadata (stored server-side):
{
  "token_id": "abc123...",
  "server_id": "orchestrator-1",
  "expires_at": 1728756000,
  "max_uses": 1,                  // ← Single use!
  "uses": 0,                      // Incremented on each use
  "revoked": false,               // Set true after use
  "created_at": "2025-10-12T17:00:00",
  "last_used": null
}

Token Lifecycle:
  1. Created:     uses=0, revoked=false
  2. First use:   uses=1, revoked=false
  3. After use:   uses=1, revoked=true  ← Auto-revoked!
```

## Comparison: Current vs Proposed

```
┌─────────────────────────────────────────────────────────────────┐
│                    CURRENT (PASSWORD)                           │
└─────────────────────────────────────────────────────────────────┘

Security:        ❌ Password exposed in requests
                 ❌ Password reusable forever
                 ❌ No per-sync audit trail
                 ❌ Logout needed to "revoke"

User Experience: ❌ Must remember/share password
                 ❌ Complex credential management
                 ❌ Security risk of password sharing

Performance:     ⚠️ Multiple auth steps
                 ⚠️ Session cookie management
                 ⚠️ 10s timeout (too short)

Debugging:       ⚠️ Passwords in logs (risk)
                 ⚠️ Hard to trace specific syncs
                 ⚠️ Mixed with regular login traffic


┌─────────────────────────────────────────────────────────────────┐
│                    PROPOSED (JWT TOKEN)                         │
└─────────────────────────────────────────────────────────────────┘

Security:        ✅ Token never includes password
                 ✅ Single-use (auto-revoked)
                 ✅ Time-limited (1 hour)
                 ✅ Can revoke individual tokens
                 ✅ Separate from login credentials

User Experience: ✅ Simple: copy/paste token
                 ✅ No password sharing
                 ✅ Clear token lifecycle
                 ✅ Visual feedback (expires, uses)

Performance:     ✅ Direct API calls (faster)
                 ✅ No session management
                 ✅ Longer timeouts (30-60s)
                 ✅ Stateless auth

Debugging:       ✅ Token ID for tracing
                 ✅ Clear audit trail
                 ✅ Separate from login logs
                 ✅ Can see token usage stats
```

## Summary

**Current System:**
- ✅ Works for basic sync
- ✅ Deadlock fixed (RLock)
- ✅ Error handling added
- ❌ Security concerns (passwords)
- ❌ Timeout issues
- ❌ No single-use guarantee

**Proposed System:**
- ✅ More secure (JWT tokens)
- ✅ Better UX (simple token paste)
- ✅ Single-use tokens
- ✅ Better performance
- ✅ Better debugging
- ✅ Infrastructure already exists!

**Next Steps:**
1. Implement token generation UI
2. Update sync form to use tokens
3. Switch backend to token API
4. Test end-to-end
5. Deploy

