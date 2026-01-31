#!/bin/bash
# =============================================================================
# PuroBeach One-Command Deployment Script
# =============================================================================
# Usage: ./deploy.sh
# =============================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== PuroBeach Production Deployment ===${NC}"

# --- 1. Check prerequisites ---
echo -e "\n${YELLOW}[1/6] Checking prerequisites...${NC}"

if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed.${NC}"
    exit 1
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo -e "${RED}Error: Docker Compose is not installed.${NC}"
    exit 1
fi

echo "  Docker: $(docker --version)"

# Detect docker compose command
if docker compose version &> /dev/null; then
    COMPOSE_CMD="docker compose"
else
    COMPOSE_CMD="docker-compose"
fi
echo "  Compose: $COMPOSE_CMD"

# --- 2. Environment file ---
echo -e "\n${YELLOW}[2/6] Checking environment configuration...${NC}"

if [ ! -f .env.production ]; then
    echo "  Creating .env.production from template..."
    cp .env.production.example .env.production

    # Generate a random SECRET_KEY
    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))" 2>/dev/null || openssl rand -hex 32)
    sed -i "s/^SECRET_KEY=$/SECRET_KEY=${SECRET_KEY}/" .env.production

    echo -e "  ${YELLOW}IMPORTANT: Edit .env.production with your domain and email before proceeding.${NC}"
    echo "  Generated SECRET_KEY automatically."
    echo ""
    echo "  Required settings:"
    echo "    - DOMAIN=your-domain.com"
    echo "    - ADMIN_EMAIL=your-email@example.com"
    echo ""
    read -p "  Press Enter after editing .env.production (or Ctrl+C to abort)..."
fi

# Validate required env vars
source .env.production
if [ -z "${SECRET_KEY}" ]; then
    echo -e "${RED}Error: SECRET_KEY is not set in .env.production${NC}"
    exit 1
fi
if [ -z "${DOMAIN}" ] || [ "${DOMAIN}" = "example.com" ]; then
    echo -e "${YELLOW}Warning: DOMAIN is not configured (using '${DOMAIN:-example.com}').${NC}"
    echo "  For production with SSL, set DOMAIN in .env.production."
fi
echo "  Environment OK."

# --- 3. Build images ---
echo -e "\n${YELLOW}[3/6] Building Docker images...${NC}"
$COMPOSE_CMD build

# --- 4. Start services ---
echo -e "\n${YELLOW}[4/6] Starting services...${NC}"
$COMPOSE_CMD up -d

# --- 5. Health check ---
echo -e "\n${YELLOW}[5/6] Verifying health...${NC}"
sleep 5

MAX_RETRIES=10
RETRY=0
until curl -sf http://localhost/api/health > /dev/null 2>&1 || [ $RETRY -ge $MAX_RETRIES ]; do
    RETRY=$((RETRY + 1))
    echo "  Waiting for app to start (attempt $RETRY/$MAX_RETRIES)..."
    sleep 3
done

if [ $RETRY -ge $MAX_RETRIES ]; then
    echo -e "${YELLOW}  Warning: Health check via Nginx not responding (SSL may need setup).${NC}"
    echo "  Checking app container directly..."
    if curl -sf http://localhost:8000/api/health > /dev/null 2>&1; then
        echo -e "  ${GREEN}App container is healthy.${NC}"
    else
        echo -e "${RED}  Error: App container health check failed.${NC}"
        echo "  Check logs: $COMPOSE_CMD logs app"
        exit 1
    fi
else
    echo -e "  ${GREEN}Health check passed!${NC}"
fi

# --- 6. Setup backup cron ---
echo -e "\n${YELLOW}[6/6] Setting up backup cron job...${NC}"

CRON_JOB="0 3 * * * docker exec purobeach-app /app/scripts/backup.sh >> /var/log/purobeach-backup.log 2>&1"
if crontab -l 2>/dev/null | grep -q "purobeach-app"; then
    echo "  Backup cron already configured."
else
    (crontab -l 2>/dev/null; echo "${CRON_JOB}") | crontab -
    echo "  Backup cron installed (daily at 3:00 AM)."
fi

# --- Done ---
echo -e "\n${GREEN}=== Deployment Complete ===${NC}"
echo ""
echo "  Services: $COMPOSE_CMD ps"
echo "  Logs:     $COMPOSE_CMD logs -f"
echo "  Stop:     $COMPOSE_CMD down"
echo "  Backup:   docker exec purobeach-app /app/scripts/backup.sh"
echo ""

if [ "${DOMAIN}" != "example.com" ] && [ -n "${DOMAIN}" ] && [ -n "${ADMIN_EMAIL}" ]; then
    echo -e "${YELLOW}SSL Setup:${NC}"
    echo "  Run once to obtain certificates:"
    echo "  $COMPOSE_CMD run --rm certbot certonly --webroot -w /var/www/certbot -d ${DOMAIN} -d www.${DOMAIN} --email ${ADMIN_EMAIL} --agree-tos --no-eff-email"
    echo "  Then restart nginx: $COMPOSE_CMD restart nginx"
fi
