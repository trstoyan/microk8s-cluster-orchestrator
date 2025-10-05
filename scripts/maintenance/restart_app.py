#!/usr/bin/env python3
"""
Utility script to gracefully restart the Flask application.
This ensures SQLAlchemy metadata is refreshed after database migrations.
"""

import os
import sys
import signal
import subprocess
import time

def find_flask_process():
    """Find running Flask processes."""
    try:
        result = subprocess.run(['pgrep', '-f', 'python.*cli.py.*web'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            pids = result.stdout.strip().split('\n')
            return [int(pid) for pid in pids if pid]
        return []
    except Exception as e:
        print(f"Error finding Flask processes: {e}")
        return []

def stop_flask_processes(pids):
    """Stop Flask processes gracefully."""
    for pid in pids:
        try:
            print(f"Stopping Flask process {pid}...")
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            print(f"Process {pid} not found (already stopped)")
        except PermissionError:
            print(f"Permission denied stopping process {pid}")
        except Exception as e:
            print(f"Error stopping process {pid}: {e}")

def wait_for_processes_to_stop(pids, timeout=10):
    """Wait for processes to stop."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        remaining_pids = []
        for pid in pids:
            try:
                os.kill(pid, 0)  # Check if process exists
                remaining_pids.append(pid)
            except ProcessLookupError:
                pass  # Process stopped
        
        if not remaining_pids:
            print("All processes stopped successfully.")
            return True
        
        time.sleep(0.5)
    
    print(f"Some processes still running after {timeout}s: {remaining_pids}")
    return False

def main():
    """Main function."""
    print("MicroK8s Cluster Orchestrator - App Restart Utility")
    print("=" * 55)
    
    # Find running Flask processes
    pids = find_flask_process()
    
    if not pids:
        print("No Flask processes found running.")
        print("You can start the application with: python cli.py web")
        return
    
    print(f"Found {len(pids)} Flask process(es): {pids}")
    
    # Stop processes
    stop_flask_processes(pids)
    
    # Wait for processes to stop
    if wait_for_processes_to_stop(pids):
        print("\n✓ Flask application stopped successfully!")
        print("\nTo restart the application:")
        print("1. Activate virtual environment: source venv/bin/activate  # if using venv")
        print("2. Start the web interface: python cli.py web")
        print("\nNote: This restart ensures SQLAlchemy picks up any database schema changes.")
    else:
        print("\n⚠ Some processes may still be running.")
        print("You may need to manually kill them or restart your terminal.")

if __name__ == '__main__':
    main()
