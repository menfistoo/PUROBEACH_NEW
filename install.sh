#!/bin/bash
# =============================================================================
# PuroBeach — One-Command VM Installer
# =============================================================================
# Tested on: Ubuntu 22.04 LTS / Ubuntu 24.04 LTS
#
# Usage (run as root or with sudo):
#   curl -sSL https://raw.githubusercontent.com/menfistoo/PUROBEACH_NEW/main/install.sh | bash
#
#   Or after cloning:
#   sudo bash install.sh
#
# Optional arguments:
#   sudo bash install.sh [domain] [admin-email]
#
#   With domain: sets up SSL via Let's Encrypt automatically.
#   Without domain: runs HTTP-only (access via server IP).
# =============================================================================

set -e

DOMAIN="${1:-}"
ADMIN_EMAIL="${2:-catia.schubert@proton.me}"
INSTALL_DIR="/opt/purobeach"
REPO_URL="https://github.com/menfistoo/PUROBEACH_NEW.git"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

info()    { echo -e "${CYAN}>>> $*${NC}"; }
success() { echo -e "${GREEN}✓  $*${NC}"; }
warn()    { echo -e "${YELLOW}⚠  $*${NC}"; }
error()   { echo -e "${RED}✗  $*${NC}" >&2; exit 1; }

# =============================================================================
# 1. ROOT CHECK
# =============================================================================
if [ "$EUID" -ne 0 ]; then
    error "Please run as root: sudo bash install.sh"
fi

echo ""
echo "============================================================"
echo "  PuroBeach — VM Installer"
echo "============================================================"
echo ""

# =============================================================================
# 2. OS CHECK
# =============================================================================
info "Checking operating system..."
if ! grep -qi "ubuntu" /etc/os-release 2>/dev/null; then
    warn "This script is designed for Ubuntu 22.04/24.04."
    warn "Continuing anyway — some steps may fail on other distros."
fi
UBUNTU_VERSION=$(grep VERSION_ID /etc/os-release | cut -d'"' -f2 2>/dev/null || echo "unknown")
success "OS detected: Ubuntu $UBUNTU_VERSION"

# =============================================================================
# 3. SYSTEM PACKAGES
# =============================================================================
info "Updating package lists..."
apt-get update -qq

info "Installing prerequisites (git, curl, ca-certificates)..."
apt-get install -y -qq git curl ca-certificates gnupg lsb-release
success "Prerequisites installed"

# =============================================================================
# 4. DOCKER ENGINE
# =============================================================================
if command -v docker &>/dev/null; then
    DOCKER_VERSION=$(docker --version | awk '{print $3}' | tr -d ',')
    success "Docker already installed: $DOCKER_VERSION"
else
    info "Installing Docker Engine..."

    # Add Docker's official GPG key
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
        | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    chmod a+r /etc/apt/keyrings/docker.gpg

    # Add Docker apt repository
    echo \
        "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
        https://download.docker.com/linux/ubuntu \
        $(lsb_release -cs) stable" \
        | tee /etc/apt/sources.list.d/docker.list > /dev/null

    apt-get update -qq
    apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

    systemctl enable docker
    systemctl start docker

    success "Docker Engine installed"
fi

# =============================================================================
# 5. DOCKER COMPOSE V2 CHECK
# =============================================================================
if docker compose version &>/dev/null; then
    COMPOSE_VERSION=$(docker compose version --short)
    success "Docker Compose already available: $COMPOSE_VERSION"
else
    error "Docker Compose v2 not found. Re-run the installer or install docker-compose-plugin manually."
fi

# =============================================================================
# 6. CLONE / UPDATE REPOSITORY
# =============================================================================
if [ -d "$INSTALL_DIR/.git" ]; then
    info "Updating existing repository at $INSTALL_DIR..."
    git -C "$INSTALL_DIR" pull --ff-only
    success "Repository updated"
else
    info "Cloning repository to $INSTALL_DIR..."
    git clone "$REPO_URL" "$INSTALL_DIR"
    success "Repository cloned"
fi

cd "$INSTALL_DIR"

# =============================================================================
# 7. CREATE .env.production (if not already present)
# =============================================================================
if [ -f .env.production ]; then
    warn ".env.production already exists — leaving it unchanged."
else
    info "Generating .env.production..."

    # Generate a cryptographically secure 64-character hex secret key
    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")

    cat > .env.production << EOF
# =============================================================================
# PuroBeach Production Environment — generated by install.sh
# =============================================================================

FLASK_APP=wsgi.py

# Secret key — do NOT share or commit this value
SECRET_KEY=${SECRET_KEY}

# Database path inside the container
DATABASE_PATH=/app/instance/beach_club.db

# Set to true only when running behind HTTPS
SESSION_COOKIE_SECURE=false

# Uncomment and fill in when you add a domain + SSL:
# DOMAIN=${DOMAIN}
# ADMIN_EMAIL=${ADMIN_EMAIL}
EOF

    success ".env.production created with a generated SECRET_KEY"
fi

# =============================================================================
# 8. MAKE SCRIPTS EXECUTABLE
# =============================================================================
chmod +x deploy.sh
success "deploy.sh is executable"

# =============================================================================
# 9. DEPLOY
# =============================================================================
info "Starting PuroBeach..."
echo ""

if [ -n "$DOMAIN" ]; then
    ./deploy.sh "$DOMAIN" "$ADMIN_EMAIL"
else
    ./deploy.sh
fi

# =============================================================================
# DONE
# =============================================================================
echo ""
echo "============================================================"
echo "  Installation Complete!"
echo "============================================================"
SERVER_IP=$(curl -s --max-time 5 ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}')
echo ""
if [ -n "$DOMAIN" ]; then
    echo "  App URL:   https://${DOMAIN}"
else
    echo "  App URL:   http://${SERVER_IP}"
fi
echo ""
echo "  Login:     admin / admin"
echo "  IMPORTANT: Change the password immediately after first login!"
echo ""
echo "  App dir:   ${INSTALL_DIR}"
echo "  Logs:      docker compose -C ${INSTALL_DIR} logs -f"
echo "  Restart:   docker compose -C ${INSTALL_DIR} restart"
echo "  Update:    git -C ${INSTALL_DIR} pull && docker compose -C ${INSTALL_DIR} up -d --build"
echo ""
echo "  To add SSL later:"
echo "    cd ${INSTALL_DIR} && ./deploy.sh yourdomain.com"
echo ""
