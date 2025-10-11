#!/bin/bash
#
# MicroK8s Cluster Orchestrator - Node SSH Setup Script
# This script automatically configures SSH access for the orchestrator
#
# Usage:
#   curl -sSL http://orchestrator:5000/setup/node-ssh?node_id=1 | bash
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script variables (will be replaced by server)
NODE_ID="{{node_id}}"
NODE_HOSTNAME="{{hostname}}"
SSH_PUBLIC_KEY="{{ssh_public_key}}"
ORCHESTRATOR_IP="{{orchestrator_ip}}"
SSH_USER="{{ssh_user}}"

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   MicroK8s Cluster Orchestrator - Node SSH Setup          ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}Node:${NC} $NODE_HOSTNAME (ID: $NODE_ID)"
echo -e "${GREEN}User:${NC} $SSH_USER"
echo -e "${GREEN}Orchestrator:${NC} $ORCHESTRATOR_IP"
echo ""

# Function to print status
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    print_error "Please do NOT run this script as root!"
    print_status "Run it as the user that will be used for SSH access: $SSH_USER"
    exit 1
fi

# Check if running as correct user
CURRENT_USER=$(whoami)
if [ "$CURRENT_USER" != "$SSH_USER" ]; then
    print_warning "Running as '$CURRENT_USER' but expected user is '$SSH_USER'"
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

print_status "Starting prerequisite checks..."
echo ""

# Check prerequisites
HAS_ERRORS=0

# Check if SSH is installed
print_status "Checking for SSH..."
if command -v ssh &> /dev/null; then
    SSH_VERSION=$(ssh -V 2>&1 | head -n1)
    print_success "SSH is installed: $SSH_VERSION"
else
    print_error "SSH is not installed!"
    print_status "Install with: sudo apt install openssh-client (Debian/Ubuntu)"
    print_status "           or: sudo pacman -S openssh (Arch)"
    HAS_ERRORS=1
fi

# Check if .ssh directory exists
print_status "Checking SSH directory..."
SSH_DIR="$HOME/.ssh"
if [ -d "$SSH_DIR" ]; then
    print_success "SSH directory exists: $SSH_DIR"
else
    print_warning "SSH directory does not exist, will create it"
fi

# Check if authorized_keys exists
print_status "Checking authorized_keys file..."
AUTH_KEYS="$SSH_DIR/authorized_keys"
if [ -f "$AUTH_KEYS" ]; then
    print_success "authorized_keys file exists"
    EXISTING_KEYS=$(wc -l < "$AUTH_KEYS")
    print_status "Current keys: $EXISTING_KEYS"
else
    print_warning "authorized_keys file does not exist, will create it"
fi

# Check if key already exists
if [ -f "$AUTH_KEYS" ]; then
    KEY_COMMENT="orchestrator-node-${NODE_ID}"
    if grep -q "$KEY_COMMENT" "$AUTH_KEYS"; then
        print_warning "Key for this node already exists in authorized_keys"
        print_status "The existing key will be updated"
    fi
fi

# Check network connectivity to orchestrator
print_status "Checking network connectivity to orchestrator..."
if ping -c 1 -W 2 "$ORCHESTRATOR_IP" &> /dev/null; then
    print_success "Can reach orchestrator at $ORCHESTRATOR_IP"
else
    print_warning "Cannot ping orchestrator at $ORCHESTRATOR_IP"
    print_status "This might be normal if ICMP is blocked"
fi

# Check if curl is available
print_status "Checking for curl..."
if command -v curl &> /dev/null; then
    print_success "curl is installed"
else
    print_error "curl is not installed (but you're running this script, so it should be available)"
    HAS_ERRORS=1
fi

echo ""

if [ $HAS_ERRORS -eq 1 ]; then
    print_error "Prerequisites check failed! Please fix the errors above."
    exit 1
fi

print_success "All prerequisites passed!"
echo ""

# Validate SSH public key
if [ -z "$SSH_PUBLIC_KEY" ] || [ "$SSH_PUBLIC_KEY" == "None" ]; then
    print_error "No SSH public key provided by orchestrator!"
    print_status "Please generate an SSH key for this node in the orchestrator first."
    exit 1
fi

echo ""
print_status "SSH Public Key received from orchestrator:"
echo -e "${BLUE}══════════════════════════════════════════════════${NC}"
echo "$SSH_PUBLIC_KEY" | sed 's/^/  /'
echo -e "${BLUE}══════════════════════════════════════════════════${NC}"
echo ""

print_status "Configuring SSH access..."
echo ""

# Create .ssh directory if it doesn't exist
if [ ! -d "$SSH_DIR" ]; then
    print_status "Creating SSH directory: $SSH_DIR"
    mkdir -p "$SSH_DIR"
    chmod 700 "$SSH_DIR"
    print_success "SSH directory created"
fi

# Create or update authorized_keys
if [ ! -f "$AUTH_KEYS" ]; then
    print_status "Creating authorized_keys file: $AUTH_KEYS"
    touch "$AUTH_KEYS"
    chmod 600 "$AUTH_KEYS"
    print_success "authorized_keys file created"
