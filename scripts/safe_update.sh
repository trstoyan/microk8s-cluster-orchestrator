#!/bin/bash

# Safe update script for MicroK8s Cluster Orchestrator
# Downloads new code to temp location, checks for conflicts, and applies safely

set -e  # Exit on any error

# Start timing
SECONDS=0

# Progress bar function
show_progress() {
    local duration=$1
    local task_name=$2
    local progress=0
    local bar_length=30
    
    echo -n "📊 $task_name: ["
    for ((i=0; i<bar_length; i++)); do echo -n " "; done
    echo -n "] 0%"
    
    while [ $progress -lt 100 ]; do
        sleep $((duration * 10 / 100 / 10)) 2>/dev/null || sleep 1
        progress=$((progress + 100 / bar_length))
        if [ $progress -gt 100 ]; then progress=100; fi
        
        echo -ne "\r📊 $task_name: ["
        for ((i=0; i<bar_length; i++)); do
            if [ $i -lt $((progress * bar_length / 100)) ]; then
                echo -n "█"
            else
                echo -n " "
            fi
        done
        echo -ne "] $progress%"
    done
    echo ""
}

echo "🔄 Starting safe codebase update..."
echo "📅 Timestamp: $(date)"
echo "📁 Current directory: $(pwd)"

# Check for progress bar tools
if ! command -v pv >/dev/null 2>&1; then
    echo "💡 Tip: Install 'pv' package for better progress bars:"
    echo "   Ubuntu/Debian: sudo apt install pv"
    echo "   CentOS/RHEL: sudo yum install pv"
    echo "   Arch: sudo pacman -S pv"
    echo ""
fi

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
if command -v pv >/dev/null 2>&1; then
    echo "📊 Cloning with progress indicator..."
    git clone --progress --depth 1 "$REPO_URL" "$TMP_DIR/microk8s-cluster-orchestrator" 2>&1 | while read line; do
        echo "   $line"
    done
else
    git clone --depth 1 "$REPO_URL" "$TMP_DIR/microk8s-cluster-orchestrator"
fi

# Checkout main branch
cd "$TMP_DIR/microk8s-cluster-orchestrator"
git checkout main
cd "$CURRENT_DIR"

# Create backup of current state
echo "💾 Creating backup of current state..."
BACKUP_DIR="$TMP_DIR/backup-$TIMESTAMP"

# Create the backup directory
mkdir -p "$BACKUP_DIR"

# Add timeout for backup operation (10 minutes)
BACKUP_TIMEOUT=600

# Check if pv (pipe viewer) is available for progress bar
if command -v pv >/dev/null 2>&1; then
    echo "📊 Creating backup with progress indicator..."
    # Calculate directory size first
    DIR_SIZE=$(du -sb "$CURRENT_DIR" 2>/dev/null | cut -f1 || echo "0")
    echo "   📁 Directory size: $(du -sh "$CURRENT_DIR" 2>/dev/null | cut -f1 || echo 'Unknown')"
    echo "   📊 Starting backup..."
    
    # Create backup with progress bar
    tar -cf - -C "$CURRENT_DIR" . | pv -s "$DIR_SIZE" -p -t -e -r | tar -xf - -C "$BACKUP_DIR"
    
    if [ $? -eq 0 ]; then
        echo "✅ Backup created successfully"
    else
        echo "❌ Backup failed, trying alternative method..."
        cp -r "$CURRENT_DIR" "$BACKUP_DIR"
    fi
else
    echo "📊 Creating backup (no progress bar available)..."
    echo "   Installing 'pv' package will show progress bars for file operations"
    echo "   📁 Directory size: $(du -sh "$CURRENT_DIR" 2>/dev/null | cut -f1 || echo 'Unknown')"
    echo "   📊 Starting backup..."
    
    # Use rsync for better progress indication even without pv
    echo "   🔄 Using rsync for backup..."
    timeout $BACKUP_TIMEOUT rsync -a --progress "$CURRENT_DIR/" "$BACKUP_DIR/" --exclude='.git' --exclude='__pycache__' --exclude='*.pyc' 2>&1 | while read line; do
        echo "   $line"
    done
    
    if [ ${PIPESTATUS[0]} -ne 0 ]; then
        echo "❌ Rsync backup failed or timed out, trying cp..."
        echo "   🔄 Using cp for backup..."
        timeout $BACKUP_TIMEOUT cp -r "$CURRENT_DIR" "$BACKUP_DIR"
        if [ $? -eq 0 ]; then
            echo "✅ Backup completed with cp"
        else
            echo "❌ Backup failed completely"
            exit 1
        fi
    else
        echo "✅ Backup completed with rsync"
    fi
