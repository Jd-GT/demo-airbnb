# Deploy a Azure — guía rápida (≈ 45 min)

Esta guía deja la app corriendo en una **Azure VM Ubuntu** con HTTPS
automático vía **Caddy + Let's Encrypt**, en menos de una hora.

> ¿Por qué no Container Apps / App Service?
> Container Apps requiere registry (ACR) + pipelines de imagen +
> configuración de red. Para una demo de 1 hora es overkill. Una VM
> con docker-compose es la ruta más conocida y rápida cuando ya
> tienes docker funcionando local.

## 0. Antes de empezar

Necesitas:

- Cuenta Azure activa (la free de estudiante sirve perfecto).
- Tarjeta vinculada (la VM más barata es ≈ USD 0.02/h = USD 5/mes).
- Un dominio o subdominio que puedas apuntar a la VM. **Opcional**:
  Azure asigna un FQDN gratis del estilo `mi-vm-12345.brazilsouth.cloudapp.azure.com`,
  y Caddy le puede sacar HTTPS automático.

## 1. Crear la VM (5 min, en el portal de Azure)

1. Portal Azure → **Virtual machines** → **Create** → **Azure virtual machine**.
2. Resource group: crea uno nuevo, `pms-rg`.
3. Virtual machine name: `pms-vm`.
4. Region: la más cercana (Brazil South / East US 2 para LATAM).
5. **Image:** Ubuntu Server 24.04 LTS (Gen2) — o 22.04 si no aparece.
6. **Size:** **Standard_B2s** (2 vCPU, 4 GB RAM, ≈ USD 30/mes). Para
   la demo basta. Puedes downgrade a B1ms después.
7. Authentication: **SSH public key**. Crea/usa una llave nueva
   (descarga el `.pem` si te lo ofrece — lo necesitas para conectarte).
8. Inbound ports: marca **HTTP (80)**, **HTTPS (443)** y **SSH (22)**.
9. Disk: estándar SSD 30 GB es suficiente.
10. Networking → DNS name label: pon algo único, ej. `mi-pms-andres`.
    Esto te da `mi-pms-andres.brazilsouth.cloudapp.azure.com` gratis.
11. Review + Create → Create.

Espera 2-3 minutos. Anota:
- **Public IP**
- **DNS name** (si usaste el del paso 10)

## 2. (Opcional) Apuntar tu propio dominio

Si tienes `mi-pms.example.com`, en tu proveedor DNS:

```
TYPE   NAME       VALUE                TTL
A      mi-pms     <PUBLIC_IP_DE_LA_VM> 300
```

Si NO tienes dominio, usa el FQDN gratis de Azure
(`mi-pms-andres.brazilsouth.cloudapp.azure.com`). Caddy te saca HTTPS
también ahí.

## 3. Conectarte por SSH

Desde Windows (PowerShell):

```powershell
ssh -i C:\path\a\tu-key.pem azureuser@<PUBLIC_IP>
```

(o usa Azure Cloud Shell directo desde el navegador → **Connect** →
**Bastion** o **SSH**).

## 4. Bootstrap de la VM (1 comando)

Ya dentro de la VM:

```bash
# Asume que el repo está en GitHub. Cambia la URL si es otra cosa.
curl -fsSL https://raw.githubusercontent.com/<TU-USUARIO>/<TU-REPO>/main/demo-airbnb/deploy/azure-vm-bootstrap.sh \
  -o azure-vm-bootstrap.sh
bash azure-vm-bootstrap.sh
```

(O si prefieres a mano: `sudo apt update && sudo apt install -y docker.io docker-compose-plugin git ufw` y luego `git clone <URL>`.)

El script instala Docker, configura el firewall, clona el repo y te
deja en `~/p2-abnb/demo-airbnb/`. Al final imprime los próximos pasos.

Si Docker se acabó de instalar, cierra y vuelve a abrir la sesión SSH
para que tu usuario tenga acceso al socket de Docker sin sudo
(`newgrp docker` también sirve sin cerrar sesión).

## 5. Configurar `.env.production`

```bash
cd ~/p2-abnb/demo-airbnb
nano .env.production
```

Reemplaza los valores marcados como `cambiame-...`. Para generar
secrets fuertes:

```bash
# DJANGO_SECRET_KEY
python3 -c "import secrets; print(secrets.token_urlsafe(64))"

# DJANGO_FERNET_KEY (cripto de tokens externos)
sudo apt install -y python3-cryptography
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# POSTGRES_PASSWORD
openssl rand -base64 24
```

Variables críticas:

