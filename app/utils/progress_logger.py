"""
Progress Logger for Live Sync Operations
Captures and streams logs in real-time
"""

import logging
import queue
import time
from datetime import datetime
from threading import Lock

class ProgressLogger:
    """
    Thread-safe progress logger for sync operations
    Stores logs in memory and allows streaming to multiple clients
    """
    
    def __init__(self, max_logs=1000):
        self.logs = []
        self.max_logs = max_logs
        self.lock = Lock()
        self.clients = []  # List of queues for SSE clients
        self.operation_id = None
        self.start_time = None
        self.status = 'idle'  # idle, running, completed, error
        
    def start_operation(self, operation_id):
        """Start a new operation"""
        with self.lock:
            self.operation_id = operation_id
            self.start_time = time.time()
            self.status = 'running'
            self.logs = []
            self.log('info', f'🚀 Starting sync operation: {operation_id}')
    
    def log(self, level, message):
        """Add a log entry"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        entry = {
            'timestamp': timestamp,
            'level': level,
            'message': message,
            'operation_id': self.operation_id
        }
        
        with self.lock:
            # Add to logs
            self.logs.append(entry)
            
            # Trim old logs if needed
            if len(self.logs) > self.max_logs:
                self.logs = self.logs[-self.max_logs:]
            
            # Send to all connected clients
            for client_queue in self.clients:
                try:
                    client_queue.put_nowait(entry)
                except queue.Full:
                    pass  # Client queue full, skip
    
    def info(self, message):
        """Log info message"""
        self.log('info', message)
    
    def success(self, message):
        """Log success message"""
        self.log('success', message)
    
    def warning(self, message):
        """Log warning message"""
        self.log('warning', message)
    
    def error(self, message):
        """Log error message"""
        self.log('error', message)
        self.status = 'error'
    
    def complete(self, message='Operation completed'):
        """Mark operation as complete"""
        duration = time.time() - self.start_time if self.start_time else 0
        self.status = 'completed'
        self.log('success', f'✅ {message} (took {duration:.1f}s)')
    
    def subscribe(self):
        """
        Subscribe to log stream
        Returns a queue that will receive log entries
        """
        client_queue = queue.Queue(maxsize=100)
        
        with self.lock:
            # Add client
            self.clients.append(client_queue)
            
            # Send existing logs to new client
            for log_entry in self.logs:
                try:
                    client_queue.put_nowait(log_entry)
                except queue.Full:
                    break
        
        return client_queue
    
    def unsubscribe(self, client_queue):
        """Unsubscribe from log stream"""
        with self.lock:
            if client_queue in self.clients:
                self.clients.remove(client_queue)
    
    def get_logs(self, since_index=0):
        """Get logs since a specific index"""
        with self.lock:
            return self.logs[since_index:]
    
    def get_status(self):
        """Get current operation status"""
        duration = time.time() - self.start_time if self.start_time else 0
        
        with self.lock:
            return {
                'operation_id': self.operation_id,
                'status': self.status,
                'duration': duration,
                'log_count': len(self.logs),
                'start_time': self.start_time
            }


# Global progress logger instance
_progress_logger = None

def get_progress_logger():
    """Get or create global progress logger"""
    global _progress_logger
    if _progress_logger is None:
        _progress_logger = ProgressLogger()
    return _progress_logger

