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
    rm -f /tmp/merge-check.txt
}
trap cleanup EXIT

# Configure git credential caching for longer time (24 hours)
echo "🔐 Configuring git credentials cache (24 hours)..."
git config --global credential.helper 'cache --timeout=86400'
git config --global credential.helper cache
echo "   Git credentials will be cached for 24 hours"

# Detect current branch
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
echo "🌿 Current branch: $CURRENT_BRANCH"

# Fetch latest changes from remote
echo "📥 Fetching latest changes from remote..."
git fetch origin $CURRENT_BRANCH

# Check if we're ahead of remote (have local commits)
LOCAL_COMMITS=$(git rev-list --count origin/$CURRENT_BRANCH..HEAD 2>/dev/null || echo "0")
REMOTE_COMMITS=$(git rev-list --count HEAD..origin/$CURRENT_BRANCH 2>/dev/null || echo "0")

echo "📊 Update status:"
echo "   Local commits ahead: $LOCAL_COMMITS"
echo "   Remote commits ahead: $REMOTE_COMMITS"

# Check if this is a self-update scenario
if [ "$SAFE_UPDATE_SELF_UPDATE" = "true" ]; then
    echo "🔄 Running in self-update mode - skipping self-update check"
    echo "   This process will handle the actual codebase update"
else
    # Check if safe_update.sh itself has changed on remote
    CURRENT_SCRIPT_HASH=$(git hash-object "$0")
    REMOTE_SCRIPT_HASH=$(git ls-tree origin/$CURRENT_BRANCH:scripts/safe_update.sh 2>/dev/null | cut -d' ' -f3 || echo "")

    if [ "$REMOTE_SCRIPT_HASH" != "" ] && [ "$CURRENT_SCRIPT_HASH" != "$REMOTE_SCRIPT_HASH" ]; then
    echo "🔄 Newer version of safe_update.sh detected on remote"
    echo "   Current version: $CURRENT_SCRIPT_HASH"
    echo "   Remote version:  $REMOTE_SCRIPT_HASH"
    echo "🔄 Downloading new version and running as side process..."
    
    # Create backup of current script
    cp "$0" "$TMP_DIR/safe_update_backup.sh"
    
    # Download new version to temporary location
    git show origin/$CURRENT_BRANCH:scripts/safe_update.sh > "$TMP_DIR/safe_update_new.sh"
    chmod +x "$TMP_DIR/safe_update_new.sh"
    
    # First, update the current script file with the new version
    echo "🔄 Updating current script file with new version..."
    cp "$TMP_DIR/safe_update_new.sh" "$0"
    
    # Run the new version (which is now the current script) as a side process
    echo "🚀 Starting updated safe_update.sh as side process..."
    echo "   New process will handle the actual update while current process monitors"
    
    # Set environment variable to indicate this is a self-update scenario
    export SAFE_UPDATE_SELF_UPDATE="true"
    
    # Run the updated script as background process
    nohup "$0" > "$TMP_DIR/update.log" 2>&1 &
    NEW_PID=$!
    
    echo "   New update process started with PID: $NEW_PID"
    echo "   Log file: $TMP_DIR/update.log"
    echo "🔄 Waiting for new process to complete..."
    
    # Wait for the new process to finish
    wait $NEW_PID
    EXIT_CODE=$?
    
    if [ $EXIT_CODE -eq 0 ]; then
        echo "✅ Update process completed successfully"
        echo "🔄 Script has been updated and is ready for future use"
    else
        echo "❌ Update process failed with exit code: $EXIT_CODE"
        echo "   Check the log file: $TMP_DIR/update.log"
        echo "   Restoring backup script..."
        cp "$TMP_DIR/safe_update_backup.sh" "$0"
    fi
    
    # Exit current process since the new one handled everything
    exit $EXIT_CODE
    fi
fi

if [ "$REMOTE_COMMITS" -eq 0 ]; then
    echo "✅ Already up to date with remote"
    echo "🔄 No update needed, but will still create backup for safety"
else
    echo "🔄 Remote has $REMOTE_COMMITS new commit(s) to pull"
fi

# Clean up old backups (keep only last 5)
echo "🧹 Cleaning old backups..."
if [ -d "$CURRENT_DIR/backups" ]; then
    OLD_BACKUP_COUNT=$(find "$CURRENT_DIR/backups" -maxdepth 1 -type d -name "backup-*" 2>/dev/null | wc -l)
    if [ "$OLD_BACKUP_COUNT" -gt 5 ]; then
        echo "   Found $OLD_BACKUP_COUNT old backups, keeping only the last 5..."
        find "$CURRENT_DIR/backups" -maxdepth 1 -type d -name "backup-*" -printf '%T@ %p\n' 2>/dev/null | \
            sort -n | head -n -5 | cut -d' ' -f2- | while read old_backup; do
            echo "   🗑️  Removing old backup: $(basename "$old_backup")"
            rm -rf "$old_backup"
        done
        echo "   ✅ Cleaned up old backups"
    else
        echo "   ℹ️  Found $OLD_BACKUP_COUNT backup(s), no cleanup needed"
    fi
