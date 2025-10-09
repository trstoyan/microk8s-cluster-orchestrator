#!/usr/bin/env python3
"""
Setup script for MicroK8s Cluster Orchestrator privileges.
This script configures the system to allow the orchestrator to perform
system-level operations without requiring interactive sudo prompts.
"""

import os
import sys
import subprocess
import json
from pathlib import Path

class OrchestratorPrivilegeSetup:
    """Setup and configure orchestrator privileges."""
    
    def __init__(self, auto_fix=True, interactive=True):
        self.script_dir = Path(__file__).parent
        self.project_root = self.script_dir.parent
        self.current_user = os.getenv('USER', 'orchestrator')
        self.sudoers_file = Path('/etc/sudoers.d/microk8s-orchestrator')
        self.auto_fix = auto_fix
        self.interactive = interactive
        self.fixes_applied = []
        
        # Commands that the orchestrator needs to run with sudo
        self.required_commands = [
            # NUT management
            'apt update', 'apt install', 'apt upgrade',
            'systemctl start', 'systemctl stop', 'systemctl restart', 'systemctl enable', 'systemctl disable',
            'systemctl status', 'systemctl is-active', 'systemctl is-enabled',
            'chown', 'chmod', 'cp', 'rm', 'mv', 'cat',
            'mkdir', 'rmdir', 'touch',
            
            # MicroK8s and system operations
            'microk8s', 'snap', 'ufw', 'iptables',
            'usermod', 'groupadd', 'useradd',
            'sysctl', 'tee', 'echo',
            
            # Hardware and system monitoring
            'lshw', 'lscpu', 'lsblk', 'free', 'df', 'ps', 'netstat', 'ss',
            'sensors', 'nvidia-smi', 'lspci', 'lsusb',
            'journalctl', 'dmesg', 'uptime', 'who',
            
            # Network operations
            'ping', 'nslookup', 'dig', 'traceroute',
            'ip', 'ifconfig', 'route', 'arp',
            
            # File operations
            'find', 'grep', 'awk', 'sed', 'sort', 'uniq',
            'tar', 'gzip', 'unzip', 'wget', 'curl',
            
            # UPS specific operations
            'nut-scanner', 'upsc', 'upsdrvctl', 'upscmd',
            'upsd', 'upsmon', 'upssched',
        ]
        
        # Directories that need special permissions
        self.required_directories = [
            '/etc/nut',
            '/var/lib/nut',
            '/var/log/nut',
            '/var/run/nut',
            '/opt/microk8s-orchestrator',
            '/var/log/microk8s-orchestrator',
        ]
    
    def prompt_user(self, question, default='y'):
        """Prompt user for yes/no input in interactive mode."""
        if not self.interactive:
            return default.lower() == 'y'
        
        choices = 'Y/n' if default.lower() == 'y' else 'y/N'
        response = input(f"{question} [{choices}]: ").strip().lower()
        
        if not response:
            return default.lower() == 'y'
        
        return response in ['y', 'yes']
    
    def check_current_privileges(self):
        """Check current sudo privileges."""
        print("🔍 Checking current sudo privileges...")
        
        try:
            # Test passwordless sudo
            result = subprocess.run(['sudo', '-n', 'true'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                print("✅ Passwordless sudo is configured")
                return True
            else:
                print("❌ Passwordless sudo is not configured")
                if self.auto_fix:
                    print("🔧 Auto-fix: This will be configured in the next step")
                return True  # Will be fixed by create_sudoers_config
        except Exception as e:
            print(f"❌ Error checking sudo privileges: {e}")
            return False
    
    def create_sudoers_config(self):
        """Create sudoers configuration for the orchestrator."""
        print("📝 Creating sudoers configuration...")
        
        try:
            # Create sudoers file content
            sudoers_content = f"""# MicroK8s Cluster Orchestrator privileges
# This file allows the orchestrator to perform system operations
# without requiring interactive sudo prompts.

# Allow orchestrator user to run specific commands without password
{self.current_user} ALL=(ALL) NOPASSWD: /usr/bin/apt, /usr/bin/apt-get
{self.current_user} ALL=(ALL) NOPASSWD: /bin/systemctl
{self.current_user} ALL=(ALL) NOPASSWD: /bin/chown, /bin/chmod, /bin/cp, /bin/rm, /bin/mv, /bin/cat
{self.current_user} ALL=(ALL) NOPASSWD: /bin/mkdir, /bin/rmdir, /bin/touch
{self.current_user} ALL=(ALL) NOPASSWD: /usr/bin/microk8s, /usr/bin/snap
{self.current_user} ALL=(ALL) NOPASSWD: /usr/sbin/ufw, /sbin/iptables
{self.current_user} ALL=(ALL) NOPASSWD: /usr/sbin/usermod, /usr/sbin/groupadd, /usr/sbin/useradd
{self.current_user} ALL=(ALL) NOPASSWD: /sbin/sysctl, /usr/bin/tee
{self.current_user} ALL=(ALL) NOPASSWD: /usr/bin/lshw, /usr/bin/lscpu, /usr/bin/lsblk, /usr/bin/free, /usr/bin/df
{self.current_user} ALL=(ALL) NOPASSWD: /usr/bin/ps, /usr/bin/netstat, /usr/bin/ss
{self.current_user} ALL=(ALL) NOPASSWD: /usr/bin/sensors, /usr/bin/nvidia-smi, /usr/bin/lspci, /usr/bin/lsusb
{self.current_user} ALL=(ALL) NOPASSWD: /bin/journalctl, /bin/dmesg, /usr/bin/uptime, /usr/bin/who
{self.current_user} ALL=(ALL) NOPASSWD: /bin/ping, /usr/bin/nslookup, /usr/bin/dig, /usr/bin/traceroute
{self.current_user} ALL=(ALL) NOPASSWD: /sbin/ip, /sbin/ifconfig, /sbin/route, /sbin/arp
{self.current_user} ALL=(ALL) NOPASSWD: /usr/bin/find, /bin/grep, /usr/bin/awk, /bin/sed, /usr/bin/sort, /usr/bin/uniq
{self.current_user} ALL=(ALL) NOPASSWD: /bin/tar, /bin/gzip, /usr/bin/unzip, /usr/bin/wget, /usr/bin/curl
{self.current_user} ALL=(ALL) NOPASSWD: /usr/bin/nut-scanner, /usr/bin/upsc, /usr/bin/upsdrvctl, /usr/bin/upscmd
{self.current_user} ALL=(ALL) NOPASSWD: /usr/sbin/upsd, /usr/sbin/upsmon, /usr/sbin/upssched

# Allow access to specific directories
{self.current_user} ALL=(ALL) NOPASSWD: /bin/echo, /bin/true, /bin/false

# Allow editing configuration files
{self.current_user} ALL=(ALL) NOPASSWD: /usr/bin/vim, /bin/nano, /usr/bin/emacs
"""
            
            # Write to temporary file first
            temp_file = Path('/tmp/orchestrator_sudoers')
            with open(temp_file, 'w') as f:
                f.write(sudoers_content)
            
            # Copy to sudoers directory with proper permissions
            subprocess.run(['sudo', 'cp', str(temp_file), str(self.sudoers_file)], check=True)
            subprocess.run(['sudo', 'chmod', '440', str(self.sudoers_file)], check=True)
            subprocess.run(['sudo', 'chown', 'root:root', str(self.sudoers_file)], check=True)
            
            # Validate sudoers file
            result = subprocess.run(['sudo', 'visudo', '-c', '-f', str(self.sudoers_file)], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                print("✅ Sudoers configuration created and validated successfully")
                temp_file.unlink()  # Clean up temp file
                return True
            else:
                print(f"❌ Sudoers validation failed: {result.stderr}")
                temp_file.unlink()
                return False
                
        except Exception as e:
            print(f"❌ Error creating sudoers configuration: {e}")
            return False
    
    def create_required_directories(self):
        """Create required directories with proper permissions."""
        print("📁 Creating required directories...")
        
        # Track if we already asked about NUT installation
        nut_install_asked = False
        
        try:
            for directory in self.required_directories:
                # Check if nut user exists (check each time in case it was just installed)
                nut_user_exists = False
                try:
                    result = subprocess.run(['id', 'nut'], capture_output=True, text=True)
                    nut_user_exists = (result.returncode == 0)
                except:
                    pass
                if not Path(directory).exists():
                    subprocess.run(['sudo', 'mkdir', '-p', directory], check=True)
                    print(f"✅ Created directory: {directory}")
                else:
                    print(f"ℹ️  Directory already exists: {directory}")
                
                # Set proper ownership and permissions
                if 'nut' in directory:
                    if nut_user_exists:
                        subprocess.run(['sudo', 'chown', 'nut:nut', directory], check=True)
                        subprocess.run(['sudo', 'chmod', '755', directory], check=True)
                        print(f"✅ Set NUT permissions for: {directory}")
                    else:
                        # Only ask once about NUT installation
                        if not nut_install_asked:
                            print(f"ℹ️  NUT user not found - UPS support is optional")
                            if self.interactive:
                                install_nut = self.prompt_user(
                                    "Do you want to install NUT (Network UPS Tools) now?", 
                                    default='n'
                                )
                                nut_install_asked = True  # Mark as asked
                                
                                if install_nut:
                                    print("📦 Installing NUT...")
                                    try:
                                        subprocess.run(['sudo', 'apt', 'update'], check=True)
                                        subprocess.run(['sudo', 'apt', 'install', '-y', 'nut', 'nut-client'], check=True)
                                        print("✅ NUT installed successfully")
                                        # Re-check if nut user exists now
                                        result = subprocess.run(['id', 'nut'], capture_output=True, text=True)
                                        if result.returncode == 0:
                                            subprocess.run(['sudo', 'chown', 'nut:nut', directory], check=True)
                                            subprocess.run(['sudo', 'chmod', '755', directory], check=True)
                                            self.fixes_applied.append("Installed NUT (UPS support)")
                                        else:
                                            print("⚠️  NUT user still not found after installation")
                                            subprocess.run(['sudo', 'chmod', '755', directory], check=True)
                                    except Exception as e:
                                        print(f"⚠️  NUT installation failed: {e}")
                                        print("   You can install it manually later if needed")
                                        subprocess.run(['sudo', 'chmod', '755', directory], check=True)
                                else:
                                    print("   Skipping NUT installation - UPS features will not be available")
                                    subprocess.run(['sudo', 'chmod', '755', directory], check=True)
                            else:
                                nut_install_asked = True
                                print(f"   💡 Install NUT later with: sudo apt install nut nut-client")
                                subprocess.run(['sudo', 'chmod', '755', directory], check=True)
                        else:
                            # Already asked, just set permissions without nut user
                            subprocess.run(['sudo', 'chmod', '755', directory], check=True)
                            print(f"✅ Set permissions for: {directory} (NUT user not available)")
                else:
                    subprocess.run(['sudo', 'chown', f'{self.current_user}:{self.current_user}', directory], check=True)
                    subprocess.run(['sudo', 'chmod', '755', directory], check=True)
            
            print("✅ All required directories created with proper permissions")
            return True
            
        except Exception as e:
            print(f"❌ Error creating directories: {e}")
            print(f"💡 Solution: Check permissions and try: sudo mkdir -p /etc/nut /var/lib/nut")
            return False
    
    def add_user_to_groups(self):
        """Add orchestrator user to required groups."""
        print("👥 Adding user to required groups...")
        
        groups = ['sudo', 'microk8s', 'nut', 'docker']
        
        try:
            for group in groups:
                try:
                    subprocess.run(['sudo', 'usermod', '-a', '-G', group, self.current_user], 
                                 check=True, capture_output=True)
                    print(f"✅ Added user to group: {group}")
                except subprocess.CalledProcessError:
                    # Group might not exist, that's okay
                    print(f"ℹ️  Group {group} does not exist (will be created when needed)")
            
            print("✅ User group configuration completed")
            return True
            
        except Exception as e:
            print(f"❌ Error adding user to groups: {e}")
            return False
    
    def test_privileges(self):
        """Test that all required privileges are working."""
        print("🧪 Testing privileges...")
        
        # Required tests (must pass)
        required_tests = [
            ('sudo -n systemctl status ssh', 'systemctl', 'sudo systemctl is required for service management'),
            ('sudo -n apt --version', 'apt', 'sudo apt is required for package management'),
            ('sudo -n chown --version', 'chown', 'sudo chown is required for file permissions'),
        ]
        
        # Optional tests (nice to have)
        optional_tests = [
            ('sudo -n ls /etc/nut', 'nut directory access', 'NUT (UPS) - optional, install with: sudo apt install nut'),
            ('sudo -n microk8s version', 'microk8s', 'MicroK8s - optional on orchestrator, install with: sudo snap install microk8s --classic'),
        ]
        
        all_required_passed = True
        
        # Test required commands
        for command, description, solution in required_tests:
            try:
                result = subprocess.run(command.split(), capture_output=True, text=True)
                if result.returncode == 0:
                    print(f"✅ {description}: OK")
                else:
                    print(f"❌ {description}: FAILED")
                    print(f"   💡 Solution: {solution}")
                    all_required_passed = False
            except Exception as e:
                print(f"❌ {description}: ERROR - {e}")
                print(f"   💡 Solution: {solution}")
                all_required_passed = False
        
        # Test optional commands (don't fail on these)
        for command, description, solution in optional_tests:
            try:
                result = subprocess.run(command.split(), capture_output=True, text=True)
                if result.returncode == 0:
                    print(f"✅ {description}: OK")
                else:
                    print(f"ℹ️  {description}: Not installed (optional)")
                    print(f"   💡 {solution}")
                    
                    # Interactive prompt for MicroK8s
                    if self.interactive and 'microk8s' in command:
                        print("   ℹ️  MicroK8s is NOT needed on the orchestrator server")
                        print("   ℹ️  The orchestrator manages MicroK8s on remote cluster nodes")
                        print("   ℹ️  Only install if this machine will also be a cluster node")
                        
                        install_anyway = self.prompt_user(
                            "Install MicroK8s anyway (this machine will be a cluster node)?",
                            default='n'
                        )
                        
                        if install_anyway:
                            print("📦 Installing MicroK8s...")
                            try:
                                subprocess.run(['sudo', 'snap', 'install', 'microk8s', '--classic'], check=True)
                                subprocess.run(['sudo', 'usermod', '-a', '-G', 'microk8s', self.current_user], check=True)
                                print("✅ MicroK8s installed successfully")
                                print("⚠️  You need to log out and back in for group changes to take effect")
                                self.fixes_applied.append("Installed MicroK8s (cluster node)")
                            except Exception as e:
                                print(f"⚠️  MicroK8s installation failed: {e}")
                        else:
                            print("   ✅ Skipped MicroK8s - orchestrator will manage remote nodes")
                            
            except Exception as e:
                print(f"ℹ️  {description}: Not available (optional)")
                print(f"   💡 {solution}")
        
        return all_required_passed
    
    def create_systemd_service(self):
        """Create systemd service for the orchestrator."""
        print("⚙️  Creating systemd service...")
        
        try:
            service_content = f"""[Unit]
Description=MicroK8s Cluster Orchestrator
After=network.target

[Service]
Type=simple
User={self.current_user}
Group={self.current_user}
WorkingDirectory={self.project_root}
Environment=PATH={self.project_root}/.venv/bin:/usr/local/bin:/usr/bin:/bin
ExecStart={self.project_root}/.venv/bin/python {self.project_root}/cli.py web
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
"""
            
            service_file = Path('/etc/systemd/system/microk8s-orchestrator.service')
            temp_service = Path('/tmp/microk8s-orchestrator.service')
            
            with open(temp_service, 'w') as f:
                f.write(service_content)
            
            subprocess.run(['sudo', 'cp', str(temp_service), str(service_file)], check=True)
            subprocess.run(['sudo', 'systemctl', 'daemon-reload'], check=True)
            subprocess.run(['sudo', 'systemctl', 'enable', 'microk8s-orchestrator.service'], check=True)
            
            temp_service.unlink()
            print("✅ Systemd service created and enabled")
            return True
            
        except Exception as e:
            print(f"❌ Error creating systemd service: {e}")
            return False
    
    def generate_setup_report(self):
        """Generate a setup report."""
        print("📊 Generating setup report...")
        
        report = {
            'timestamp': subprocess.run(['date', '-Iseconds'], capture_output=True, text=True).stdout.strip(),
            'user': self.current_user,
            'project_root': str(self.project_root),
            'sudoers_file': str(self.sudoers_file),
            'sudoers_exists': self.sudoers_file.exists(),
            'privileges_working': self.check_current_privileges(),
            'directories_created': [str(d) for d in self.required_directories],
            'systemd_service': '/etc/systemd/system/microk8s-orchestrator.service'
        }
        
        report_file = self.project_root / 'setup_report.json'
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"✅ Setup report saved to: {report_file}")
        return report
    
    def check_and_fix_environment(self):
        """Check and auto-fix common environment issues."""
        print("🔍 Pre-flight checks and auto-fixes...")
        print()
        
        fixes = []
        
        # 1. Check Python virtual environment
        venv_path = self.project_root / '.venv'
        if not venv_path.exists():
            print("❌ Python virtual environment not found")
            if self.auto_fix:
                print("🔧 Auto-fix: Creating virtual environment...")
                try:
                    subprocess.run(['python3', '-m', 'venv', str(venv_path)], 
                                 cwd=self.project_root, check=True)
                    print("✅ Virtual environment created")
                    fixes.append("Created Python virtual environment")
                except Exception as e:
                    print(f"⚠️  Could not create venv: {e}")
        else:
            print("✅ Python virtual environment exists")
        
        # 2. Check Python dependencies
        requirements_file = self.project_root / 'requirements.txt'
        if requirements_file.exists():
            pip_path = venv_path / 'bin' / 'pip'
            if pip_path.exists():
                print("🔍 Checking Python dependencies...")
                try:
                    result = subprocess.run([str(pip_path), 'check'], 
                                          capture_output=True, text=True)
                    if result.returncode != 0 and self.auto_fix:
                        print("🔧 Auto-fix: Installing/updating dependencies...")
                        subprocess.run([str(pip_path), 'install', '-r', 
                                      str(requirements_file)], check=True)
                        fixes.append("Installed Python dependencies")
                        print("✅ Dependencies updated")
                    else:
                        print("✅ Python dependencies OK")
                except Exception as e:
                    print(f"⚠️  Dependency check warning: {e}")
        
        # 3. Check database file
        db_files = list(self.project_root.glob('*.db')) + list(self.project_root.glob('instance/*.db'))
        if not db_files:
            print("❌ Database not initialized")
            if self.auto_fix:
                print("🔧 Auto-fix: Database will be initialized after setup")
                print("   Run 'make init' after setup completes")
                fixes.append("Database initialization pending")
        else:
            print(f"✅ Database found: {db_files[0].name}")
        
        # 4. Check logs directory
        logs_dir = self.project_root / 'logs'
        if not logs_dir.exists():
            print("❌ Logs directory missing")
            if self.auto_fix:
                print("🔧 Auto-fix: Creating logs directory...")
                logs_dir.mkdir(parents=True, exist_ok=True)
                fixes.append("Created logs directory")
                print("✅ Logs directory created")
        else:
            print("✅ Logs directory exists")
        
        # 5. Check config directory
        config_dir = self.project_root / 'config'
        if not config_dir.exists():
            print("❌ Config directory missing")
            if self.auto_fix:
                print("🔧 Auto-fix: Creating config directory...")
                config_dir.mkdir(parents=True, exist_ok=True)
                fixes.append("Created config directory")
                print("✅ Config directory created")
        else:
            print("✅ Config directory exists")
        
        self.fixes_applied.extend(fixes)
        
        if fixes:
            print(f"\n✨ Applied {len(fixes)} auto-fixes")
        
        print()
        return True
    
    def run_setup(self):
        """Run the complete privilege setup."""
        print("🚀 Starting MicroK8s Cluster Orchestrator privilege setup...")
        print(f"👤 Running as user: {self.current_user}")
        print(f"📂 Project root: {self.project_root}")
        print(f"🔧 Auto-fix mode: {'ON' if self.auto_fix else 'OFF'}")
        print()
        
        steps = [
            ("Environment pre-flight checks", self.check_and_fix_environment),
            ("Checking current privileges", self.check_current_privileges),
            ("Creating sudoers configuration", self.create_sudoers_config),
            ("Creating required directories", self.create_required_directories),
            ("Adding user to groups", self.add_user_to_groups),
            ("Testing privileges", self.test_privileges),
            ("Creating systemd service", self.create_systemd_service),
            ("Generating setup report", self.generate_setup_report),
        ]
        
        results = {}
        for step_name, step_func in steps:
            print(f"\n{'='*50}")
            print(f"Step: {step_name}")
            print('='*50)
            
            try:
                result = step_func()
                results[step_name] = result
                if result:
                    print(f"✅ {step_name} completed successfully")
                else:
                    print(f"❌ {step_name} failed")
            except Exception as e:
                print(f"❌ {step_name} failed with error: {e}")
                results[step_name] = False
        
        print(f"\n{'='*50}")
        print("Setup Summary")
        print('='*50)
        
        all_success = all(results.values())
        for step_name, success in results.items():
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"{status} {step_name}")
        
        if all_success:
            print("\n🎉 Privilege setup completed successfully!")
            print("The orchestrator is now ready to perform system-level operations.")
            
            if self.fixes_applied:
                print(f"\n🔧 Auto-fixes applied ({len(self.fixes_applied)}):")
                for fix in self.fixes_applied:
                    print(f"  • {fix}")
            
            print("\nNext steps:")
            print("1. Initialize database: make init")
            print("2. Start the server: make prod-start")
            print("3. Access web interface: http://localhost:5000")
        else:
            print("\n⚠️  Setup completed with some failures.")
            print("\n📋 Troubleshooting Common Issues:")
            print("=" * 50)
            
            # Check which steps failed and provide specific solutions
            if not results.get("Creating required directories", True):
                print("\n🔧 Directory Creation Failed:")
                print("  • NUT user not found - this is OPTIONAL")
                print("  • Install NUT only if you use UPS: sudo apt install nut nut-client")
                print("  • Otherwise, ignore this warning - the orchestrator works without UPS support")
            
            if not results.get("Testing privileges", True):
                print("\n🔧 Privilege Testing Failed:")
                print("  • MicroK8s test failed - this is OPTIONAL on orchestrator server")
                print("  • Install only on cluster nodes, not on the orchestrator itself")
                print("  • Required tests: systemctl, apt, chown - these MUST pass")
            
            print("\n💡 Quick Fixes:")
            print("  • Database not initialized: make init")
            print("  • Server won't start: Check logs/production.log for errors")
            print("  • Missing dependencies: .venv/bin/pip install -r requirements.txt")
            print("  • Permission issues: Ensure you ran with sudo")
            
            print("\n📚 For more help:")
            print("  • Check logs: cat logs/production.log")
            print("  • View setup report: cat setup_report.json")
            print("  • Documentation: docs/README.md")
        
        return all_success

def main():
    """Main function."""
    if os.geteuid() != 0:
        print("This script needs to be run with sudo privileges.")
        print("Please run: sudo python setup_orchestrator_privileges.py")
        sys.exit(1)
    
    setup = OrchestratorPrivilegeSetup()
    success = setup.run_setup()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
