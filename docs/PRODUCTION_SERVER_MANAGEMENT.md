# Production Server Management Guide

This guide explains how to use the `make` commands to manage the production server as a background service.

## Overview

The MicroK8s Cluster Orchestrator includes convenient Make commands to manage the production web server as a background process. This allows you to start, stop, and monitor the server with simple commands.

## Available Commands

### Start Production Server

```bash
make prod-start
```

**Description:** Starts the production server in the background using `nohup`. The server will:
- Run on `0.0.0.0:5000` (accessible from any network interface)
- Log output to `logs/production.log`
- Store its process ID in `.prod-server.pid`
- Continue running even after you log out

**Output Example:**
```
🚀 Starting production server in background...
✅ Production server started successfully!
   PID: 12345
   Access at: http://0.0.0.0:5000
   Logs: logs/production.log

Use 'make prod-stop' to stop the server
Use 'make prod-logs' to view logs
```

**Note:** If the server is already running, you'll get a warning message. Use `make prod-restart` to restart it.

### Stop Production Server

```bash
make prod-stop
```

**Description:** Stops the running production server gracefully.

**Output Example:**
```
🛑 Stopping production server...
✅ Production server stopped (PID: 12345)
```

### Restart Production Server

```bash
make prod-restart
```

**Description:** Stops the current server (if running) and starts a new instance. This is useful when you've updated the code or configuration.

**Output Example:**
```
🛑 Stopping production server...
✅ Production server stopped (PID: 12345)
🔄 Restarting production server...
🚀 Starting production server in background...
✅ Production server started successfully!
```

### Check Server Status

```bash
make prod-status
```

**Description:** Displays the current status of the production server, including PID, memory usage, CPU usage, and uptime.

**Output Example (Running):**
```
📊 Production Server Status:
==============================
✅ Status: RUNNING
   PID: 12345
   URL: http://0.0.0.0:5000

  PID  PPID CMD                         %MEM %CPU     ELAPSED
12345     1 python cli.py web           2.3  0.5       01:23:45
```

**Output Example (Stopped):**
```
📊 Production Server Status:
==============================
❌ Status: STOPPED
   No PID file found

Use 'make prod-start' to start the server
```

### View Server Logs

```bash
make prod-logs
```

**Description:** Displays the production server logs in real-time (follows the log file). Press `Ctrl+C` to exit.

**Output Example:**
```
📋 Production Server Logs:
==============================
[2025-10-09 14:30:15] INFO: Server starting on 0.0.0.0:5000
[2025-10-09 14:30:16] INFO: Database initialized
[2025-10-09 14:30:20] INFO: 127.0.0.1 - GET / - 200
```

## Quick Start

### 1. Start the Server

```bash
make prod-start
```

### 2. Check Status

```bash
make prod-status
```

### 3. View Logs (Optional)

```bash
make prod-logs
```

Press `Ctrl+C` to exit log viewing.

### 4. Stop the Server (When Done)

```bash
make prod-stop
```

## Files and Directories

### PID File
- **Location:** `.prod-server.pid`
- **Purpose:** Stores the process ID of the running server
- **Note:** Automatically cleaned up when the server stops
- **Git:** Ignored (added to `.gitignore`)

### Log Files
- **Location:** `logs/production.log`
- **Purpose:** Contains all server output (stdout and stderr)
- **Rotation:** Logs are appended. You may want to rotate them periodically.
- **Git:** Directory ignored (already in `.gitignore`)

## Troubleshooting

### Server Won't Start

1. **Check if port 5000 is already in use:**
   ```bash
   sudo lsof -i :5000
   ```

2. **Check the logs for errors:**
   ```bash
   cat logs/production.log
   ```

3. **Ensure virtual environment is set up:**
   ```bash
   make install
   ```

### Server Shows as Running but Not Accessible

1. **Verify the process is actually running:**
   ```bash
   make prod-status
   ```

2. **Check firewall settings:**
   ```bash
   sudo ufw status
   ```

3. **Try accessing locally first:**
   ```bash
   curl http://localhost:5000
   ```

### Stale PID File

If you see "PID file exists but process not running":

```bash
rm .prod-server.pid
make prod-start
```

Or simply use:
```bash
make prod-restart
```

## Comparison with Other Methods

### Make Commands vs Direct Python

**Make Commands (Recommended):**
```bash
make prod-start  # Background process with logging
make prod-stop   # Clean shutdown
```

**Direct Python:**
```bash
.venv/bin/python cli.py web --host 0.0.0.0 --port 5000
```
- Runs in foreground (blocks terminal)
- No automatic logging
- Stops when terminal closes

### Make Commands vs Systemd Service

**Make Commands:**
- ✅ Quick to start/stop
- ✅ No root/sudo required
- ✅ Easy debugging with logs
- ❌ Doesn't auto-restart on failure
- ❌ Doesn't start on boot

**Systemd Service:**
- ✅ Auto-restart on failure
- ✅ Starts on boot
- ✅ Better for production
- ❌ Requires sudo/root
- ❌ More complex setup

**Recommendation:** Use Make commands for development and testing. Use systemd service for production deployment.

See [DEPLOYMENT.md](DEPLOYMENT.md) for systemd setup instructions.

## Security Considerations

### Network Binding

The server binds to `0.0.0.0:5000`, making it accessible from any network interface:
- **LAN Access:** Other devices on your local network can access it
- **Public Access:** If your machine has a public IP, the server is exposed

**For development/testing only, consider:**
```bash
# Modify Makefile to use localhost only
--host 127.0.0.1
```

### Production Deployment

For production:
1. Use a reverse proxy (nginx/Apache)
2. Enable HTTPS/SSL
3. Use the systemd service
4. Configure firewall rules
5. Use gunicorn/uwsgi instead of Flask's built-in server

See [PRODUCTION_DEPLOYMENT.md](PRODUCTION_DEPLOYMENT.md) for details.

## Advanced Usage

### Custom Port

To use a different port, modify the `prod-start` target in the Makefile:

```makefile
# Change port from 5000 to 8080
nohup .venv/bin/python cli.py web --host 0.0.0.0 --port 8080 > logs/production.log 2>&1 & echo $$! > .prod-server.pid
```

### Multiple Instances

To run multiple instances on different ports:

1. Create separate make targets (e.g., `prod-start-8080`, `prod-start-8081`)
2. Use different PID files (e.g., `.prod-server-8080.pid`)
3. Use different log files (e.g., `logs/production-8080.log`)

### Automated Monitoring

Create a cron job to monitor the server:

```bash
# Add to crontab
*/5 * * * * cd /path/to/project && make prod-status > /dev/null || make prod-start
```

This checks every 5 minutes and restarts if stopped.

## Summary

The production server management commands provide a simple, user-friendly way to run the MicroK8s Cluster Orchestrator as a background service:

- **One-command start:** `make prod-start`
- **One-command stop:** `make prod-stop`
- **Easy monitoring:** `make prod-status` and `make prod-logs`
- **Quick restart:** `make prod-restart`

For production deployments with auto-restart and boot-on-startup, use the systemd service instead.