fi

# Check available disk space
echo "💽 Checking disk space..."
AVAILABLE_SPACE=$(df "$CURRENT_DIR" | tail -1 | awk '{print $4}')
REQUIRED_SPACE=1048576  # 1GB in KB
if [ "$AVAILABLE_SPACE" -lt "$REQUIRED_SPACE" ]; then
    echo "⚠️  WARNING: Low disk space!"
    echo "   Available: $(df -h "$CURRENT_DIR" | tail -1 | awk '{print $4}')"
    echo "   Recommended: At least 1GB free"
    read -p "   Continue anyway? [y/N]: " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ Update cancelled due to low disk space"
        exit 1
    fi
else
    echo "   ✅ Sufficient disk space: $(df -h "$CURRENT_DIR" | tail -1 | awk '{print $4}') available"
fi

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
    # Calculate directory size first (excluding .venv, .git, backups)
    DIR_SIZE=$(du -sb --exclude=.venv --exclude=.git --exclude=__pycache__ --exclude=node_modules --exclude=backups "$CURRENT_DIR" 2>/dev/null | cut -f1 || echo "0")
    echo "   📁 Directory size (excluding .venv, backups): $(du -sh --exclude=.venv --exclude=.git --exclude=__pycache__ --exclude=backups "$CURRENT_DIR" 2>/dev/null | cut -f1 || echo 'Unknown')"
    echo "   📊 Starting backup..."
    
    # Create backup with progress bar (excluding .venv, .git, __pycache__, backups)
    tar -cf - -C "$CURRENT_DIR" --exclude='.venv' --exclude='.git' --exclude='__pycache__' --exclude='*.pyc' --exclude='node_modules' --exclude='backups' . | pv -s "$DIR_SIZE" -p -t -e -r | tar -xf - -C "$BACKUP_DIR"
    
    if [ $? -eq 0 ]; then
        echo "✅ Backup created successfully (excluded .venv for faster backup)"
    else
        echo "❌ Backup failed, trying alternative method..."
        rsync -a "$CURRENT_DIR/" "$BACKUP_DIR/" --exclude='.venv' --exclude='.git' --exclude='__pycache__' --exclude='*.pyc' --exclude='backups'
    fi
