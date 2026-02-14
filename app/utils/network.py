"""
Network utilities for the MicroK8s Cluster Orchestrator.
"""

import socket
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def get_orchestrator_ip(config_ip: Optional[str] = None, fallback_ip: Optional[str] = None) -> str:
    """
    Get the orchestrator's IP address that nodes should use to connect.
    
    Priority order:
    1. Configured IP from config (if provided)
    2. Auto-detected IP from primary network interface
    3. Fallback IP (e.g., from request.host)
    4. 'localhost' as last resort
    
    Args:
        config_ip: IP address from configuration file
        fallback_ip: Fallback IP address (e.g., from request.host)
    
    Returns:
        str: The orchestrator IP address
    """
    # Priority 1: Use configured IP if provided
    if config_ip and config_ip.strip():
        logger.debug(f"Using configured orchestrator IP: {config_ip}")
        return config_ip.strip()
    
    # Priority 2: Try to auto-detect from network interface
    try:
        # Create a socket to determine the primary network interface
        # This doesn't actually connect, just determines routing
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            # Use Google's DNS server to determine the route
            # This doesn't send any data
            s.connect(('8.8.8.8', 80))
            detected_ip = s.getsockname()[0]
            s.close()
            
            # Verify it's not a loopback address
            if detected_ip and not detected_ip.startswith('127.'):
                logger.debug(f"Auto-detected orchestrator IP: {detected_ip}")
                return detected_ip
        except Exception:
            s.close()
            raise
    except Exception as e:
        logger.warning(f"Could not auto-detect IP address: {e}")
    
    # Priority 3: Use fallback IP if provided
    if fallback_ip and fallback_ip.strip():
        # Clean up the fallback IP (remove port if present)
        clean_ip = fallback_ip.split(':')[0].strip()
        if clean_ip and clean_ip not in ('localhost', '127.0.0.1', '0.0.0.0'):
            logger.debug(f"Using fallback orchestrator IP: {clean_ip}")
            return clean_ip
    
    # Priority 4: Last resort - return localhost
    logger.warning("Could not determine orchestrator IP, using localhost")
    return 'localhost'


def get_server_port(config_port: Optional[int] = None, fallback_port: int = 5000) -> int:
    """
    Get the server port.
    
    Args:
        config_port: Port from configuration
        fallback_port: Default port if not configured
    
    Returns:
        int: The server port
    """
    if config_port:
        return config_port
    return fallback_port

