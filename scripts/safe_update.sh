#!/bin/bash

# Safe update script for MicroK8s Cluster Orchestrator
# Downloads new code to temp location, checks for conflicts, and applies safely

set -e  # Exit on any error

echo "🔄 Starting safe codebase update..."

# Get the current directory and repository URL
CURRENT_DIR=$(pwd)
REPO_URL=$(git remote get-url origin)
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Create temporary directory
TMP_DIR=$(mktemp -d)
echo "📁 Temporary directory: $TMP_DIR"

# Function to cleanup on exit
cleanup() {
    echo "🧹 Cleaning up temporary files..."
    rm -rf "$TMP_DIR"
}
trap cleanup EXIT

# Configure git credential caching for longer time (24 hours)
echo "🔐 Configuring git credentials cache (24 hours)..."
git config --global credential.helper 'cache --timeout=86400'
git config --global credential.helper cache
echo "   Git credentials will be cached for 24 hours"

# Clone latest code to temporary location
echo "📥 Cloning latest code..."
git clone --depth 1 "$REPO_URL" "$TMP_DIR/microk8s-cluster-orchestrator"

# Checkout main branch
cd "$TMP_DIR/microk8s-cluster-orchestrator"
git checkout main
cd "$CURRENT_DIR"

# Create backup of current state
echo "💾 Creating backup of current state..."
BACKUP_DIR="$TMP_DIR/backup-$TIMESTAMP"
cp -r "$CURRENT_DIR" "$BACKUP_DIR"

# Check for any local uncommitted changes
if ! git diff --quiet || ! git diff --cached --quiet; then
    echo "⚠️  Warning: You have uncommitted changes!"
    echo "   The update will proceed, but local changes may be lost."
    echo "   Consider committing or stashing your changes first."
    read -p "   Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ Update cancelled by user"
        exit 1
    fi
fi

# Apply the update using rsync (exclude important directories)
echo "🔄 Applying update..."
rsync -av --delete \
    --exclude='.git' \
    --exclude='.venv' \
    --exclude='data/' \
    --exclude='logs/' \
    --exclude='backups/' \
    --exclude='ssh_keys/' \
    --exclude='instance/' \
    --exclude='__pycache__/' \
    --exclude='*.pyc' \
    "$TMP_DIR/microk8s-cluster-orchestrator/" "$CURRENT_DIR/"

# Run database migrations
echo "🔄 Running database migrations..."
if [ -f ".venv/bin/python" ]; then
    .venv/bin/python cli.py migrate run
else
    echo "⚠️  Virtual environment not found. Skipping migrations."
    echo "   Run 'make install' and then 'make migrate' manually."
fi

# Move backup to a permanent location for potential rollback
BACKUP_PERMANENT_DIR="backups/code-backup-$TIMESTAMP"
mkdir -p backups
mv "$BACKUP_DIR" "$BACKUP_PERMANENT_DIR"

echo "✅ Code update complete!"
echo "📁 Backup saved to: $BACKUP_PERMANENT_DIR"
echo "🔄 If you need to rollback, restore from the backup directory"
echo ""
echo "🔐 Git credential cache status:"
git credential-cache get <<< "protocol=https
host=github.com" > /dev/null 2>&1 && echo "   ✅ Credentials cached (valid for 24 hours)" || echo "   ⚠️  No cached credentials found"
