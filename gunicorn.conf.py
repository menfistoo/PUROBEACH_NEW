"""Gunicorn configuration for production deployment."""

# Server socket
bind = '0.0.0.0:8000'

# Worker processes — 2 workers with 4 threads each.
# Optimized for SQLite (avoid too many concurrent writers).
workers = 2
threads = 4
worker_class = 'gthread'

# Timeout — 120s to accommodate slow Excel imports
timeout = 120
graceful_timeout = 30
keepalive = 5

# Logging
accesslog = '/app/logs/gunicorn-access.log'
errorlog = '/app/logs/gunicorn-error.log'
loglevel = 'info'
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = 'purobeach'

# Preload app for faster worker startups
preload_app = True

# Worker recycling — restart workers after 1000 requests to prevent memory leaks
max_requests = 1000
max_requests_jitter = 50

# Security
limit_request_line = 8190
limit_request_fields = 100
limit_request_field_size = 8190
