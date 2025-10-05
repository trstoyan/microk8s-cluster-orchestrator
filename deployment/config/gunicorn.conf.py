"""
Gunicorn configuration file for MicroK8s Cluster Orchestrator.

This configuration is optimized for production deployment with proper
error handling, logging, and performance settings.
"""

import os
import multiprocessing
from pathlib import Path

# Server socket
bind = os.getenv('GUNICORN_BIND', '0.0.0.0:5000')
backlog = int(os.getenv('GUNICORN_BACKLOG', '2048'))

# Worker processes
workers = int(os.getenv('GUNICORN_WORKERS', multiprocessing.cpu_count() * 2 + 1))
worker_class = os.getenv('GUNICORN_WORKER_CLASS', 'sync')
worker_connections = int(os.getenv('GUNICORN_WORKER_CONNECTIONS', '1000'))
max_requests = int(os.getenv('GUNICORN_MAX_REQUESTS', '1000'))
max_requests_jitter = int(os.getenv('GUNICORN_MAX_REQUESTS_JITTER', '100'))

# Timeout settings
timeout = int(os.getenv('GUNICORN_TIMEOUT', '30'))
keepalive = int(os.getenv('GUNICORN_KEEPALIVE', '2'))

# Logging
accesslog = os.getenv('GUNICORN_ACCESS_LOG', '-')  # stdout
errorlog = os.getenv('GUNICORN_ERROR_LOG', '-')   # stderr
loglevel = os.getenv('GUNICORN_LOG_LEVEL', 'info')
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = os.getenv('GUNICORN_PROC_NAME', 'microk8s-orchestrator')

# Security
limit_request_line = int(os.getenv('GUNICORN_LIMIT_REQUEST_LINE', '4094'))
limit_request_fields = int(os.getenv('GUNICORN_LIMIT_REQUEST_FIELDS', '100'))
limit_request_field_size = int(os.getenv('GUNICORN_LIMIT_REQUEST_FIELD_SIZE', '8190'))

# Preload application for better performance
preload_app = os.getenv('GUNICORN_PRELOAD_APP', 'True').lower() == 'true'

# Worker lifecycle hooks
def when_ready(server):
    """Called just after the server is started."""
    server.log.info("MicroK8s Cluster Orchestrator server is ready. Workers: %s", server.cfg.workers)

def worker_int(worker):
    """Called just after a worker has been forked."""
    worker.log.info("Worker spawned (pid: %s)", worker.pid)

def pre_fork(server, worker):
    """Called just before a worker is forked."""
    server.log.info("Worker will be spawned")

def post_fork(server, worker):
    """Called just after a worker has been forked."""
    server.log.info("Worker spawned (pid: %s)", worker.pid)

def worker_abort(worker):
    """Called when a worker receives the SIGABRT signal."""
    worker.log.info("Worker received SIGABRT signal")

# SSL settings (if needed)
# keyfile = os.getenv('GUNICORN_KEYFILE')
# certfile = os.getenv('GUNICORN_CERTFILE')