fi

# Prepare key with comment
KEY_COMMENT="orchestrator-node-${NODE_ID}"

# Ensure SSH_PUBLIC_KEY has the comment at the end
if [[ "$SSH_PUBLIC_KEY" != *"$KEY_COMMENT"* ]]; then
    print_status "Adding comment to SSH key..."
    SSH_PUBLIC_KEY_WITH_COMMENT="${SSH_PUBLIC_KEY} ${KEY_COMMENT}"
else
    SSH_PUBLIC_KEY_WITH_COMMENT="$SSH_PUBLIC_KEY"
fi

# Remove old key if exists (to avoid duplicates)
if grep -q "$KEY_COMMENT" "$AUTH_KEYS" 2>/dev/null; then
    print_status "Removing old key for this node..."
    sed -i "/$KEY_COMMENT/d" "$AUTH_KEYS"
    print_success "Old key removed"
fi

# Show what we're about to add
echo ""
print_status "Preparing to add SSH public key..."
echo -e "${BLUE}──────────────────────────────────────${NC}"
print_status "Key type: $(echo $SSH_PUBLIC_KEY_WITH_COMMENT | awk '{print $1}')"
print_status "Key fingerprint: $(echo $SSH_PUBLIC_KEY_WITH_COMMENT | awk '{print $2}' | head -c 32)..."
print_status "Comment: $KEY_COMMENT"
echo -e "${BLUE}──────────────────────────────────────${NC}"

# Count keys before
KEYS_BEFORE=$(wc -l < "$AUTH_KEYS" 2>/dev/null || echo "0")

# Add new key
echo ""
print_status "Adding SSH public key to authorized_keys..."
print_status "Keys before: $KEYS_BEFORE"

# Write the key
echo "$SSH_PUBLIC_KEY_WITH_COMMENT" >> "$AUTH_KEYS"

# Count keys after
KEYS_AFTER=$(wc -l < "$AUTH_KEYS")
print_status "Keys after: $KEYS_AFTER"

if [ "$KEYS_AFTER" -gt "$KEYS_BEFORE" ]; then
    print_success "✓ SSH key written to file! (added 1 line)"
else
    print_error "✗ No line was added to file!"
fi

# Ensure correct permissions
print_status "Setting correct permissions..."
chmod 700 "$SSH_DIR"
chmod 600 "$AUTH_KEYS"
print_success "Permissions set correctly"

# Verify the key was added
echo ""
print_status "Verifying SSH key was added correctly..."
echo -e "${BLUE}══════════════════════════════════════════════════${NC}"
print_status "Searching for: $KEY_COMMENT"

if grep -q "$KEY_COMMENT" "$AUTH_KEYS"; then
    print_success "✓ Key found in authorized_keys!"
    echo ""
    print_status "Complete authorized_keys file (${KEYS_AFTER} lines):"
    cat -n "$AUTH_KEYS" | sed 's/^/  /'
else
    print_error "✗ Key NOT found in authorized_keys!"
    echo ""
    print_status "What was written:"
    echo "$SSH_PUBLIC_KEY_WITH_COMMENT" | sed 's/^/  EXPECTED: /'
    echo ""
    print_status "What's in the file ($AUTH_KEYS):"
    cat -n "$AUTH_KEYS" | sed 's/^/  /'
    echo ""
    print_status "Searching for comment '$KEY_COMMENT' in file:"
    grep -n "$KEY_COMMENT" "$AUTH_KEYS" | sed 's/^/  FOUND: /' || echo "  NOT FOUND"
fi
echo -e "${BLUE}══════════════════════════════════════════════════${NC}"
echo ""

echo ""
print_success "SSH setup completed successfully!"
echo ""

# Configure passwordless sudo for the orchestrator
print_status "Configuring passwordless sudo for orchestrator operations..."
echo ""

# Check if user already has passwordless sudo
if sudo -n true 2>/dev/null; then
    print_success "User already has passwordless sudo configured"
    print_status "Testing with: sudo -n whoami"
    sudo -n whoami | sed 's/^/  Result: /'
