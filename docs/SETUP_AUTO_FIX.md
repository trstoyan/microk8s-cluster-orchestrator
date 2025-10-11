# Setup Auto-Fix Features

## Overview

The setup script now includes intelligent auto-fix capabilities that automatically detect and resolve common issues during installation.

## What Gets Auto-Fixed

### ✅ Automatically Fixed Issues

1. **Python Virtual Environment**
   - **Check**: Does `.venv` directory exist?
   - **Auto-fix**: Creates virtual environment if missing
   - **Command**: `python3 -m venv .venv`

2. **Python Dependencies**
   - **Check**: Are all requirements installed?
   - **Auto-fix**: Installs/updates packages from `requirements.txt`
   - **Command**: `.venv/bin/pip install -r requirements.txt`

3. **Log Directory**
   - **Check**: Does `logs/` directory exist?
   - **Auto-fix**: Creates logs directory with proper permissions
   - **Path**: `{project_root}/logs`

4. **Config Directory**
   - **Check**: Does `config/` directory exist?
   - **Auto-fix**: Creates config directory structure
   - **Path**: `{project_root}/config`

5. **System Directories**
   - **Check**: Do required system directories exist?
   - **Auto-fix**: Creates with appropriate permissions
   - **Directories**: `/etc/nut`, `/var/lib/nut`, `/var/log/nut`, etc.

6. **NUT (UPS) Permissions**
   - **Check**: Does `nut` user exist?
   - **Auto-fix**: Skips NUT permissions if user doesn't exist
   - **Note**: NUT is optional - only needed for UPS power management

7. **Ansible Collections**
   - **Check**: Are Ansible collections installed?
   - **Auto-fix**: Continues on collection errors (non-critical)
   - **Note**: Failed collections won't break the setup

### ℹ️  Reported but Not Auto-Fixed

1. **Database Initialization**
   - **Check**: Does database exist?
   - **Action**: Shows command to run manually
   - **Command**: `make init` or `.venv/bin/python cli.py init-db`
   - **Why**: Database init requires app context

2. **MicroK8s Installation**
   - **Check**: Is MicroK8s installed?
   - **Action**: Explains it's optional on orchestrator
   - **Command**: `sudo snap install microk8s --classic`
   - **Why**: Only needed on cluster nodes, not orchestrator

## Usage

### Run with Auto-Fix (Default)

```bash
sudo make setup
# or
sudo python3 scripts/setup_orchestrator_privileges.py
```

### See What Gets Fixed

The setup summary shows all auto-fixes applied:

```
🔧 Auto-fixes applied (5):
  • Created Python virtual environment
  • Installed Python dependencies
  • Created logs directory
  • Created config directory
  • Database initialization pending
```

## Common Scenarios

### Scenario 1: Fresh Installation

**What happens:**
1. ✅ Creates `.venv`
2. ✅ Installs all Python packages
3. ✅ Creates logs and config directories
4. ✅ Sets up system directories
5. ✅ Configures sudo permissions
6. ℹ️  Shows: "Run `make init` to initialize database"

**Manual step needed:**
```bash
make init
```

### Scenario 2: Missing Dependencies

**What happens:**
1. ✅ Detects missing packages
2. ✅ Automatically runs `pip install -r requirements.txt`
3. ✅ Updates all dependencies
4. ✅ Verifies installation

**No manual steps needed!**

### Scenario 3: NUT Not Installed

**What happens:**
1. ℹ️  Detects no `nut` user
2. ℹ️  Skips NUT-specific permissions
3. ✅ Continues setup normally
4. ℹ️  Shows: "Install NUT with: sudo apt install nut" (if needed)

**Result:** Setup succeeds, UPS features optional

### Scenario 4: Ansible Collection Failures

**What happens:**
1. ⚠️  Some collections fail to install
2. ✅ Setup continues anyway
3. ℹ️  Shows which collections failed
4. ✅ Core functionality still works

**Manual fix (if needed):**
```bash
ansible-galaxy install -r ansible/requirements.yml --force
```

## Error Messages Explained

### ❌ "chown: invalid user: 'nut:nut'"

**Meaning:** NUT (Network UPS Tools) is not installed  
**Impact:** None - UPS features are optional  
**Fix:** Install NUT only if you use UPS: `sudo apt install nut nut-client`  
**Or:** Ignore this - orchestrator works without UPS support

### ❌ "microk8s: FAILED"

**Meaning:** MicroK8s is not installed on this machine  
**Impact:** None - MicroK8s is only needed on cluster nodes  
**Fix:** Install on cluster nodes, not on orchestrator server  
**Note:** Orchestrator manages remote MicroK8s installations

### ⚠️  "Failed to install some Ansible collections"

**Meaning:** Some Ansible Galaxy collections couldn't be downloaded  
**Impact:** Minimal - most features still work  
**Fix:** Retry with: `ansible-galaxy install -r ansible/requirements.yml --force`  
**Note:** Often non-critical, depends on which collections failed

### ❌ "Database not initialized"

**Meaning:** No database file found  
**Impact:** Server won't start until database is created  
**Fix:** Run `make init` after setup completes  
**Auto-fix:** Pending - run manually after setup

## Troubleshooting

### Setup Still Fails After Auto-Fix

1. **Check the detailed output:**
   ```bash
   sudo make setup 2>&1 | tee setup.log
   ```

2. **Review setup report:**
   ```bash
   cat setup_report.json
   ```

3. **Check logs:**
   ```bash
   cat logs/production.log
   ```

4. **Run individual fixes:**
   ```bash
   # Fix Python deps
   .venv/bin/pip install -r requirements.txt
   
   # Fix database
   make init
   
   # Fix Ansible
   ansible-galaxy install -r ansible/requirements.yml --force
   ```

### Verify Auto-Fixes

```bash
# Check venv
ls -la .venv/

# Check dependencies
.venv/bin/pip list

# Check directories
ls -la logs/ config/

# Check database
ls -la *.db instance/*.db 2>/dev/null
```

## Advanced Options

### Disable Auto-Fix (Future)

```python
# In script
setup = OrchestratorPrivilegeSetup(auto_fix=False)
```

### Manual Mode

If you prefer to fix things manually:

1. Run setup: `sudo make setup`
2. Note what failed
3. Fix manually using provided commands
4. Re-run setup to verify

## Summary

**✅ Auto-fixed automatically:**
- Virtual environment
- Python dependencies  
- Directory structure
- System permissions
- Optional feature handling

**ℹ️  Needs manual action:**
- Database initialization (`make init`)
- Optional: MicroK8s on cluster nodes
- Optional: NUT for UPS support

**Result:** Setup process is much more reliable and user-friendly!

