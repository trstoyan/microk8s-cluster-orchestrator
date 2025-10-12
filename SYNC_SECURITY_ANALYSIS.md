# Sync Security Analysis
## Protocol, Encryption, and Data Transmission

## 🔍 Current Implementation Analysis

### 1. Transport Protocol

#### What's Used: **HTTP (Unencrypted)**

```python
# cli.py line 1991
app.run(host=host, port=port, debug=debug)
# No ssl_context = No HTTPS!
```

```python
# sync_web.py line 389-390
if not remote_url.startswith('http://') and not remote_url.startswith('https://'):
    remote_url = 'http://' + remote_url
# Defaults to HTTP if no protocol specified
```

**Actual Network Traffic:**
```
Client (10.25.8.16)            Server (10.25.8.14)
       │                                │
       ├─── TCP Connection ────────────>│ Port 5000
       │    (No TLS handshake)          │
       │                                │
       ├─── HTTP POST /auth/login ─────>│
       │    Host: 10.25.8.14:5000       │
       │    Content-Type: application/x-www-form-urlencoded
       │    BODY (PLAINTEXT):            │
       │      username=admin             │
       │      password=stoyan93Nina      │ ← VISIBLE ON NETWORK!
       │                                │
       ├─── HTTP POST /api/nodes ──────>│
       │    Cookie: session=xxx          │
       │    Content-Type: application/json
       │    BODY (PLAINTEXT):            │
       │      {                          │
       │        "hostname": "devmod-42", │
       │        "ip_address": "10.25.8.28",
       │        "ssh_user": "sumix"      │ ← ALL VISIBLE!
       │      }                          │
       │                                │
```

### 2. Data Encryption

#### Built-in Capability: **AES-256 (Available but NOT USED)**

**The Code Exists:**
```python
# app/utils/encryption.py
class SyncEncryption:
    """Handle encryption/decryption for sync operations"""
    
    def encrypt(self, data: dict) -> dict:
        """
        Uses:
        • AES-256 encryption (Fernet)
        • PBKDF2HMAC key derivation
        • SHA-256 hashing
        • 100,000 iterations
        • Random 16-byte salt
        """
        json_data = json.dumps(data)
        encrypted = self.fernet.encrypt(json_data.encode())
        
        return {
            'payload': base64.b64encode(encrypted).decode(),
            'salt': base64.b64encode(self.salt).decode()
        }
```

**But in Practice:**
```python
# sync_web.py - Current transfer code
response = session.post(
    f"{remote_url}/api/nodes",
    json=node_data,  # ← SENT AS PLAIN JSON!
    timeout=30       # No encryption applied
)
```

❌ **The encryption utility exists but is NOT used in sync_web.py!**

#### Where It's Designed to Be Used:
```python
# sync_api.py (line 220-224) - NOT currently used by UI
if encrypted and session_id and session_id in active_sessions:
    encryption = active_sessions[session_id].get('encryption')
    if encryption:
        sync_service.encryption = encryption

package = sync_service.create_sync_package(items_to_sync)
# ^ This would encrypt IF encryption object provided
```

### 3. Complete Security Breakdown

```
┌───────────────────────────────────────────────────────────────┐
│                  CURRENT SECURITY STATUS                      │
└───────────────────────────────────────────────────────────────┘

Layer 1: Physical/Network
  ✅ Local network (10.25.8.x)
  ⚠️  No VPN/tunnel
  ⚠️  No network segmentation
  ❌ Anyone on LAN can sniff traffic

Layer 2: Transport (TLS/SSL)
  ❌ NO TLS/SSL
  ❌ NO certificate validation
  ❌ NO encrypted channel
  🚨 ALL traffic is PLAINTEXT on network

Layer 3: Authentication
  ❌ Password sent in POST body (plaintext)
  ❌ Session cookie transmitted (HTTP only, no secure flag)
  ❌ No token expiration enforcement
  ❌ Passwords logged in access logs

Layer 4: Application Data
  ❌ JSON data sent unencrypted
  ❌ Node details (hostnames, IPs, users) visible
  ❌ Cluster configs visible
  ❌ No payload encryption

Layer 5: Authorization
  ⚠️  Basic Flask-Login session
  ⚠️  Session cookie can be hijacked
  ⚠️  No IP binding
  ⚠️  No request signing
```

### 4. What CAN Be Sniffed

**Using Wireshark/tcpdump on the LAN:**