| Variable | Valor |
|---|---|
| `DOMAIN` | Lo que apuntaste (ej. `mi-pms.example.com` o `mi-pms-andres.brazilsouth.cloudapp.azure.com`) |
| `DJANGO_ALLOWED_HOSTS` | `mi-pms.example.com,<PUBLIC_IP>` |
| `NEXT_PUBLIC_API_URL` | `https://mi-pms.example.com` |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | `https://mi-pms.example.com` |
| `DJANGO_CORS_ALLOWED_ORIGINS` | `https://mi-pms.example.com` |
| `SEED_DEMO_TENANT` | `0` (no quieres data demo en prod) |
| `SUPERADMIN_EMAIL_1` / `SUPERADMIN_PASSWORD_1` | `admin@admin.com` + pass fuerte |
| `SUPERADMIN_EMAIL_2` / `SUPERADMIN_PASSWORD_2` | `afprietol2005@gmail.com` + pass fuerte |

## 6. Levantar la stack

```bash
docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build
```

Toma ~5 min la primera vez (build de las dos imágenes). Monitorea:

```bash
docker compose -f docker-compose.prod.yml logs -f backend
```

Debes ver al final:

```
Superuser CREATED: admin@admin.com
Superuser CREATED: afprietol2005@gmail.com
Bootstrap CREATE_TENANT invitation code: XXXXXXXXXXXX
Starting server...
[INFO] Listening at: http://0.0.0.0:8000 (gunicorn)
```

**Guarda ese `Bootstrap CREATE_TENANT invitation code`** — lo usarás en `/login` la primera vez para crear tu primer tenant real.

## 7. Verificación

Desde tu PC:

```bash
curl -k https://mi-pms.example.com/healthz
# → {"status":"ok","db":true}
```

Abre en el navegador `https://mi-pms.example.com/login`:
- Si ves el banner verde "🔒" → HTTPS automático funcionó.
- Si ves el dashboard al hacer login con `admin@admin.com` → ✅

## 8. Cosas comunes que pueden fallar

### Caddy no obtiene certificado HTTPS

```bash
docker compose -f docker-compose.prod.yml logs caddy --tail 30
```

- Si dice "no such host" → tu DNS no propagó aún. Espera 5-10 min.
- Si dice "rate limit" → Let's Encrypt te limitó por intentos. Espera
  1 hora.

Workaround temporal: edita `Caddyfile`, comenta el bloque `{$DOMAIN} {}`
y descomenta el bloque `:80 {}` para servir sin HTTPS. Reinicia caddy:

```bash
docker compose -f docker-compose.prod.yml restart caddy
```

### El frontend muestra "Failed to fetch" en login

`NEXT_PUBLIC_API_URL` quedó con valor viejo. Reconstruye el frontend:

```bash
docker compose -f docker-compose.prod.yml up -d --build frontend
```

### CSRF / CORS errors

Verifica que `DJANGO_CSRF_TRUSTED_ORIGINS` y `DJANGO_CORS_ALLOWED_ORIGINS`
tengan el `https://` con dominio exacto del frontend.

### Quiero resetear el password de un admin

En `.env.production` cambia `SUPERADMIN_PASSWORD_1` (o 2) y pon
`SUPERADMIN_RESET=1`. Reinicia:

```bash
docker compose -f docker-compose.prod.yml --env-file .env.production up -d
```

Después vuelve a poner `SUPERADMIN_RESET=0` para que no se resetee en
cada arranque.

## 9. Mantenimiento

```bash
# Ver el estado
docker compose -f docker-compose.prod.yml ps

# Actualizar a la última versión del repo
cd ~/p2-abnb && git pull
cd demo-airbnb
docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build

# Backup de la DB
docker compose -f docker-compose.prod.yml exec db pg_dump -U pms_app pms > backup_$(date +%F).sql

# Restaurar
cat backup_2026-05-20.sql | docker compose -f docker-compose.prod.yml exec -T db psql -U pms_app pms

# Apagar todo (sin perder data)
docker compose -f docker-compose.prod.yml down

# Apagar y BORRAR la DB (cuidado)
docker compose -f docker-compose.prod.yml down -v
```

## 10. Costo estimado mensual

| Recurso | Costo aprox |
|---|---|
| VM Standard_B2s (730h/mes) | ~USD 30 |
| Disco 30 GB SSD | ~USD 5 |
| IP pública estática | ~USD 4 |
| Egress (tráfico salida, primeros 100 GB) | gratis |
| **Total** | **~USD 39/mes** |

Para apagar costos cuando no la uses: portal Azure → VM → **Stop**
(deallocate). Pagas sólo el disco (~USD 5/mes).
