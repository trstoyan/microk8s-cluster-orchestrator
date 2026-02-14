# Ansible Temporary Directory Fix

## Problem

**Operation ID: 136** - "Check Node Status" for `devmod-09` failed with:

```
Failed to create temporary directory. In some cases, you may have been able 
to authenticate and did not have permissions on the target directory. 
Consider changing the remote tmp path in ansible.cfg to a path rooted in "/tmp"
```

### Root Cause
Ansible was trying to create temporary directories in `/home/sumix/.ansible/tmp` on remote nodes, but:
- This directory may not exist
- User may not have permissions to create it
- Home directory may have restrictive permissions

The playbook successfully gathered all health information but failed at the final step when trying to write the report to a file (which requires Ansible to copy the file, which uses a temporary directory).

## Solution

Updated `/ansible/ansible.cfg` to specify a writable temporary directory path:

```ini
[defaults]
...
remote_tmp = /tmp/.ansible-${USER}/tmp
deprecation_warnings = False
```

### What This Does

1. **`remote_tmp = /tmp/.ansible-${USER}/tmp`**
   - Tells Ansible to use `/tmp` for temporary files on remote nodes
   - `/tmp` is always writable by all users on Linux systems
   - `${USER}` expands to the SSH user on the remote node (e.g., `sumix`)
   - Prevents permission issues in home directories

2. **`deprecation_warnings = False`**
   - Disables deprecation warnings (like the yaml callback plugin warning)
   - Cleaner output in operation logs

## Impact

This fix affects **ALL** Ansible playbook executions:
- ✅ Check Node Status
- ✅ Setup New Node
- ✅ Install MicroK8s
- ✅ Configure Wake-on-LAN
- ✅ Setup Longhorn Prerequisites
- ✅ All other playbooks

## Testing

To verify the fix works, re-run the failed operation:

### Via Web UI:
1. Go to Nodes → devmod-09
2. Click "Actions" → "Check Status"
3. The operation should now complete successfully

### Via CLI:
```bash
cd /home/sumix/sDisk/workinprogress/microk8s-cluster-orchestrator
source .venv/bin/activate
cd ansible
ansible-playbook -i inventory/dynamic_inventory.ini playbooks/check_node_status.yml -l devmod-09
```

## Expected Result

The playbook should now complete all tasks including:
```yaml
TASK [Write health report to file] ***************************************************
changed: [devmod-09]

PLAY RECAP ***************************************************************************
devmod-09                  : ok=15   changed=1    unreachable=0    failed=0
```

The health report will be written to: `/tmp/microk8s_health_devmod-09.json` on the remote node.

## Technical Details

### Why `/tmp`?
- `/tmp` has permission mode `1777` (sticky bit + world writable)
- Any user can create directories/files in `/tmp`
- Each user's files are protected from other users (sticky bit)
- Standard location for temporary files on all Unix/Linux systems

### Why `${USER}` variable?
- Creates isolated directory per user
- Prevents conflicts between different SSH users
- Ansible automatically expands `${USER}` to the remote user name
- Example: `/tmp/.ansible-sumix/tmp`

### Alternative Configurations

If you want to use a different location:

```ini
# Use a custom temp directory
remote_tmp = /var/tmp/.ansible-${USER}/tmp

# Use absolute path (no variable expansion)
remote_tmp = /tmp/ansible_tmp

# Use user's home (not recommended, may have permission issues)
remote_tmp = ~/.ansible/tmp
```

## Related Files

- **Fixed:** `ansible/ansible.cfg`
- **Affected Playbooks:** All playbooks in `ansible/playbooks/`
- **Operation Log:** Operation #136 in the web UI
- **Similar Issues:** SSH key setup also fixed (see `setup_node_ssh.sh`)

## Prevention

This fix prevents similar issues in the future:
- ✅ All new nodes will use `/tmp` for Ansible operations
- ✅ No more permission denied errors for temporary files
- ✅ Consistent behavior across all nodes
- ✅ Works regardless of home directory permissions

## Additional Notes

The orchestrator dynamically generates Ansible inventory before running playbooks, so this configuration will be used for all operations triggered through:
- Web UI (nodes page, operations page)
- API endpoints
- CLI commands
- Scheduled/automated tasks

No restart of the orchestrator is required - the change takes effect immediately for the next playbook execution.

