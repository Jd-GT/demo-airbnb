#!/bin/bash
#
# Bootstrap para un Droplet nuevo de DigitalOcean (Ubuntu 22.04+).
# Corre como usuario normal con sudo (NO como root).
#
# Uso rápido desde el Droplet:
#   curl -fsSL https://raw.githubusercontent.com/TU_USER/TU_REPO/main/demo-airbnb/deploy/digitalocean-bootstrap.sh | bash
#
set -euo pipefail

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log()  { echo -e "${GREEN}[OK]${NC} $*"; }
warn() { echo -e "${YELLOW}[!!]${NC} $*"; }
die()  { echo -e "${RED}[XX]${NC} $*"; exit 1; }

REPO_URL="${REPO_URL:-https://github.com/CAMBIA_USUARIO/CAMBIA_REPO.git}"
REPO_DIR="${REPO_DIR:-$HOME/p2-abnb}"

log "Actualizando paquetes..."
sudo apt-get update -y && sudo apt-get upgrade -y

log "Instalando Docker + Git..."
if ! command -v docker >/dev/null; then
    curl -fsSL https://get.docker.com | sudo sh
    sudo usermod -aG docker "$USER"
    warn "Agregado al grupo docker. Necesitas cerrar sesión y volver a entrar"
    warn "Cuando vuelvas, ejecuta: cd $REPO_DIR/demo-airbnb && bash deploy/digitalocean-bootstrap.sh"
    exit 0
fi
sudo apt-get install -y git ufw

log "Configurando firewall UFW..."
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw --force enable

if [ ! -d "$REPO_DIR" ]; then
    log "Clonando repo en $REPO_DIR..."
    git clone "$REPO_URL" "$REPO_DIR"
else
    log "Repo encontrado, haciendo pull..."
    git -C "$REPO_DIR" pull --ff-only
fi

cd "$REPO_DIR/demo-airbnb"

if [ ! -f .env.production ]; then
    cp .env.production.example .env.production

    # Generar secrets automáticamente
    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(64))")
    FERNET_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
    DB_PASS=$(openssl rand -base64 24 | tr -d '=/+' | head -c 32)

    sed -i "s|cambiame-genera-uno-con-secrets-token-urlsafe-64|$SECRET_KEY|" .env.production
    sed -i "s|cambiame-genera-uno-con-fernet-generate-key|$FERNET_KEY|" .env.production
    sed -i "s|cambiame-genera-uno-con-openssl-rand-base64-24|$DB_PASS|" .env.production

    # Detectar IP pública del Droplet
    PUBLIC_IP=$(curl -s http://169.254.169.254/metadata/v1/interfaces/public/0/ipv4/address 2>/dev/null || \
                curl -s https://api.ipify.org 2>/dev/null || echo "TU_IP")
    sed -i "s|167.99.10.20|$PUBLIC_IP|g" .env.production

    log "Secrets generados automáticamente en .env.production"
    warn "⚠ EDITA .env.production para poner tu email y contraseña de admin:"
    warn "   nano $REPO_DIR/demo-airbnb/.env.production"
    warn ""
    warn "Campos que DEBES cambiar:"
    warn "   SUPERADMIN_EMAIL_1    <- tu email"
    warn "   SUPERADMIN_PASSWORD_1 <- contraseña segura"
fi

cat <<EOF

────────────────────────────────────────────────────────────
✅ Bootstrap listo. Próximos pasos:

  1. Edita el .env de producción:
     nano $REPO_DIR/demo-airbnb/.env.production

  2. Levanta los contenedores:
     cd $REPO_DIR/demo-airbnb
     docker compose -f docker-compose.prod.yml \\
         --env-file .env.production up -d --build

  3. Revisa los logs del backend:
     docker compose -f docker-compose.prod.yml logs -f backend

     Busca esta línea y guarda el código:
     "Bootstrap CREATE_TENANT invitation code: XXXXXXXXXXXX"

  4. Entra a:  http://IP_DEL_DROPLET/admin
────────────────────────────────────────────────────────────
EOF
