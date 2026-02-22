#!/bin/bash
# PuroBeach Production Deployment Script
# =============================================================================
#
# Two modes:
#   1. HTTP-only (no args):  ./deploy.sh
#      Starts the app with HTTP on port 80 (no domain needed)
#
#   2. SSL with domain:      ./deploy.sh <domain> [email]
#      Obtains SSL cert and configures HTTPS
#
# =============================================================================

set -e

DOMAIN="${1:-}"
EMAIL="${2:-catia.schubert@proton.me}"

# =============================================================================
# HTTP-ONLY DEPLOYMENT (no domain)
# =============================================================================
if [ -z "$DOMAIN" ]; then
    echo "=== PuroBeach HTTP Deployment ==="
    echo ""

    # Check .env.production exists
    if [ ! -f .env.production ]; then
        echo "ERROR: .env.production not found."
        echo "Copy .env.production.example to .env.production and fill in SECRET_KEY."
        exit 1
    fi

    # Ensure HTTP config is active
    if [ -f nginx/conf.d/purobeach.conf ]; then
        mv nginx/conf.d/purobeach.conf nginx/conf.d/purobeach.conf.ssl
    fi

    echo ">>> Starting services (HTTP mode)..."
    docker compose up -d --build

    echo ""
    echo "=== Deployment Complete! ==="
    echo "Your app is live at: http://$(curl -s ifconfig.me 2>/dev/null || echo '<your-server-ip>')"
    echo ""
    echo "Login credentials:"
    echo "  Username: admin"
    echo "  Password: admin (change immediately!)"
    echo ""
    echo "To add SSL later, run: ./deploy.sh yourdomain.com"
    exit 0
fi

# =============================================================================
# SSL DEPLOYMENT (with domain)
# =============================================================================
echo "=== PuroBeach SSL Deployment ==="
echo "Domain: $DOMAIN"
echo "Email:  $EMAIL"
echo ""

# Check .env.production exists
if [ ! -f .env.production ]; then
    echo "ERROR: .env.production not found."
    echo "Copy .env.production.example to .env.production and fill in SECRET_KEY."
    exit 1
fi

# 1. Update .env.production with domain and enable secure cookies
sed -i "s/^DOMAIN=.*/DOMAIN=$DOMAIN/" .env.production 2>/dev/null || true
sed -i "s/^# DOMAIN=.*/DOMAIN=$DOMAIN/" .env.production 2>/dev/null || true
sed -i "s/^SESSION_COOKIE_SECURE=.*/SESSION_COOKIE_SECURE=true/" .env.production

# 2. Ensure HTTP config is active for initial cert request
if [ -f nginx/conf.d/purobeach.conf ]; then
    mv nginx/conf.d/purobeach.conf nginx/conf.d/purobeach.conf.ssl
fi
if [ ! -f nginx/conf.d/purobeach-http.conf ]; then
    echo "ERROR: nginx/conf.d/purobeach-http.conf not found."
    exit 1
fi

# 3. Create SSL docker-compose override with certbot
cat > docker-compose.ssl.yml << 'EOF'
services:
  nginx:
    ports:
      - "${SERVER_IP:-0.0.0.0}:443:443"
    volumes:
      - certbot-conf:/etc/letsencrypt:ro

  certbot:
    image: certbot/certbot
    container_name: purobeach-certbot
    restart: unless-stopped
    volumes:
      - certbot-conf:/etc/letsencrypt
      - certbot-www:/var/www/certbot
    entrypoint: /bin/sh -c 'trap exit TERM; while :; do certbot renew --quiet; sleep 12h & wait $${!}; done'

volumes:
  certbot-conf:
    driver: local
EOF

# 4. Start app + nginx (HTTP only) for cert issuance
echo ">>> Step 1: Starting services in HTTP mode..."
docker compose up -d --build
sleep 5

# 5. Request SSL certificate
echo ">>> Step 2: Requesting SSL certificate for $DOMAIN..."
docker compose -f docker-compose.yml -f docker-compose.ssl.yml run --rm certbot certonly \
    --webroot \
    --webroot-path=/var/www/certbot \
    --email "$EMAIL" \
    --agree-tos \
    --no-eff-email \
    -d "$DOMAIN"

# 6. Switch to full SSL Nginx config
echo ">>> Step 3: Switching to SSL config..."
rm -f nginx/conf.d/purobeach-http.conf
if [ -f nginx/conf.d/purobeach.conf.ssl ]; then
    mv nginx/conf.d/purobeach.conf.ssl nginx/conf.d/purobeach.conf
fi

# Replace ${DOMAIN} placeholders in nginx config with actual domain
sed -i "s/\${DOMAIN}/$DOMAIN/g" nginx/conf.d/purobeach.conf

# 7. Restart everything with SSL
echo ">>> Step 4: Restarting with full SSL config..."
docker compose -f docker-compose.yml -f docker-compose.ssl.yml up -d

echo ""
echo "=== Deployment Complete! ==="
echo "Your app is live at: https://$DOMAIN"
echo ""
echo "Login credentials:"
echo "  Username: admin"
echo "  Password: admin (change immediately!)"
echo ""
echo "Certbot auto-renewal is active (every 12h)."
