#!/bin/bash
#
# Provision script for a brand-new Ubuntu 22.04+ VM on Azure.
# Run AS THE ADMIN USER (no sudo prefix — the script will sudo).
#
# Lo que hace:
#   1. Instala docker, docker compose, git
#   2. Clona el repo (si no está)
#   3. Te recuerda los siguientes pasos manuales
#
# Uso:
#   curl -fsSL https://raw.githubusercontent.com/<user>/<repo>/main/demo-airbnb/deploy/azure-vm-bootstrap.sh | bash
# o:
#   wget https://...azure-vm-bootstrap.sh && bash azure-vm-bootstrap.sh
#
set -euo pipefail

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log()  { echo -e "${GREEN}[OK]${NC} $*"; }
warn() { echo -e "${YELLOW}[!!]${NC} $*"; }
die()  { echo -e "${RED}[XX]${NC} $*"; exit 1; }

[ "$(whoami)" = "root" ] && die "Corre como tu usuario normal, no root."

REPO_URL="${REPO_URL:-https://github.com/CHANGEME/CHANGEME.git}"
REPO_DIR="${REPO_DIR:-$HOME/p2-abnb}"

log "Actualizando paquetes del sistema..."
sudo apt-get update -y
sudo apt-get upgrade -y

log "Instalando docker + git..."
if ! command -v docker >/dev/null; then
    curl -fsSL https://get.docker.com | sudo sh
    sudo usermod -aG docker "$USER"
    warn "Te añadí al grupo docker. Cierra sesión y vuelve a entrar (o ejecuta: newgrp docker)"
fi
sudo apt-get install -y git ufw

log "Configurando firewall (UFW)..."
sudo ufw allow OpenSSH || true
sudo ufw allow 80/tcp  || true
sudo ufw allow 443/tcp || true
sudo ufw --force enable

if [ ! -d "$REPO_DIR" ]; then
    log "Clonando repo a $REPO_DIR..."
    git clone "$REPO_URL" "$REPO_DIR"
else
    log "Repo ya existe en $REPO_DIR, haciendo pull..."
    cd "$REPO_DIR" && git pull --ff-only
fi

cd "$REPO_DIR/demo-airbnb"

if [ ! -f .env.production ]; then
    log "Copiando .env.production.example -> .env.production"
    cp .env.production.example .env.production
    warn "⚠ EDITA .env.production CON SECRETS REALES ANTES DE LEVANTAR"
    warn "   nano $REPO_DIR/demo-airbnb/.env.production"
    warn ""
    warn "Genera valores reales con:"
    warn "   DJANGO_SECRET_KEY:   python3 -c 'import secrets; print(secrets.token_urlsafe(64))'"
    warn "   DJANGO_FERNET_KEY:   python3 -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
    warn "   POSTGRES_PASSWORD:   openssl rand -base64 24"
fi

cat <<'EOF'

────────────────────────────────────────────────────────────
✅ Bootstrap listo. Próximos pasos manuales:

  1. nano demo-airbnb/.env.production    # llena DOMAIN y secrets
  2. Apunta tu DNS A-record a esta VM (ej: mi-pms.example.com)
  3. cd demo-airbnb
     docker compose -f docker-compose.prod.yml \
         --env-file .env.production up -d --build
  4. docker compose -f docker-compose.prod.yml logs -f backend
     (espera "Bootstrap CREATE_TENANT invitation code: XXXX" y guárdalo)
  5. Abre https://TU_DOMINIO/login en el navegador
────────────────────────────────────────────────────────────
EOF