else
    print_warning "Passwordless sudo is not configured - required for orchestrator operations"
    print_status "Configuring now (use SKIP_SUDO=1 to skip)..."
    
    # Check for SKIP_SUDO environment variable
    if [ "$SKIP_SUDO" == "1" ]; then
        print_warning "⚠️  Skipped passwordless sudo configuration (SKIP_SUDO=1)"
        print_status "To configure manually later:"
        echo -e "${GREEN}  echo \"$CURRENT_USER ALL=(ALL) NOPASSWD:ALL\" | sudo tee /etc/sudoers.d/orchestrator-$CURRENT_USER${NC}"
        echo -e "${GREEN}  sudo chmod 440 /etc/sudoers.d/orchestrator-$CURRENT_USER${NC}"
    else
        echo ""
        print_status "Creating passwordless sudo configuration..."
        SUDOERS_FILE="/etc/sudoers.d/orchestrator-$CURRENT_USER"
        SUDOERS_CONTENT="$CURRENT_USER ALL=(ALL) NOPASSWD:ALL"
        
        echo ""
        print_status "Writing to: $SUDOERS_FILE"
        print_status "Content: $SUDOERS_CONTENT"
        echo ""
        
        echo "$SUDOERS_CONTENT" | sudo tee $SUDOERS_FILE
        sudo chmod 440 $SUDOERS_FILE
        
        echo ""
        print_status "Verifying sudoers file..."
        echo -e "${BLUE}══════════════════════════════════════════════════${NC}"
        print_status "File: $SUDOERS_FILE"
        if [ -f "$SUDOERS_FILE" ]; then
            print_success "✓ File exists"
            print_status "Permissions: $(ls -l $SUDOERS_FILE | awk '{print $1}')"
            print_status "Owner: $(ls -l $SUDOERS_FILE | awk '{print $3\":\"$4}')"
            echo ""
            print_status "Contents:"
            sudo cat $SUDOERS_FILE | sed 's/^/  → /'
        else
            print_error "✗ File was not created!"
        fi
        echo -e "${BLUE}══════════════════════════════════════════════════${NC}"
        
        echo ""
        print_status "Validating sudoers syntax..."
        if sudo visudo -c -f $SUDOERS_FILE 2>&1 | grep -q "parsed OK"; then
            print_success "✓ Sudoers syntax is valid"
        else
            print_error "✗ Sudoers syntax validation failed"
            sudo visudo -c -f $SUDOERS_FILE 2>&1 | sed 's/^/  /'
        fi
        
        echo ""
        print_status "Testing passwordless sudo..."
        echo -e "${BLUE}──────────────────────────────────────${NC}"
        print_status "Test 1: sudo -n true"
        if sudo -n true 2>/dev/null; then
            print_success "  ✓ PASS"
        else
            print_error "  ✗ FAIL"
        fi
        
        print_status "Test 2: sudo -n whoami"
        SUDO_TEST=$(sudo -n whoami 2>&1)
        if [ "$SUDO_TEST" == "root" ]; then
            print_success "  ✓ PASS (result: $SUDO_TEST)"
        else
            print_error "  ✗ FAIL (result: $SUDO_TEST)"
        fi
        
        print_status "Test 3: sudo -n echo 'test'"
        if sudo -n echo "test" >/dev/null 2>&1; then
            print_success "  ✓ PASS"
        else
            print_error "  ✗ FAIL"
        fi
        echo -e "${BLUE}──────────────────────────────────────${NC}"
        
        echo ""
        if sudo -n true 2>/dev/null; then
            print_success "✅ Passwordless sudo configured successfully!"
        else
            print_error "❌ Passwordless sudo still not working"
            print_status "Manual configuration required:"
            echo -e "${YELLOW}  1. sudo visudo${NC}"
            echo -e "${YELLOW}  2. Add line: $CURRENT_USER ALL=(ALL) NOPASSWD:ALL${NC}"
            echo -e "${YELLOW}  3. Save and exit${NC}"
        fi
    fi
fi

echo ""

# Print summary
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✓ Setup Summary:${NC}"
echo -e "  • SSH directory: $SSH_DIR"
echo -e "  • Authorized keys: $AUTH_KEYS"
echo -e "  • Key comment: $KEY_COMMENT"
echo -e "  • Orchestrator IP: $ORCHESTRATOR_IP"
if sudo -n true 2>/dev/null; then
    echo -e "  • Passwordless sudo: ${GREEN}✓ Configured${NC}"
else
    echo -e "  • Passwordless sudo: ${YELLOW}⚠ Not configured${NC}"
fi
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo ""

print_status "The orchestrator can now connect to this node via SSH"
if ! sudo -n true 2>/dev/null; then
    print_warning "Note: Configure passwordless sudo for full orchestrator functionality"
fi
echo ""

# Optional: Test SSH connection back (if SSH server is running)
if command -v sshd &> /dev/null || systemctl is-active --quiet ssh || systemctl is-active --quiet sshd; then
    print_success "SSH server is running on this node"
else
    print_warning "SSH server might not be running on this node"
    print_status "Install SSH server with:"
    print_status "  • Debian/Ubuntu: sudo apt install openssh-server"
    print_status "  • Arch: sudo pacman -S openssh && sudo systemctl enable --now sshd"
fi

echo ""
print_status "Setup complete! 🎉"
echo ""

# Notify orchestrator that setup is complete (optional callback)
print_status "Notifying orchestrator that SSH setup is complete..."
if curl -sSf -X POST "http://${ORCHESTRATOR_IP}:5000/api/nodes/${NODE_ID}/ssh-setup-complete" \
    -H "Content-Type: application/json" \
    -d "{\"hostname\":\"$(hostname)\",\"setup_completed\":true}" \
    --max-time 5 2>/dev/null; then
    print_success "✅ Orchestrator notified - connection will be tested automatically"
else
    print_warning "Could not notify orchestrator (this is OK - you can test manually)"
    print_status "Go to the orchestrator web UI and click 'Check SSH Connection'"
fi

echo ""
print_status "All done! The orchestrator can now manage this node. 🎉"

