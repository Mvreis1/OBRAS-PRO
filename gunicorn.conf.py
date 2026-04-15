"""
Gunicorn configuration file for OBRAS_FINANCEIRO
Centralized settings for production deployment
"""

import multiprocessing
from pathlib import Path

from decouple import AutoConfig

# Setup decouple: auto-detecta .env no projeto
config = AutoConfig(search_path=str(Path(__file__).resolve().parent))

# Server socket
bind = f"0.0.0.0:{config('PORT', default='5000')}"
backlog = 2048

# Worker processes
workers = int(config('GUNICORN_WORKERS', default=multiprocessing.cpu_count() * 2 + 1))
worker_class = config('GUNICORN_WORKER_CLASS', default='gthread')
threads = int(config('GUNICORN_THREADS', default='4'))
worker_connections = 1000
max_requests = int(config('GUNICORN_MAX_REQUESTS', default='1000'))
max_requests_jitter = int(config('GUNICORN_MAX_REQUESTS_JITTER', default='50'))

# Timeout
graceful_timeout = int(config('GUNICORN_GRACEFUL_TIMEOUT', default='30'))
timeout = int(config('GUNICORN_TIMEOUT', default='120'))
keepalive = int(config('GUNICORN_KEEPALIVE', default='5'))

# Restart workers after this many requests, to help prevent memory leaks
requests = max_requests
requests_jitter = max_requests_jitter

# Logging
accesslog = config('GUNICORN_ACCESS_LOG', default='-')  # '-' = stdout
errorlog = config('GUNICORN_ERROR_LOG', default='-')
loglevel = config('GUNICORN_LOG_LEVEL', default='info')
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# StatsD monitoring (optional)
# statsd_host = 'localhost:8125'
# statsd_prefix = 'obras_pro'

# Process naming
proc_name = 'obras-pro'

# Server mechanics
preload_app = True
daemon = False
pidfile = '/tmp/obras-pro.pid'

# Worker temporary directory
worker_tmp_dir = '/dev/shm'  # Use tmpfs for better performance

# SSL (if not using nginx reverse proxy)
# keyfile = "/path/to/keyfile"
# certfile = "/path/to/certfile"

# When True, closing master process will refuse new connections but wait for all requests to finish.
# This is useful for graceful shutdown
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


def worker_int(worker):
    """Called when a worker receives the INT signal."""
    worker.log.warning("Worker %s received INT signal", worker.pid)


def worker_abort(worker):
    """Called when a worker receives the ABORT signal."""
    worker.log.warning("Worker %s received ABORT signal", worker.pid)