```
# Capture filter
tcpdump -i any port 5000 -A

# Attacker sees:
POST /auth/login HTTP/1.1
Host: 10.25.8.14:5000
Content-Length: 42

username=admin&password=stoyan93Nina         ← PASSWORD VISIBLE!

POST /api/nodes HTTP/1.1
Host: 10.25.8.14:5000
Cookie: session=.eJwlj8uKwz... 
Content-Type: application/json

{
  "hostname": "devmod-42",
  "ip_address": "10.25.8.28",              ← ALL NODE DATA VISIBLE!
  "ssh_user": "sumix",
  "ssh_port": 22,
  "notes": "proxmox VM with sensitive data"
}
```

**Attack Scenarios:**
1. **Password Sniffing** → Attacker gets admin credentials
2. **Session Hijacking** → Copy session cookie, impersonate user
3. **Data Harvesting** → Learn network topology, usernames, IPs
4. **MITM Attack** → Modify data in transit

### 5. Comparison Matrix

```
┌────────────────────────────────────────────────────────────────┐
│            CURRENT vs SHOULD BE vs CAN BE                      │
└────────────────────────────────────────────────────────────────┘

Feature                  Current     Should Be      Available But Unused
─────────────────────────────────────────────────────────────────────────
Transport Protocol       HTTP        HTTPS          ❌ Not configured
TLS Certificate          None        Let's Encrypt  ❌ Not setup
Password Transmission    Plaintext   Hashed/Token   ⚠️  Token code exists!
Session Security         HTTP Cookie Secure Cookie  ⚠️  Flask supports it
Data Encryption          None        AES-256        ✅ Code exists in 
                                                       encryption.py!
Request Signing          None        HMAC-SHA256    ❌ Not implemented
Token-based Auth         None        JWT            ✅ SyncToken class 
                                                       exists!
Single-use Tokens        No          Yes            ⚠️  Can add to 
                                                       SyncToken
IP Whitelisting          No          Yes            ❌ Not implemented
Rate Limiting            No          Yes            ❌ Not implemented
Audit Logging            Basic       Comprehensive  ⚠️  Partial
```

## 📊 Encryption Capability (Exists but Unused)

### What's Already Built

```python
from app.utils.encryption import SyncEncryption

# Encryption is ready to use:
enc = SyncEncryption(password="shared_secret")

# BEFORE sending:
node_data = {
    'hostname': 'devmod-42',
    'ip_address': '10.25.8.28',
    'ssh_user': 'sumix'
}

encrypted_package = enc.encrypt(node_data)
# Returns:
# {
#   'payload': 'gAAAAABmK9x5P2aQzR...',  # Base64 encrypted
#   'salt': 'xYz123...'                  # For key derivation
# }

# SEND encrypted_package instead of node_data
```

```python
# On receiving end:
enc = SyncEncryption(password="same_shared_secret")
decrypted_data = enc.decrypt(encrypted_package)
# Returns original node_data
```

### Encryption Specs (if used)

```
Algorithm:     AES-256 (Fernet)
Mode:          CBC with HMAC
Key Derivation: PBKDF2-HMAC-SHA256
Iterations:    100,000
Salt:          16 bytes (random per encryption)
Key Size:      256 bits
Block Size:    128 bits
Authentication: Built-in (HMAC verification)
```

**Security Properties:**
- ✅ Authenticated encryption (prevents tampering)
- ✅ Random IV per message
- ✅ Secure key derivation
- ✅ Industry standard (NIST approved)
- ✅ Protection against padding oracle attacks

## 🛡️ Recommended Security Improvements

### Priority 1: Critical (Do First)

#### 1.1 Enable HTTPS

**Why Critical:**
- Encrypts ALL traffic (passwords, cookies, data)
- Prevents MITM attacks
- Industry standard
- Required for compliance

**Implementation:**

```python
# Option A: Self-signed certificate (internal network)
import ssl

ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
ssl_context.load_cert_chain('cert.pem', 'key.pem')

app.run(host=host, port=5000, ssl_context=ssl_context)
```

```bash
# Generate self-signed cert
openssl req -x509 -newkey rsa:4096 -nodes \
  -keyout key.pem -out cert.pem -days 365 \
  -subj "/CN=orchestrator.local"
```

```python
# Option B: Let's Encrypt (if public domain)
ssl_context = ('fullchain.pem', 'privkey.pem')
app.run(host=host, port=443, ssl_context=ssl_context)
```

**Immediate Impact:**
- ✅ Password encrypted in transit
- ✅ Session cookies protected
- ✅ Data payloads encrypted
- ✅ Certificate validation

#### 1.2 Switch to JWT Token Auth (Already Planned!)

