#!/bin/bash

# Safe update script for Raspberry Pi
# This script safely updates the code while preserving local changes

set -e

echo "🔄 Updating MicroK8s Cluster Orchestrator..."

# Navigate to project directory
cd "$(dirname "$0")/.."

# Check if there are local changes
if ! git diff --quiet || ! git diff --cached --quiet; then
    echo "⚠️  Local changes detected!"
    echo "📋 Current changes:"
    git status --porcelain
    
    echo ""
    echo "Choose an option:"
    echo "1) Stash changes and update (recommended)"
    echo "2) Commit changes and merge"
    echo "3) Discard changes and update (DANGEROUS)"
    echo "4) Cancel update"
    
    read -p "Enter your choice (1-4): " choice
    
    case $choice in
        1)
            echo "💾 Stashing local changes..."
            git stash push -m "Auto-stash before update $(date)"
            STASHED=true
            ;;
        2)
            echo "📝 Committing local changes..."
            git add .
            git commit -m "Local Pi changes before update $(date)"
            ;;
        3)
            echo "🗑️  Discarding local changes..."
            git reset --hard HEAD
            ;;
        4)
            echo "❌ Update cancelled"
            exit 0
            ;;
        *)
            echo "❌ Invalid choice, cancelling update"
            exit 1
            ;;
    esac
fi

# Fetch and pull latest changes
echo "📥 Fetching latest changes..."
git fetch origin

echo "📥 Pulling latest changes..."
if git pull origin main; then
    echo "✅ Update successful!"
    
    # If we stashed changes, try to reapply them
    if [[ "$STASHED" == "true" ]]; then
        echo "🔄 Attempting to reapply stashed changes..."
        if git stash pop; then
            echo "✅ Stashed changes reapplied successfully"
        else
            echo "⚠️  Could not reapply stashed changes automatically"
            echo "💡 You can manually resolve conflicts and run: git stash drop"
        fi
    fi
else
    echo "❌ Update failed due to conflicts"
    echo "💡 You may need to resolve conflicts manually"
    exit 1
fi

echo "🚀 Update complete! You can now run: ./scripts/setup_system.sh"
