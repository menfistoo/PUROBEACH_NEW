#!/bin/bash
# PuroBeach Production Deployment Script
# Usage: ./deploy.sh <domain>
# Example: ./deploy.sh beach.purobeach.com

set -e

DOMAIN="${1:?Usage: ./deploy.sh <domain>}"
EMAIL="${2:-catia.schubert@proton.me}"

echo "=== PuroBeach Production Deployment ==="
echo "Domain: $DOMAIN"
echo "Email:  $EMAIL"
echo ""

# 1. Update .env.production with domain
sed -i "s/^DOMAIN=.*/DOMAIN=$DOMAIN/" .env.production

# 2. Create initial Nginx config (HTTP only, for Certbot)
echo ">>> Step 1: Starting with HTTP-only config for certificate issuance..."
mkdir -p nginx/conf.d
cat > nginx/conf.d/purobeach-init.conf << 'INITEOF'
server {
    listen 80;
    server_name DOMAIN_PLACEHOLDER;

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        proxy_pass http://app:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
INITEOF
sed -i "s/DOMAIN_PLACEHOLDER/$DOMAIN/g" nginx/conf.d/purobeach-init.conf

# Temporarily rename the SSL config
if [ -f nginx/conf.d/purobeach.conf ]; then
    mv nginx/conf.d/purobeach.conf nginx/conf.d/purobeach.conf.ssl
fi

# 3. Start app + nginx (HTTP only)
echo ">>> Step 2: Starting services..."
FLASK_ENV=production APP_PORT=8000 docker compose up -d app nginx
sleep 5

# 4. Request SSL certificate
echo ">>> Step 3: Requesting SSL certificate..."
docker compose run --rm certbot certonly \
    --webroot \
    --webroot-path=/var/www/certbot \
    --email "$EMAIL" \
    --agree-tos \
    --no-eff-email \
    -d "$DOMAIN"

# 5. Switch to full SSL Nginx config
echo ">>> Step 4: Switching to SSL config..."
rm -f nginx/conf.d/purobeach-init.conf
if [ -f nginx/conf.d/purobeach.conf.ssl ]; then
    mv nginx/conf.d/purobeach.conf.ssl nginx/conf.d/purobeach.conf
fi

# Replace ${DOMAIN} placeholders in nginx config with actual domain
sed -i "s/\${DOMAIN}/$DOMAIN/g" nginx/conf.d/purobeach.conf

# 6. Restart everything in production mode
echo ">>> Step 5: Restarting with full production config..."
FLASK_ENV=production docker compose up -d

echo ""
echo "=== Deployment Complete! ==="
echo "Your app is live at: https://$DOMAIN"
echo ""
echo "Login credentials:"
echo "  Username: admin"
echo "  Password: (check with your administrator)"
echo ""
echo "Certbot auto-renewal is active (every 12h)."