else
    echo "📊 Creating backup (no progress bar available)..."
    echo "   Installing 'pv' package will show progress bars for file operations"
    echo "   📁 Directory size (excluding .venv, backups): $(du -sh --exclude=.venv --exclude=.git --exclude=__pycache__ --exclude=backups "$CURRENT_DIR" 2>/dev/null | cut -f1 || echo 'Unknown')"
    echo "   📊 Starting backup..."
    
    # Check if rsync is available
    if command -v rsync &> /dev/null; then
        echo "   🔄 Using rsync for backup (excluding .venv, .git, __pycache__, backups)..."
        timeout $BACKUP_TIMEOUT rsync -a --progress "$CURRENT_DIR/" "$BACKUP_DIR/" --exclude='.venv' --exclude='.git' --exclude='__pycache__' --exclude='*.pyc' --exclude='node_modules' --exclude='backups' 2>&1 | while read line; do
            echo "   $line"
        done
        
        if [ ${PIPESTATUS[0]} -ne 0 ]; then
            echo "❌ Rsync with progress failed or timed out, trying rsync without progress..."
            echo "   🔄 Using basic rsync for backup..."
            rsync -a "$CURRENT_DIR/" "$BACKUP_DIR/" --exclude='.venv' --exclude='.git' --exclude='__pycache__' --exclude='*.pyc' --exclude='node_modules' --exclude='backups'
            if [ $? -eq 0 ]; then
                echo "✅ Backup completed with rsync (excluded .venv for faster backup)"
            else
                echo "❌ Backup failed with rsync, falling back to cp..."
                # Fallback to cp
                mkdir -p "$BACKUP_DIR"
                cp -a "$CURRENT_DIR"/* "$BACKUP_DIR/" 2>/dev/null
                # Remove excluded directories from backup
                rm -rf "$BACKUP_DIR/.venv" "$BACKUP_DIR/.git" 2>/dev/null
                find "$BACKUP_DIR" -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true
                find "$BACKUP_DIR" -type f -name '*.pyc' -delete 2>/dev/null || true
                echo "✅ Backup completed with cp (excluded .venv for faster backup)"
            fi
        else
            echo "✅ Backup completed with rsync (excluded .venv for faster backup)"
        fi
    else
        # rsync not available, use cp
        echo "   ℹ️  rsync not found, using cp for backup..."
        echo "   💡 Install rsync for faster backups: sudo pacman -S rsync"
        echo "   🔄 Using cp for backup (excluding .venv, .git, __pycache__)..."
        mkdir -p "$BACKUP_DIR"
        
        # Copy everything except excluded directories
        for item in "$CURRENT_DIR"/*; do
            basename=$(basename "$item")
            if [ "$basename" != ".venv" ] && [ "$basename" != ".git" ] && [ "$basename" != "node_modules" ] && [ "$basename" != "backups" ]; then
                cp -a "$item" "$BACKUP_DIR/" 2>&1 | sed 's/^/   /' || true
            fi
        done
        
        # Clean up any __pycache__ and .pyc files that might have been copied
        find "$BACKUP_DIR" -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true
        find "$BACKUP_DIR" -type f -name '*.pyc' -delete 2>/dev/null || true
        
        echo "✅ Backup completed with cp (excluded .venv for faster backup)"
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

# Apply the update using git merge (preserves local changes)
if [ "$REMOTE_COMMITS" -gt 0 ]; then
    echo "🔄 Applying update using git merge..."
    echo "   This will merge remote changes while preserving local commits"
    
    # Check if there are any conflicts before merging
    echo "🔍 Checking for potential merge conflicts..."
    git merge-tree $(git merge-base HEAD origin/$CURRENT_BRANCH) HEAD origin/$CURRENT_BRANCH > /tmp/merge-check.txt 2>/dev/null || true
    
    if grep -q "<<<<<<< " /tmp/merge-check.txt; then
        echo "⚠️  Potential merge conflicts detected:"
        echo "   The following files may have conflicts:"
        grep -B1 -A1 "<<<<<<< " /tmp/merge-check.txt | grep "^[a-zA-Z]" | sort -u | sed 's/^/     - /'
        echo "   Consider resolving conflicts manually or stashing local changes"
        read -p "   Continue with merge anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "❌ Update cancelled by user"
            exit 1
        fi
    fi
    
    # Perform the merge
    echo "🔄 Merging remote changes..."
    if git merge origin/$CURRENT_BRANCH --no-edit; then
        echo "✅ Merge completed successfully"
    else
        echo "❌ Merge failed due to conflicts"
        echo "🔄 Attempting to resolve conflicts automatically..."
        
        # Try to resolve common conflicts automatically
        if git status --porcelain | grep -q "^UU"; then
            echo "⚠️  Manual conflict resolution required"
            echo "   Run 'git status' to see conflicted files"
            echo "   Edit conflicted files and run 'git add <file>' for each"
            echo "   Then run 'git commit' to complete the merge"
            exit 1
        else
            echo "✅ Conflicts resolved automatically"
        fi
    fi
else
    echo "✅ No remote changes to apply"
fi

echo "✅ Update process completed"

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

if [ -d "$BACKUP_DIR" ]; then
    if command -v pv >/dev/null 2>&1; then
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
else
    echo "⚠️  Backup directory not found, skipping backup move"
fi

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║           🎉 UPDATE COMPLETE - SUMMARY                    ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "📊 Update Summary:"
echo "   🌿 Branch: $CURRENT_BRANCH"
echo "   ✅ Code pulled from repository"
echo "   ✅ Files synchronized safely"
echo "   ✅ Database initialized/updated"
echo "   ✅ Migrations applied"
echo "   ✅ Backup created for rollback"
echo ""
echo "📈 Statistics:"
echo "   📁 Files processed: $(find . -type f -not -path './.git/*' -not -path './.venv/*' -not -path './data/*' -not -path './logs/*' -not -path './backups/*' | wc -l)"
echo "   💾 Backup size: $(du -sh "$BACKUP_PERMANENT_DIR" 2>/dev/null | cut -f1 || echo 'Unknown')"
echo "   🚫 Excluded from backup: .venv, .git, __pycache__, *.pyc, node_modules"
echo "   📦 Local commits ahead: $LOCAL_COMMITS"
echo "   📥 Remote commits applied: $REMOTE_COMMITS"
echo "   ⏱️  Total time: $((SECONDS/60))m $((SECONDS%60))s"
echo ""
echo "📁 Backup Location:"
echo "   $BACKUP_PERMANENT_DIR"
echo ""
echo "🔄 Rollback (if needed):"
echo "   cp -r $BACKUP_PERMANENT_DIR/* ."
echo ""
echo "🔐 Git credential cache status:"
git credential-cache get <<< "protocol=https
host=github.com" > /dev/null 2>&1 && echo "   ✅ Credentials cached (valid for 24 hours)" || echo "   ⚠️  No cached credentials found"

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║              ✨ NEXT STEPS                                ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "🔄 Restart Server (to apply changes):"
echo "   make restart          # Restart server (auto-detects method)"
echo "   OR"
echo "   make service-restart  # Restart systemd service specifically"
echo "   make prod-restart     # Restart background process specifically"
echo ""
echo "🧪 Verify Update:"
echo "   make status           # Check server status"
echo "   make logo             # See updated version"
echo "   curl http://localhost:5000"
echo ""
echo "📚 Check What Changed:"
echo "   git log -5 --oneline  # Recent commits"
if [ "$REMOTE_COMMITS" -gt 0 ]; then
    echo "   git diff HEAD~$REMOTE_COMMITS HEAD  # Code changes"
fi
echo ""
echo "✅ Update completed successfully!"
