# Setup local

## Requisitos

- Python 3.13 (probado con 3.14)
- Node.js 20+ (para el frontend)
- (opcional) Docker + Docker Compose
- (opcional) PostgreSQL 14+ — si no, se usa SQLite por defecto

## Backend

### 1. Instalar dependencias

```bash
cd demoairbnb
python -m venv .venv
source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r ../requirements.txt
```

### 2. Variables de entorno (opcional en dev)

Crea `.env` en la raíz si quieres cambiar defaults:

```bash
DJANGO_SECRET_KEY=cambiame-en-prod-por-favor
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
DJANGO_CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173

# Postgres (opcional; si no se setea POSTGRES_DB, usa SQLite local)
POSTGRES_DB=demoairbnb
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
```

### 3. Migraciones

```bash
python manage.py migrate
```

### 4. Crear super-admin

```bash
python manage.py createsuperuser
```

Esto crea un user con `is_superuser=True`. Es el "operador del SaaS" —
NO está asociado a ningún tenant. Se usa para entrar a `/admin/` y
gestionar tenants + invitation codes.

### 5. Generar el primer CREATE_TENANT code

```bash
python manage.py issue_invite_code --notes "Primer tenant del sistema"
```

Esto imprime un código (ej: `AB12CD34EF56`) que puedes usar luego en
`/login` del frontend para crear la primera empresa.

### 6. Levantar el server

```bash
python manage.py runserver
```

API en `http://localhost:8000`. Swagger en
`http://localhost:8000/api/schema/swagger/`.

### 7. Tests

```bash
python manage.py test apps
```

Deben dar 28 tests verdes (a 2026-05-13). Si añades código nuevo, añade
tests y mantén el contador subiendo.

## Frontend

```bash
cd frontend/demo-airbnb
npm install     # o bun install si prefieres
npm run dev
```

App en `http://localhost:3000`. Si tu backend está en otra URL, configura:

```bash
# frontend/demo-airbnb/.env.local
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Flujo end-to-end mínimo (para validar que todo funciona)

1. Levantas backend (`runserver`) y frontend (`npm run dev`).
2. En el backend, generas un `CREATE_TENANT` code (paso 5 arriba).
3. Vas a `http://localhost:3000/login` → "Tengo un código de invitación".
4. Pegas el code, eliges "Para abrir una empresa nueva".
5. Llenas el formulario y submit.
6. Quedas adentro como OWNER de tu nuevo tenant.
7. Vas a `/settings` → generas un código JOIN_TENANT para invitar a otra
   persona.
8. (En otro navegador o privado) entras con ese segundo código eligiendo
   "Para entrar a una empresa". Quedas como MEMBER.

## Docker (opcional)

`docker-compose.yml` levanta Postgres + backend + frontend juntos.

```bash
docker compose up --build
```

Si es la primera vez, dentro del container del backend corre las
migraciones:

```bash
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py createsuperuser
docker compose exec backend python manage.py issue_invite_code
```

## Atajos útiles

| Comando                                          | Para qué                             |
| ------------------------------------------------ | ------------------------------------ |
| `python manage.py issue_invite_code`             | CREATE_TENANT, 1 uso, sin expiry.    |
| `python manage.py issue_invite_code --expires-days 7 --notes "X"` | Con expiry y nota.   |
| `python manage.py issue_invite_code --join --tenant acme --max-uses 5` | JOIN para tenant existente. |
| `python manage.py shell`                         | REPL Django para hacer queries.      |
| `python manage.py test apps -v 2`                | Tests con output detallado.          |
| `python manage.py spectacular --file schema.yaml`| Exportar OpenAPI YAML.               |

## Troubleshooting

**"Tenant not found" en cualquier request:**
- Verifica que `localStorage.tenant_id` exista. Re-loguéate.
- O revisa que el tenant esté `is_active=True` desde Django Admin.

**400 al hacer signup:**
- Verifica que el code exista, esté activo, no expirado.
- Si es CREATE_TENANT, ¿pasaste tenant_name y tenant_subdomain?
- ¿El subdominio cumple el regex (lowercase, números, guiones)?

**El frontend muestra "Session expired" loop:**
- Se borraron los tokens. Sólo loguéate de nuevo.

**Migraciones inconsistentes:**
- En dev, `rm db.sqlite3 && python manage.py migrate` resetea todo.
- En prod, planea data migrations. NUNCA borres la DB.
