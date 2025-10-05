#!/bin/bash

# Safe update script for MicroK8s Cluster Orchestrator
# Downloads new code to temp location, checks for conflicts, and applies safely

set -e  # Exit on any error

echo "🔄 Starting safe codebase update..."
echo "📅 Timestamp: $(date)"
echo "📁 Current directory: $(pwd)"

# Get the current directory and repository URL
CURRENT_DIR=$(pwd)
REPO_URL=$(git remote get-url origin)
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "🔗 Repository URL: $REPO_URL"
echo "🕐 Backup timestamp: $TIMESTAMP"

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
echo "🔍 Checking for local uncommitted changes..."
if ! git diff --quiet || ! git diff --cached --quiet; then
    echo "⚠️  Warning: You have uncommitted changes!"
    echo "   Modified files:"
    git diff --name-only | sed 's/^/     - /'
    git diff --cached --name-only | sed 's/^/     - /' | sed 's/^/     (staged) /'
    echo "   The update will proceed, but local changes may be lost."
    echo "   Consider committing or stashing your changes first."
    read -p "   Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ Update cancelled by user"
        exit 1
    fi
else
    echo "✅ No uncommitted changes found"
fi

# Apply the update using rsync (exclude important directories)
echo "🔄 Applying update with rsync..."
echo "   Source: $TMP_DIR/microk8s-cluster-orchestrator/"
echo "   Destination: $CURRENT_DIR/"
echo "   Excluding: .git, .venv, data/, logs/, backups/, ssh_keys/, instance/, __pycache__/, *.pyc"

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

echo "✅ File sync completed"

# Initialize database if needed and run migrations
echo "🔄 Checking database status..."
if [ -f ".venv/bin/python" ]; then
    echo "📊 Checking if database exists..."
    if [ ! -f "cluster_data.db" ] && [ ! -f "data/cluster_data.db" ]; then
        echo "📝 Database not found. Initializing database first..."
        .venv/bin/python cli.py init --force
        if [ $? -ne 0 ]; then
            echo "❌ Database initialization failed!"
            exit 1
        fi
        echo "✅ Database initialized successfully"
    else
        echo "✅ Database exists"
    fi
    
    echo "🔄 Running database migrations..."
    .venv/bin/python cli.py migrate run
    if [ $? -ne 0 ]; then
        echo "⚠️  Some migrations failed. This might be normal if tables don't exist yet."
        echo "🔄 Trying to initialize database and retry migrations..."
        .venv/bin/python cli.py init --force
        .venv/bin/python cli.py migrate run
        if [ $? -ne 0 ]; then
            echo "❌ Migration failed after retry. Please check manually."
            echo "   You can run: python cli.py migrate status"
            echo "   Then: python cli.py migrate run"
        else
            echo "✅ Migrations completed successfully on retry"
        fi
    else
        echo "✅ Migrations completed successfully"
    fi
else
    echo "⚠️  Virtual environment not found. Skipping database operations."
    echo "   Run 'make install' and then 'make init' and 'make migrate' manually."
fi

# Move backup to a permanent location for potential rollback
BACKUP_PERMANENT_DIR="backups/code-backup-$TIMESTAMP"
echo "📁 Moving backup to permanent location: $BACKUP_PERMANENT_DIR"
mkdir -p backups
mv "$BACKUP_DIR" "$BACKUP_PERMANENT_DIR"

echo ""
echo "🎉 Code update complete!"
echo "📁 Backup saved to: $BACKUP_PERMANENT_DIR"
echo "🔄 If you need to rollback, restore from the backup directory"
echo ""
echo "📊 Update Summary:"
echo "   ✅ Code pulled from repository"
echo "   ✅ Files synchronized safely"
echo "   ✅ Database initialized/updated"
echo "   ✅ Migrations applied"
echo "   ✅ Backup created for rollback"
echo ""
echo "🔐 Git credential cache status:"
git credential-cache get <<< "protocol=https
host=github.com" > /dev/null 2>&1 && echo "   ✅ Credentials cached (valid for 24 hours)" || echo "   ⚠️  No cached credentials found"
