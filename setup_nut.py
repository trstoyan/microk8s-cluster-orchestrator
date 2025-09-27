#!/usr/bin/env python3
"""
Simple NUT setup script for the MicroK8s Cluster Orchestrator.
This script will install and configure NUT for UPS power management.
"""

import sys
import os
import subprocess

def print_step(step, message):
    """Print a step with formatting."""
    print(f"\n{'='*50}")
    print(f"Step {step}: {message}")
    print('='*50)

def run_command(cmd, description):
    """Run a command and handle errors."""
    print(f"Running: {description}")
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"✓ {description} - Success")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ {description} - Failed")
        print(f"Error: {e.stderr}")
        return False

def check_root():
    """Check if running as root or with sudo."""
    if os.geteuid() == 0:
        return True
    
    # Check if user can run sudo
    try:
        subprocess.run(['sudo', '-n', 'true'], check=True, capture_output=True)
        return True
    except subprocess.CalledProcessError:
        return False

def main():
    """Main setup function."""
    print("MicroK8s Cluster Orchestrator - NUT Setup")
    print("This script will install and configure NUT for UPS power management.")
    
    # Check permissions
    if not check_root():
        print("\n❌ Error: This script requires root privileges or sudo access.")
        print("Please run with sudo or as root:")
        print("  sudo python3 setup_nut.py")
        sys.exit(1)
    
    # Step 1: Install NUT packages
    print_step(1, "Installing NUT packages")
    if not run_command(['sudo', 'apt', 'update'], "Updating package list"):
        sys.exit(1)
    
    packages = ['nut', 'nut-client', 'nut-server', 'nut-driver']
    for package in packages:
        if not run_command(['sudo', 'apt', 'install', '-y', package], f"Installing {package}"):
            print(f"Warning: Failed to install {package}")
    
    # Step 2: Create NUT configuration directory
    print_step(2, "Creating NUT configuration directory")
    if not run_command(['sudo', 'mkdir', '-p', '/etc/nut'], "Creating /etc/nut directory"):
        sys.exit(1)
    
    if not run_command(['sudo', 'chown', '-R', 'nut:nut', '/etc/nut'], "Setting ownership"):
        sys.exit(1)
    
    if not run_command(['sudo', 'chmod', '755', '/etc/nut'], "Setting permissions"):
        sys.exit(1)
    
    # Step 3: Create basic NUT configuration
    print_step(3, "Creating basic NUT configuration")
    
    # nut.conf
    nut_conf = "MODE=standalone\n"
    with open('/tmp/nut.conf', 'w') as f:
        f.write(nut_conf)
    
    if not run_command(['sudo', 'cp', '/tmp/nut.conf', '/etc/nut/nut.conf'], "Creating nut.conf"):
        sys.exit(1)
    
    if not run_command(['sudo', 'chown', 'nut:nut', '/etc/nut/nut.conf'], "Setting nut.conf ownership"):
        sys.exit(1)
    
    if not run_command(['sudo', 'chmod', '644', '/etc/nut/nut.conf'], "Setting nut.conf permissions"):
        sys.exit(1)
    
    # upsd.users
    upsd_users = """# NUT users file
[admin]
    password = adminpass
    actions = SET
    instcmds = ALL
    upscmds = ALL

[monuser]
    password = monpass
    actions = GET
    instcmds = ALL
"""
    with open('/tmp/upsd.users', 'w') as f:
        f.write(upsd_users)
    
    if not run_command(['sudo', 'cp', '/tmp/upsd.users', '/etc/nut/upsd.users'], "Creating upsd.users"):
        sys.exit(1)
    
    if not run_command(['sudo', 'chown', 'nut:nut', '/etc/nut/upsd.users'], "Setting upsd.users ownership"):
        sys.exit(1)
    
    if not run_command(['sudo', 'chmod', '600', '/etc/nut/upsd.users'], "Setting upsd.users permissions"):
        sys.exit(1)
    
    # Step 4: Enable and start NUT services
    print_step(4, "Enabling NUT services")
    services = ['nut-server', 'nut-driver', 'nut-client']
    for service in services:
        run_command(['sudo', 'systemctl', 'enable', service], f"Enabling {service}")
        run_command(['sudo', 'systemctl', 'start', service], f"Starting {service}")
    
    # Step 5: Add user to nut group
    print_step(5, "Adding user to nut group")
    username = os.environ.get('SUDO_USER', os.environ.get('USER', 'root'))
    if username != 'root':
        run_command(['sudo', 'usermod', '-a', '-G', 'nut', username], f"Adding {username} to nut group")
    
    # Cleanup
    try:
        os.unlink('/tmp/nut.conf')
        os.unlink('/tmp/upsd.users')
    except:
        pass
    
    # Final step
    print_step(6, "Setup Complete!")
    print("\n✅ NUT has been installed and configured successfully!")
    print("\nNext steps:")
    print("1. Connect your UPS device via USB")
    print("2. Run the orchestrator to scan for UPS devices:")
    print("   python cli.py ups scan")
    print("3. Create power management rules:")
    print("   python cli.py ups rules create")
    print("4. Start power monitoring:")
    print("   python cli.py ups monitor start")
    print("\nWeb interface: http://localhost:5000/ups")
    print("Login: admin / admin123")
    
    print("\n⚠️  Security Note:")
    print("Please change the default passwords in /etc/nut/upsd.users")

if __name__ == '__main__':
    main()
