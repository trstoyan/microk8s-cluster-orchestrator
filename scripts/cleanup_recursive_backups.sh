#!/bin/bash
# Script to clean up recursive backup mess
# Safely removes old backups, keeping only the most recent one

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

echo "╔════════════════════════════════════════════════════════════╗"
echo "║     🧹 Recursive Backup Cleanup Tool                      ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "This script will clean up the recursive backup mess."
echo ""

# Check if backups directory exists
if [ ! -d "backups" ]; then
    echo "✅ No backups directory found - nothing to clean!"
    exit 0
fi

# Show current backup situation
echo "📊 Current backup status:"
echo "   Directory: $PROJECT_DIR/backups"
BACKUP_SIZE=$(du -sh backups/ 2>/dev/null | cut -f1 || echo "Unknown")
BACKUP_COUNT=$(find backups/ -maxdepth 1 -type d -name "backup-*" 2>/dev/null | wc -l)
echo "   Total size: $BACKUP_SIZE"
echo "   Backup count: $BACKUP_COUNT"
echo ""

if [ "$BACKUP_COUNT" -eq 0 ]; then
    echo "✅ No backup folders found - nothing to clean!"
    exit 0
fi

# Show list of backups
echo "📋 Found backups:"
find backups/ -maxdepth 1 -type d -name "backup-*" -printf '%TY-%Tm-%Td %TH:%TM  %f\n' 2>/dev/null | sort -r | head -10
if [ "$BACKUP_COUNT" -gt 10 ]; then
    echo "   ... and $(($BACKUP_COUNT - 10)) more"
fi
echo ""

# Ask for confirmation
echo "⚠️  This will:"
echo "   1. Keep ONLY the most recent backup"
echo "   2. Delete all other old backups"
echo "   3. Free up significant disk space"
echo ""
read -p "   Continue? [y/N]: " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Cleanup cancelled"
    exit 0
fi

echo ""
echo "🧹 Starting cleanup..."

# Find and delete all but the most recent backup
DELETED_COUNT=0
find backups/ -maxdepth 1 -type d -name "backup-*" -printf '%T@ %p\n' 2>/dev/null | \
    sort -n | head -n -1 | cut -d' ' -f2- | while read old_backup; do
    echo "   🗑️  Removing: $(basename "$old_backup")"
    rm -rf "$old_backup"
    DELETED_COUNT=$((DELETED_COUNT + 1))
done

echo ""
echo "✅ Cleanup complete!"
echo ""
echo "📊 New backup status:"
NEW_SIZE=$(du -sh backups/ 2>/dev/null | cut -f1 || echo "Unknown")
NEW_COUNT=$(find backups/ -maxdepth 1 -type d -name "backup-*" 2>/dev/null | wc -l)
echo "   Total size: $NEW_SIZE (was: $BACKUP_SIZE)"
echo "   Backup count: $NEW_COUNT (was: $BACKUP_COUNT)"
echo ""
echo "💽 Disk space freed:"
df -h "$PROJECT_DIR" | tail -1 | awk '{print "   Available: " $4 " (" $5 " used)"}'
echo ""
echo "✅ Done! Future updates will:"
echo "   • Not include old backups in new backups"
echo "   • Auto-cleanup old backups (keep last 5)"
echo "   • Check disk space before backup"