**Why Critical:**
- No passwords in requests
- Single-use tokens
- Time-limited access
- Granular permissions

**What's Ready:**
```python
# Already exists in sync_api.py!
from app.utils.encryption import SyncToken

token_mgr = SyncToken()
token = token_mgr.create_token("server_id", expires_in=3600)

# In requests:
headers = {'Authorization': f'Bearer {token}'}
```

### Priority 2: High (Do Soon)

#### 2.1 Enable Application-Layer Encryption

**Use the existing SyncEncryption class:**

```python
# In sync_web.py:
from app.utils.encryption import SyncEncryption

# Before transfer:
enc = SyncEncryption(password=shared_secret)
encrypted_data = enc.encrypt(node_data)

# Send encrypted payload:
response = session.post(
    f"{remote_url}/api/v1/sync/receive",
    json={'encrypted': True, 'payload': encrypted_data},
    headers={'Authorization': f'Bearer {token}'}
)
```

**Benefits:**
- ✅ Defense in depth (encryption on encryption)
- ✅ Protection even if HTTPS compromised
- ✅ End-to-end encryption
- ✅ No trust in network layer

#### 2.2 Secure Cookie Settings

```python
# In app/__init__.py:
app.config['SESSION_COOKIE_SECURE'] = True      # HTTPS only
app.config['SESSION_COOKIE_HTTPONLY'] = True    # No JavaScript access
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # CSRF protection
app.config['PERMANENT_SESSION_LIFETIME'] = 3600 # 1 hour expiry
```

### Priority 3: Medium (Nice to Have)

- IP Whitelisting (only allow specific IPs to sync)
- Rate Limiting (prevent brute force)
- Request Signing (HMAC integrity check)
- Audit Logging (log all sync operations)
- Certificate Pinning (prevent MITM with fake certs)

## 🎯 Recommended Implementation Order

```
Phase 1: Token-Based Auth (Week 1)
  ✅ Already planned in SYNC_REFACTOR_PLAN.md
  • Generate tokens on remote
  • Use tokens in sync UI
  • Single-use enforcement
  • Time-limited tokens
  
Phase 2: HTTPS (Week 2)
  • Generate/obtain SSL certificates
  • Configure Flask with ssl_context
  • Update all http:// to https://
  • Test with self-signed cert first
  • Deploy production certs
  
Phase 3: Application Encryption (Week 3)
  • Integrate SyncEncryption in transfer flow
  • Add encryption toggle in UI
  • Test encrypted sync
  • Document shared secret exchange
  
Phase 4: Hardening (Week 4)
  • Secure cookie settings
  • Rate limiting
  • IP whitelisting
  • Enhanced logging
  • Security testing
```

## 📈 Security Improvement Metrics

```
Current State (Score: 2/10)
  ❌ No transport encryption
  ❌ Plaintext passwords
  ❌ No token auth
  ❌ No data encryption
  Total: 2 points (basic auth only)

After Phase 1 - Tokens (Score: 5/10)
  ❌ No transport encryption
  ✅ Token-based auth (single-use)
  ✅ No password transmission
  ❌ No data encryption
  Total: 5 points (authentication improved)

After Phase 2 - HTTPS (Score: 8/10)
  ✅ TLS transport encryption
  ✅ Token-based auth
  ✅ Certificate validation
  ⚠️  Basic data encryption (via TLS)
  Total: 8 points (industry standard)

After Phase 3 - App Encryption (Score: 9/10)
  ✅ TLS transport encryption
  ✅ Token-based auth
  ✅ End-to-end data encryption
  ✅ Defense in depth
  Total: 9 points (high security)

After Phase 4 - Hardening (Score: 10/10)
  ✅ Everything above
  ✅ Rate limiting
  ✅ IP whitelisting
  ✅ Security audit trail
  Total: 10 points (enterprise grade)
```

## Summary

### Current State: 🚨 INSECURE
- **Protocol**: HTTP (unencrypted)
- **Auth**: Password in POST body (plaintext)
- **Data**: JSON (plaintext)
- **Sniffable**: Yes, everything visible on LAN
- **Encryption Available**: Yes, but not used

### Good News: 
✅ Encryption code already exists!
✅ Token infrastructure already built!
✅ Easy to enable HTTPS
✅ Most work is just connecting existing pieces

### Action Required:
1. **Immediate**: Switch to token auth (Phase 1)
2. **Urgent**: Enable HTTPS (Phase 2)  
3. **Important**: Add application encryption (Phase 3)
4. **Nice to have**: Security hardening (Phase 4)

