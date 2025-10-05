#!/usr/bin/env python3
"""
WSGI entry point for the MicroK8s Cluster Orchestrator.

This file provides the WSGI application instance for production deployment
using Gunicorn or other WSGI servers.
"""

import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from app import create_app

# Create the WSGI application
application = create_app()

if __name__ == "__main__":
    # This allows running the WSGI module directly for testing
    # In production, this should be run via Gunicorn
    import argparse
    
    parser = argparse.ArgumentParser(description='MicroK8s Cluster Orchestrator WSGI Server')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=5000, help='Port to bind to')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    args = parser.parse_args()
    
    print(f"Starting WSGI server on {args.host}:{args.port}")
    print("WARNING: This is for development/testing only. Use Gunicorn for production!")
    
    application.run(
        host=args.host,
        port=args.port,
        debug=args.debug
    )
