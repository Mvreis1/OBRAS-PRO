"""
Gunicorn configuration file for OBRAS_FINANCEIRO
Centralized settings for production deployment
"""

import multiprocessing
import os

# Helper para ler variáveis de ambiente
def get_env(key, default):
    """Get environment variable with default"""
    return os.environ.get(key, default)

# Server socket
bind = f"0.0.0.0:{get_env('PORT', '5000')}"
backlog = 2048

# Worker processes
workers = int(get_env('GUNICORN_WORKERS', '1'))
worker_class = get_env('GUNICORN_WORKER_CLASS', 'gthread')
threads = int(get_env('GUNICORN_THREADS', '4'))
worker_connections = 1000
max_requests = int(get_env('GUNICORN_MAX_REQUESTS', '500'))
max_requests_jitter = int(get_env('GUNICORN_MAX_REQUESTS_JITTER', '50'))

# Timeout
graceful_timeout = int(get_env('GUNICORN_GRACEFUL_TIMEOUT', '30'))
timeout = int(get_env('GUNICORN_TIMEOUT', '120'))
keepalive = int(get_env('GUNICORN_KEEPALIVE', '5'))

# Restart workers after this many requests, to help prevent memory leaks
requests = max_requests
requests_jitter = max_requests_jitter

# Logging
accesslog = get_env('GUNICORN_ACCESS_LOG', '-')  # '-' = stdout
errorlog = get_env('GUNICORN_ERROR_LOG', '-')
loglevel = get_env('GUNICORN_LOG_LEVEL', 'info')
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = 'obras-financeiro'

# Server mechanics
preload_app = True
daemon = False

# Worker temporary directory
worker_tmp_dir = '/dev/shm'  # Use tmpfs for better performance

# Enable stdio inheritance
enable_stdio_inheritance = True


def on_starting(server):
    """Called just before the master process is initialized."""
    server.log.info("OBRAS_FINANCEIRO starting up...")


def on_reload(server):
    """Called to recycle worker processes when a SIGHUP is received."""
    server.log.info("OBRAS_FINANCEIRO reloading...")


def when_ready(server):
    """Called just after the server is started."""
    server.log.info("OBRAS_FINANCEIRO is ready. Listening on %s", server.address)


def pre_fork(server, worker):
    """Called just before a worker is forked."""
    server.log.debug("Pre-forking worker %s", worker.pid)


def post_fork(server, worker):
    """Called just after a worker has been forked."""
    server.log.debug("Worker %s forked", worker.pid)


def post_worker_init(worker):
    """Called after a worker has been initialized."""
    worker.log.debug("Worker %s initialized", worker.pid)
