#!/bin/bash
# System Logger for Makefile Operations
# Logs all system operations (updates, restarts, etc.) to system.log

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_FILE="$PROJECT_ROOT/logs/system.log"

# Ensure logs directory exists
mkdir -p "$PROJECT_ROOT/logs"

# Function to log with timestamp and level
log_system() {
    local level="$1"
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    local user="${SUDO_USER:-$USER}"
    
    # Color codes for terminal output
    local RED='\033[0;31m'
    local GREEN='\033[0;32m'
    local YELLOW='\033[1;33m'
    local BLUE='\033[0;34m'
    local NC='\033[0m' # No Color
    
    # Format log entry
    local log_entry="[$timestamp] [$level] [$user] $message"
    
    # Append to log file
    echo "$log_entry" >> "$LOG_FILE"
    
    # Also output to console with color
    case "$level" in
        INFO)
            echo -e "${BLUE}ℹ ${NC}$message" >&2
            ;;
        SUCCESS)
            echo -e "${GREEN}✅${NC} $message" >&2
            ;;
        WARNING)
            echo -e "${YELLOW}⚠️ ${NC} $message" >&2
            ;;
        ERROR)
            echo -e "${RED}❌${NC} $message" >&2
            ;;
        COMMAND)
            echo -e "${BLUE}🔧${NC} $message" >&2
            ;;
        *)
            echo "$message" >&2
            ;;
    esac
}

# Export function for use in other scripts
export -f log_system
export LOG_FILE
export PROJECT_ROOT

# If called directly, log the arguments
if [ "${BASH_SOURCE[0]}" = "$0" ]; then
    if [ $# -lt 2 ]; then
        echo "Usage: $0 <LEVEL> <MESSAGE>"
        echo "Levels: INFO, SUCCESS, WARNING, ERROR, COMMAND"
        exit 1
    fi
    
    log_system "$@"
fi

