# Restart System Comparison

## Overview
This document compares the two main restart methods: **Web UI "Restart System"** and **`make restart`**.

## Comparison Table

| Method | Systemd Service | Background Process | Script Used |
|--------|----------------|-------------------|-------------|
| **Web UI Restart** | ✅ `sudo systemctl restart` | ✅ `restart_server.sh` | `/api/system/restart` endpoint |
| **make restart** | ✅ `make service-restart` | ✅ `make prod-restart` | Makefile targets |

## Detailed Behavior

### 1. Web UI "Restart System" (`/api/system/restart`)

**Location:** `app/controllers/api.py` lines 1809-1926

**Logic:**
```python
1. Check if SYSTEMD_SERVICE environment variable is set
   → YES: Use `sudo systemctl restart <service_name>`
   → NO: Continue to next check

2. Check if running via gunicorn/uwsgi
   → YES: Send SIGHUP signal to parent process
   → NO: Continue to next check

3. Fallback: Use restart_server.sh script
   → Spawn script in background after 2-second delay
   → Exit current process
```

### 2. `make restart` (Makefile)

**Location:** `Makefile` lines 672-681

**Logic:**
```bash
1. Check if systemd service is active
   → YES: Call `make service-restart`
   → NO: Continue to next check

2. Check if .prod-server.pid file exists
   → YES: Call `make prod-restart`
   → NO: Call `make start`
```

### 3. `restart_server.sh` Script

**Location:** `scripts/restart_server.sh`

**Logic:**
```bash
1. Stop old process (using PID file)
   - SIGTERM first, wait up to 10 seconds
   - SIGKILL if still running

2. Wait for port 5000 to be free (up to 15 seconds)
   - Force kill remaining processes if needed

3. Start new server
   - nohup python cli.py web > logs/production.log 2>&1 &
   - Save new PID to file
```

### 4. `make prod-restart`

**Location:** `Makefile` lines 426-429

**Logic:**
```bash
1. Call `make prod-stop` (comprehensive cleanup)
2. Sleep 1 second
3. Call `make prod-start` (with extensive checks)
```

## Key Differences

### When Systemd Service is Installed:

| Feature | Web UI | make restart |
|---------|--------|-------------|
| **Method** | `sudo systemctl restart` | `make service-restart` → `sudo systemctl restart` |
| **Result** | ✅ Same | ✅ Same |

### When No Systemd Service (Background Process):

| Feature | Web UI | make restart |
|---------|--------|-------------|
| **Method** | `restart_server.sh` | `make prod-restart` |
| **Stop Process** | SIGTERM → SIGKILL (10s timeout) | Interactive with cleanup prompts |
| **Port Check** | Waits 15 seconds, then force kill | Extensive checks and user prompts |
| **Conflict Detection** | Basic | Advanced (checks for conflicts, asks user) |
| **Orphan Cleanup** | Yes | Yes (more comprehensive) |
| **Interactive** | No (silent) | Yes (prompts user) |
| **Speed** | ⚡ Faster (automated) | 🐢 Slower (interactive) |

## Current System Status

```bash
# Check current system status
systemctl list-unit-files | grep microk8s-orchestrator
# → No systemd service found (as of check)

# This means:
# - Web UI uses: restart_server.sh
# - make restart uses: make prod-restart
```

## Verdict

### ✅ Are They Equivalent?

**YES**, when systemd service is active:
- Both use `sudo systemctl restart microk8s-orchestrator`
- Identical behavior and result

**MOSTLY YES**, when running as background process:
- Both stop old process and start new one
- Both clean up orphaned processes
- Both ensure port 5000 is free

**Differences** (background process mode):
- **Web UI** (`restart_server.sh`): Fully automated, non-interactive
- **make restart** (`make prod-restart`): Interactive, more safety checks

### Recommendation

For **automated restarts** (cron, scripts, monitoring):
- Use **Web UI API**: `POST /api/system/restart`
- Or use: `scripts/restart_server.sh` directly
- Non-interactive, reliable, fast

For **manual restarts** (terminal, development):
- Use **`make restart`**: Better feedback, safer
- Interactive prompts prevent conflicts
- More detailed status information

### Making Them Identical

To make `make restart` behave exactly like Web UI restart in non-interactive mode:

```makefile
restart:
	@echo "🔄 Restarting MicroK8s Orchestrator..."
	@if systemctl is-active --quiet microk8s-orchestrator 2>/dev/null; then \
		$(MAKE) service-restart; \
	else \
		./scripts/restart_server.sh; \
	fi
```

This would make both methods use the same script for background process mode.

## Testing

To verify both methods work the same:

```bash
# Terminal 1: Start server
make start

# Terminal 2: Test Web UI restart
curl -X POST http://localhost:5000/api/system/restart \
  -H "Content-Type: application/json" \
  -H "Cookie: your_session_cookie"

# Wait 10 seconds, then test make restart
make restart
```

Both should:
1. Stop the running process cleanly
2. Wait for port to be free
3. Start new process successfully
4. Server accessible at http://localhost:5000