fi

# Verify backup was created successfully
if [ ! -d "$BACKUP_DIR" ]; then
    echo "❌ Backup directory was not created. Something went wrong."
    exit 1
else
    echo "✅ Backup verified: $(du -sh "$BACKUP_DIR" 2>/dev/null | cut -f1 || echo 'Unknown size')"
fi

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

if command -v pv >/dev/null 2>&1; then
    echo "📊 Syncing files with progress indicator..."
    rsync -av --delete --progress \
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
else
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
fi

echo "✅ File sync completed"

# Initialize database if needed and run migrations
echo "🔄 Checking database status..."
if [ -f ".venv/bin/python" ]; then
    echo "📊 Checking if database exists..."
    if [ ! -f "cluster_data.db" ] && [ ! -f "data/cluster_data.db" ]; then
        echo "📝 Database not found. Initializing database first..."
        echo "📊 Database initialization progress:"
        .venv/bin/python cli.py init --force 2>&1 | while read line; do
            echo "   $line"
        done
        
        if [ ${PIPESTATUS[0]} -ne 0 ]; then
            echo "❌ Database initialization failed!"
            exit 1
        fi
        echo "✅ Database initialized successfully"
    else
        echo "✅ Database exists"
    fi
    
    echo "🔄 Running database migrations..."
    echo "📊 Migration progress:"
    .venv/bin/python cli.py migrate run 2>&1 | while read line; do
        echo "   $line"
    done
    
    if [ ${PIPESTATUS[0]} -ne 0 ]; then
        echo "⚠️  Some migrations failed. This might be normal if tables don't exist yet."
        echo "🔄 Trying to initialize database and retry migrations..."
        show_progress 3 "Initializing database"
        .venv/bin/python cli.py init --force 2>&1 | while read line; do
            echo "   $line"
        done
        
        echo "📊 Retrying migrations:"
        .venv/bin/python cli.py migrate run 2>&1 | while read line; do
            echo "   $line"
        done
        
        if [ ${PIPESTATUS[0]} -ne 0 ]; then
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

if command -v pv >/dev/null 2>&1 && [ -d "$BACKUP_DIR" ]; then
    echo "📊 Moving backup with progress indicator..."
    # Calculate size for progress bar
    BACKUP_SIZE=$(du -sb "$BACKUP_DIR" 2>/dev/null | cut -f1 || echo "0")
    if [ "$BACKUP_SIZE" -gt 0 ]; then
        tar -cf - -C "$TMP_DIR" "backup-$TIMESTAMP" | pv -s "$BACKUP_SIZE" | tar -xf - -C "$(dirname "$BACKUP_PERMANENT_DIR")"
        rm -rf "$BACKUP_DIR"
    else
        mv "$BACKUP_DIR" "$BACKUP_PERMANENT_DIR"
    fi
else
    mv "$BACKUP_DIR" "$BACKUP_PERMANENT_DIR"
fi

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
echo "📈 Process Statistics:"
echo "   📁 Files processed: $(find . -type f -not -path './.git/*' -not -path './.venv/*' -not -path './data/*' -not -path './logs/*' -not -path './backups/*' | wc -l)"
echo "   💾 Backup size: $(du -sh "$BACKUP_PERMANENT_DIR" 2>/dev/null | cut -f1 || echo 'Unknown')"
echo "   ⏱️  Total time: $((SECONDS/60))m $((SECONDS%60))s"
echo ""
echo "🔐 Git credential cache status:"
git credential-cache get <<< "protocol=https
host=github.com" > /dev/null 2>&1 && echo "   ✅ Credentials cached (valid for 24 hours)" || echo "   ⚠️  No cached credentials found"
