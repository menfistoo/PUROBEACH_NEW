# Docker Production Deployment — HTTP-First

**Date:** 2026-02-21
**Status:** Approved
**Approach:** Fix existing Docker stack, deploy HTTP-first on Contabo VPS, add HTTPS/domain later

## Context

The project already has a Docker setup (Dockerfile, docker-compose, Nginx, Gunicorn, deploy script) but contains several critical bugs that prevent successful deployment. The target is a Contabo VPS with Docker installed, accessed via SSH from VS Code. No domain is available yet.

## Critical Bug Fixes

### 1. docker-entrypoint.sh — missing `--confirm` flag
- Line 18: `flask init-db` must become `flask init-db --confirm`
- Without this, first boot on empty DB exits with code 1

### 2. Dockerfile — missing FLASK_APP env var
- Flask CLI commands (`init-db`, `run-migrations`) need `FLASK_APP` to find the app
- Add `FLASK_APP=wsgi.py` to the ENV block

### 3. .dockerignore — missing temp patterns
- Add `tmpclaude-*/` to prevent Claude Code temp dirs in image

### 4. docker-entrypoint.sh — stale static files
- Replace `cp -r` with clean-then-copy to remove old files between deploys

## HTTP-First Nginx Config

Create `nginx/conf.d/purobeach-http.conf`:
- Listen port 80 only, no SSL
- Proxy to app with all rate limiting
- Security headers (minus HSTS)
- Direct static file serving
- ACME challenge location (ready for future SSL)

The existing `purobeach.conf` (SSL) stays untouched for when `deploy.sh` activates it.

## Docker Compose Changes

- Remove certbot dependency for default mode
- Nginx uses HTTP config by default
- Port 443 only exposed when SSL is active
- Add `FLASK_APP` to environment

## ProductionConfig — Conditional SESSION_COOKIE_SECURE

- Make `SESSION_COOKIE_SECURE` configurable via env var
- Default to `False` for HTTP-only mode
- Flip to `True` when SSL is added

## .env.production Updates

- Add `FLASK_APP=wsgi.py`
- Add `SESSION_COOKIE_SECURE=false`
- Clear comments for domain setup

## Deliverables

1. Fixed `docker-entrypoint.sh`
2. Fixed `Dockerfile`
3. Fixed `.dockerignore`
4. New `nginx/conf.d/purobeach-http.conf`
5. Updated `docker-compose.yml` (HTTP-first default)
6. Updated `config.py` (conditional cookie secure)
7. Updated `.env.production.example`
8. New `docs/DEPLOYMENT.md` with step-by-step instructions
