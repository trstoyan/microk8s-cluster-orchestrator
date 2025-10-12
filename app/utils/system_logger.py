"""
System Logger for Makefile and System Operations
Logs system-level actions (updates, restarts, etc.) to logs/system.log
"""

import logging
import os
from datetime import datetime
from pathlib import Path

# Create logs directory if it doesn't exist
PROJECT_ROOT = Path(__file__).parent.parent.parent
LOGS_DIR = PROJECT_ROOT / 'logs'
LOGS_DIR.mkdir(exist_ok=True)

# Configure system logger
system_logger = logging.getLogger('system_operations')
system_logger.setLevel(logging.INFO)

# File handler for system.log
system_log_file = LOGS_DIR / 'system.log'
file_handler = logging.FileHandler(system_log_file)
file_handler.setLevel(logging.INFO)

# Format: [timestamp] [LEVEL] [user] message
formatter = logging.Formatter(
    '[%(asctime)s] [%(levelname)s] [%(username)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
file_handler.setFormatter(formatter)
system_logger.addHandler(file_handler)

# Also log to console
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)
system_logger.addHandler(console_handler)


def log_system_action(action, details=None, level='INFO', user=None):
    """
    Log a system action to system.log
    
    Args:
        action: Description of the action (e.g., "Server restarted")
        details: Optional additional details
        level: Log level (INFO, WARNING, ERROR, SUCCESS)
        user: Username performing the action (auto-detected if None)
    """
    # Get username from Flask context if available
    if user is None:
        try:
            from flask_login import current_user
            if current_user.is_authenticated:
                user = current_user.username
            else:
                user = 'anonymous'
        except:
            import os
            user = os.environ.get('SUDO_USER', os.environ.get('USER', 'system'))
    
    # Create extra dict with username for formatter
    extra = {'username': user}
    
    # Combine action and details
    message = action
    if details:
        message = f"{action} - {details}"
    
    # Log based on level
    level_map = {
        'INFO': system_logger.info,
        'WARNING': system_logger.warning,
        'ERROR': system_logger.error,
        'SUCCESS': system_logger.info,  # Log SUCCESS as INFO level
        'DEBUG': system_logger.debug
    }
    
    log_func = level_map.get(level.upper(), system_logger.info)
    
    # Add emoji prefix based on level
    emoji_map = {
        'INFO': 'ℹ️',
        'SUCCESS': '✅',
        'WARNING': '⚠️',
        'ERROR': '❌',
        'DEBUG': '🔍'
    }
    emoji = emoji_map.get(level.upper(), '')
    
    log_func(f"{emoji} {message}", extra=extra)


def log_make_command(command, user=None):
    """Log a make command execution"""
    log_system_action(f"Makefile command: make {command}", level='INFO', user=user)


def log_server_start(method='background', pid=None, user=None):
    """Log server start"""
    details = f"method={method}"
    if pid:
        details += f", PID={pid}"
    log_system_action("Server started", details=details, level='SUCCESS', user=user)


def log_server_stop(method='background', pid=None, user=None):
    """Log server stop"""
    details = f"method={method}"
    if pid:
        details += f", PID={pid}"
    log_system_action("Server stopped", details=details, level='SUCCESS', user=user)


def log_server_restart(user=None):
    """Log server restart"""
    log_system_action("Server restarted", level='SUCCESS', user=user)


def log_update_start(branch=None, user=None):
    """Log update start"""
    details = f"branch={branch}" if branch else None
    log_system_action("Update started", details=details, level='INFO', user=user)


def log_update_complete(changed_files=0, user=None):
    """Log update completion"""
    details = f"changed_files={changed_files}"
    log_system_action("Update completed", details=details, level='SUCCESS', user=user)


def log_update_error(error, user=None):
    """Log update error"""
    log_system_action("Update failed", details=str(error), level='ERROR', user=user)

