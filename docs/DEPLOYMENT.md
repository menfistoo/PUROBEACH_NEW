# PuroBeach — Server Deployment Guide

## Prerequisites

- A Linux server (Ubuntu 22.04+ recommended) with:
  - Docker Engine installed
  - Docker Compose v2 installed
  - Git installed
  - At least 1 GB RAM, 10 GB disk
- SSH access to the server

## Quick Start (HTTP, no domain)

### 1. Clone the repository on the server

```bash
ssh user@your-server-ip
cd /opt   # or wherever you keep apps
git clone https://github.com/menfistoo/PUROBEACH_NEW.git purobeach
cd purobeach
```

### 2. Create the environment file

```bash
cp .env.production.example .env.production
```

Edit `.env.production` and set the `SECRET_KEY`:

```bash
# Generate a secure key:
python3 -c "import secrets; print(secrets.token_hex(32))"

# Paste the output as SECRET_KEY in .env.production
nano .env.production
```

Your `.env.production` should look like:

```
FLASK_APP=wsgi.py
SECRET_KEY=your_64_char_hex_string_here
DATABASE_PATH=/app/instance/beach_club.db
SESSION_COOKIE_SECURE=false
```

### 3. Deploy

```bash
chmod +x deploy.sh
./deploy.sh
```

This will:
- Build the Docker image
- Initialize the database (first run only)
- Run migrations
- Start Gunicorn (app) + Nginx (reverse proxy)

### 4. Access the app

Open `http://your-server-ip` in a browser.

**Default login:**
- Username: `admin`
- Password: `admin`
- **Change the password immediately** in Admin > Users

## Adding SSL (when you have a domain)

### 1. Point your domain DNS to the server IP

Create an A record:
```
yourdomain.com → your-server-ip
```

Wait for DNS propagation (check with `dig yourdomain.com`).

### 2. Run the SSL deployment

```bash
./deploy.sh yourdomain.com
```

This will:
- Request a Let's Encrypt SSL certificate
- Switch Nginx to HTTPS
- Enable secure cookies
- Start auto-renewal (every 12h)

### 3. Access via HTTPS

Open `https://yourdomain.com`

## Common Operations

### View logs

```bash
# Application logs
docker compose logs app -f

# Nginx logs
docker compose logs nginx -f

# All logs
docker compose logs -f
```

### Restart services

```bash
docker compose restart        # Restart all
docker compose restart app    # Restart app only
```

### Update the application

```bash
git pull
docker compose up -d --build
```

### Database backup

```bash
# Copy DB from the Docker volume to the host
docker cp purobeach-app:/app/instance/beach_club.db ./backup-$(date +%Y%m%d).db
```

### Database restore

```bash
# Stop the app, copy DB in, restart
docker compose stop app
docker cp ./backup.db purobeach-app:/app/instance/beach_club.db
docker compose start app
```

### Check health

```bash
curl http://localhost:8000/api/health
```

## Architecture

```
Internet
   │
   ▼
┌─────────┐      ┌──────────────┐      ┌──────────┐
│  Nginx  │──────│  Gunicorn    │──────│  SQLite   │
│  :80    │      │  :8000       │      │  (WAL)   │
│  (:443) │      │  2 workers   │      │          │
└─────────┘      └──────────────┘      └──────────┘
     │
     └── Static files served directly from shared volume
```

**Volumes:**
| Volume | Container Path | Purpose |
|--------|---------------|---------|
| `db-data` | `/app/instance/` | SQLite database |
| `uploads` | `/app/static/uploads/` | User-uploaded files |
| `logs` | `/app/logs/` | Application logs |
| `static-shared` | `/app/static-shared/` | Static files (Nginx) |

## Troubleshooting

### Container won't start
```bash
docker compose logs app    # Check for errors
docker compose ps          # Check container status
```

### Database initialization fails
```bash
# Manually initialize
docker compose exec app flask init-db --confirm
```

### Nginx shows 502 Bad Gateway
The app container isn't ready yet. Wait for the health check (40s start period) or check app logs.

### Permission errors
```bash
# Fix ownership inside the container
docker compose exec --user root app chown -R purobeach:purobeach /app/instance /app/logs /app/static/uploads
```

### Reset everything (destructive!)
```bash
docker compose down -v    # Removes all volumes (DB, uploads, logs)
./deploy.sh               # Fresh start
```
