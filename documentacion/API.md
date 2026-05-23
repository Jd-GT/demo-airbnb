# Contrato REST

Base URL en dev: `http://localhost:8000`

> **Sprint 4/5 añadió** los endpoints listados en las secciones **10
> (Operations)** y **11 (Integrations / Hardening)**.

Convenciones:

- Auth: header `Authorization: Bearer <access_token>` salvo donde diga lo contrario.
- Tenant: la mayoría de endpoints viven bajo `/api/tenants/<tenant_id>/...`.
  El `tenant_id` debe coincidir con el del usuario (a menos que sea
  superuser). Los superusers pueden operar sobre cualquier tenant.
- Errores: status HTTP estándar. Body es `{detail: "..."}` o
  `{<field>: ["mensaje"]}`. El frontend extrae el primero.

OpenAPI completo en runtime: `http://localhost:8000/api/schema/swagger/`.

## 1. Auth & onboarding

### `POST /api/auth/register/` — Signup

Permisos: `AllowAny`. Requiere `invitation_code` siempre.

Request (CREATE_TENANT code):
```json
{
  "invitation_code": "AB12CD34EF56",
  "email": "owner@acme.com",
  "full_name": "Owner Acme",
  "password": "supersecret123",
  "tenant_name": "Inmobiliaria Acme",
  "tenant_subdomain": "acme"
}
```

Request (JOIN_TENANT code, subdominio opcional):
```json
{
  "invitation_code": "XYZ123ABC456",
  "email": "carolina@acme.com",
  "full_name": "Carolina Recepcionista",
  "password": "supersecret123"
}
```

Response 201:
```json
{
  "tenant": { "id": "...", "name": "...", "subdomain": "..." },
  "user": { "id": "...", "email": "...", "system_role": "OWNER" },
  "access": "<jwt>",
  "refresh": "<jwt>",
  "message": "Empresa creada exitosamente."
}
```

### `POST /api/auth/token/` — Login

```json
{ "email": "owner@acme.com", "password": "supersecret123" }
```
→ `{ "access": "...", "refresh": "..." }`

### `POST /api/auth/token/refresh/`
```json
{ "refresh": "..." }
```
→ `{ "access": "..." }`

### `GET /api/me/`

Auth requerido.

Response:
```json
{
  "user": {
    "id": "...",
    "email": "...",
    "full_name": "...",
    "system_role": "OWNER" | "MEMBER" | "CLEANER",
    "is_primary_owner": true,
    "role": { "id": "...", "name": "Solo Lectura" } | null,
    "is_active": true
  },
  "tenant": {
    "id": "...",
    "name": "...",
    "subdomain": "...",
    "branding_config": {},
    "integration_config": {},
    "is_active": true
  } | null,
  "permissions": {
    "core": "read", "users": "none", "inventory": "read",
    "crm": "read", "booking": "read", "finance": "none"
  }
}
```

## 2. Tenants

### `GET /api/tenants/`
Lista los tenants visibles al usuario actual. Para usuarios normales
es solo el suyo.

### `GET /api/tenants/<id>/`
Detalle. `integration_config` se devuelve `{}` para no-OWNER.

### `PATCH /api/tenants/<id>/`
Editar nombre, branding_config, integration_config (solo OWNER puede
cambiar `integration_config` realmente). El resto puede cambiar branding
si tiene `core:admin`.

> **Eliminado:** `POST /api/tenants/`. Tenants se crean SOLO vía
> `/api/auth/register/` con un `CREATE_TENANT` code, o desde Django Admin.

## 3. Roles

`/api/tenants/<id>/roles/` — CRUD.

Permission: USERS:read para listar, USERS:write para crear/editar,
USERS:admin para borrar.

Body POST/PUT:
```json
{
  "name": "Editor de Reservas",
  "permissions": {
    "core": "read",
    "users": "none",
    "inventory": "read",
    "crm": "write",
    "booking": "write",
    "finance": "none"
  },
  "is_default": false
}
```

## 4. Users

`/api/tenants/<id>/users/` — Listar y crear.
`/api/tenants/<id>/users/<user_id>/` — Detalle y editar (PATCH).

Permission: USERS:read+. Si no tienes USERS:read usas `/api/me/` para
ver tu propia ficha.

POST (invitar via API directa, sin código):
```json
{
  "email": "nuevo@acme.com",
  "full_name": "Nuevo Usuario",
  "password": "tempPass123",
  "system_role": "MEMBER",
  "role_id": "<uuid del rol>"
}
```

PATCH:
```json
{ "is_active": false }            // desactiva
{ "role_id": "<uuid otro rol>" }  // cambia rol
```

> Notas:
> - El primary OWNER no se puede degradar ni desactivar.
> - Para invitaciones controladas por código, usar el endpoint de
>   `invitation-codes` y compartir el código (recomendado para flujo
>   self-service del MEMBER).

## 5. Invitation codes

`/api/tenants/<id>/invitation-codes/` — Listar y crear.
`/api/tenants/<id>/invitation-codes/<code_id>/` — Detalle y desactivar
(DELETE no borra fila, solo pone `is_active=False`).

Permission: USERS:admin.

POST:
```json
{
  "max_uses": 1,
  "notes": "Para Carolina",
  "expires_at": "2026-06-01T00:00:00Z",
  "role_id": null
}
```

Response 201:
```json
{
  "id": "...",
  "code": "AB12CD34EF56",
  "purpose": "JOIN_TENANT",
  "tenant_subdomain": "acme",
  "role": null,
  "max_uses": 1,
  "uses_count": 0,
  "expires_at": "2026-06-01T00:00:00Z",
  "is_active": true,
  "is_usable": true,
  "is_expired": false,
  "is_exhausted": false,
  "notes": "Para Carolina",
  "created_at": "2026-05-13T..."
}
```

## 6. Inventory

`/api/tenants/<id>/inventory/properties/` — CRUD.
`/api/tenants/<id>/inventory/amenities/` — CRUD.

Permission: INVENTORY:read/write/admin.

GET de properties acepta `?year=2026&month=3` para inyectar
`monthly_revenue` y `occupancy_rate` calculados.

POST property:
```json
{
  "name": "Apto 301",
  "address": "Calle 1 #2-3",
  "capacity_adults": 2,
  "capacity_kids": 1,
  "base_price": "120.00",
  "cleaning_fee": "20.00",
  "amenity_ids": ["<uuid>", "<uuid>"]
}
```

## 7. CRM

`/api/tenants/<id>/crm/contacts/?search=<q>` — CRUD + búsqueda.
`/api/tenants/<id>/crm/leads/` — CRUD.

Contact body (campos extendidos en hotfix 5.5):
```json
{
  "name": "Juan Pérez",
  "email": "juan@correo.com",
  "phone": "+57 300 1234567",
  "type": "GUEST" | "AGENT" | "PLATFORM",
  "commission_rate": "10.00",
  "tax_id": "1234567890",
  "address": "Calle 5 # 6-7",
  "nationality": "CO",
  "notes": "Cliente recurrente, prefiere apto en piso alto"
}
```

`tax_id` debe ser único por tenant cuando no es vacío. `commission_rate`
solo aplica a `AGENT` (se fuerza a 0 para otros tipos).

### Stats por contacto (hotfix 5.5)

`GET /api/tenants/<id>/crm/contacts/<contact_id>/stats/`

```json
{
  "contact_id": "<uuid>",
  "reservations_count": 5,
  "confirmed_reservations_count": 4,
  "cancelled_reservations_count": 1,
  "total_billed": "1200.00",
  "total_lodging_paid": "950.00",
  "total_extras_paid": "120.00",
  "total_refunded": "0.00",
  "outstanding_balance": "250.00",
  "first_check_in": "2026-01-12",
  "last_check_out": "2026-09-04",
  "nights_total": 32
}
```

Suma sobre todas las reservas donde el contacto figura como `guest`.

## 8. Booking

`/api/tenants/<id>/booking/quote/` — POST cotización (no reserva).
```json
{ "property_id": "...", "check_in": "2026-06-01", "check_out": "2026-06-05" }
```
Response: `{nights, nightly_rate, subtotal_amount, cleaning_fee, total_amount}`.

`/api/tenants/<id>/booking/reservations/availability/` — POST
verificación de overlap.
Response: `{available: bool, conflicting_reservation_ids: [...]}`.

`/api/tenants/<id>/booking/reservations/` — Listar y crear (NO update).
Acepta `?from=YYYY-MM-DD&to=YYYY-MM-DD` para filtrar por fecha.

POST reservation:
```json
{
  "property_id": "...",
  "guest_id": "...",
  "agent_id": null,
  "check_in": "2026-06-01",
  "check_out": "2026-06-05",
  "status": "CONFIRMED"
}
```

**`guest_id` puede apuntar a:**
- `Contact.type=GUEST` — el huésped real (caso típico).
- `Contact.type=PLATFORM` — para registrar reservas que vienen de
  Airbnb / Booking / Expedia cuando aún no tienes datos del huésped
  real. Crea un Contact "Airbnb" tipo PLATFORM una vez y reutilízalo
  en cada reserva externa.

**No se acepta** `Contact.type=AGENT` como guest — los agentes /
comisionistas van en `agent_id` para que se calcule la comisión.

## 9. Finance

### Analytics legacy

`GET /api/tenants/<id>/finance/analytics/?year=2026&month=3`

Response:
```json
{
  "monthly_revenue_total": "12500.00",
  "annual_revenue_total": "98000.00",
  "monthly_revenue_series": [{"month": "Ene", "ingresos": "8000.00"}, ...],
  "revenue_by_property": [{"name": "Apto 301", "ingresos": "5000.00"}, ...]
}
```

### Taxes (Sprint 2)

`/api/tenants/<id>/finance/taxes/` — CRUD.

Body:
```json
{ "name": "IVA 19%", "value": "0.19", "type": "PERCENT", "is_active": true }
```

`type`: `PERCENT` (value es fracción 0.19) o `FIXED` (value es monto plano).

### Cost Centers (Sprint 3)

`/api/tenants/<id>/finance/cost-centers/` — list/create/retrieve/update.

Cada `Property` genera el suyo automáticamente. Devuelve `balance` calculado.

### Analytic Lines (Sprint 3)

`GET /api/tenants/<id>/finance/analytic-lines/?account_id=&from=&to=`

Lectura solo. Para crear gastos use `/finance/expenses/`.

### Expenses (Sprint 3)

`POST /api/tenants/<id>/finance/expenses/`

```json
{
  "account_id": "<uuid cost center>",
  "date": "2026-06-10",
  "amount": "120.00",
  "category": "MAINTENANCE",
  "description": "Cambio de cerradura"
}
```

`category` debe ser una de: `CLEANING_COST`, `MAINTENANCE`, `UTILITIES`,
`COMMISSION`, `OTHER_EXPENSE`. Internamente se almacena como
`AnalyticLine.amount` negativo.

### Payments (Sprint 3 + Hotfix 5.5)

`/api/tenants/<id>/finance/payments/` — list/create/retrieve/destroy
(`?reservation_id=` opcional para filtrar).

POST:
```json
{
  "reservation_id": "<uuid>",
  "date": "2026-07-01",
  "amount": "200.00",
  "type": "ADVANCE" | "BALANCE" | "EXTRA" | "REFUND",
  "method": "CASH" | "TRANSFER" | "OTHER",
  "reference": "consignación-9182",
  "notes": ""
}
```

**Validación de tipo (hotfix 5.5):**
- `ADVANCE` y `BALANCE` cuentan contra el saldo de **alojamiento**.
  Cualquier intento que haga `amount_paid > total_amount` se rechaza
  con `400 {amount: "el monto excede el saldo pendiente ($X)..."}`.
- `EXTRA` no tiene tope. Cuenta en `Reservation.extras_received`.
  Úsalo para daños, servicios extra, late fees.
- `REFUND` no puede exceder `amount_paid`.

Cada response de `Payment` incluye `is_lodging: bool` para que el
frontend pueda categorizar sin recalcular.

Tras crear/borrar se recalculan en `Reservation`:
- `amount_paid` = sum(ADVANCE+BALANCE) − sum(REFUND)
- `extras_received` = sum(EXTRA)
- `payment_status` ∈ PENDING / PARTIAL / PAID / OVERPAID

> **No hay pasarela de pagos.** El dinero ya pasó por fuera (Whatsapp,
> banco, efectivo). Aquí sólo se *registra* lo ocurrido.

### P&L (Sprint 3)

`GET /api/tenants/<id>/finance/profit-and-loss/?account_id=&from_date=&to_date=`

Response:
```json
{
  "income": "1200.00",
  "expenses": "-380.00",
  "net": "820.00",
  "by_category": {
    "INCOME": "1200.00",
    "MAINTENANCE": "-180.00",
    "UTILITIES": "-200.00"
  }
}
```

### Reportes Excel (Sprint 3)

Devuelven `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`
con `Content-Disposition: attachment`.

- `GET /api/tenants/<id>/finance/reports/pnl.xlsx?year=2026`
- `GET /api/tenants/<id>/finance/reports/occupancy.xlsx?year=2026`
- `GET /api/tenants/<id>/finance/reports/payments.xlsx?from=&to=`

## 9b. Booking — Price Rules (Sprint 2)

`/api/tenants/<id>/booking/price-rules/` — CRUD.

Body POST:
```json
{
  "name": "Temporada Alta Navidad",
  "start_date": "2026-12-15",
  "end_date": "2027-01-10",
  "is_percent": true,
  "modifier": "1.50",
  "min_nights": 3,
  "priority": 50,
  "property_ids": [],
  "is_active": true
}
```

Reglas:

- `is_percent=true` → `modifier` es multiplicador del `base_price` (1.50 = +50%).
- `is_percent=false` → `modifier` es la tarifa nocturna fija que reemplaza al base.
- `priority` desempata cuando se solapan reglas — gana la más alta.
- `property_ids=[]` ⇒ aplica a todas; lista no vacía ⇒ scope acotado.
- `min_nights` rechaza la cotización si la estancia no alcanza.

`POST /api/tenants/<id>/booking/quote/` ahora devuelve además:

```json
{
  ...campos previos...,
  "nights_breakdown": [{"date": "...", "rate": "120.00", "rule": "Temporada Alta"}],
  "applied_rule_names": ["Temporada Alta"],
  "min_nights_required": 3
}
```

## 9c. Booking — Reservation Lines (Sprint 2)

Las líneas se crean automáticamente al crear la reserva (1 línea NIGHT
por todas las noches + 1 FEE por la limpieza si > 0). Por ahora se
exponen como anidadas en la respuesta de `Reservation` (`lines`):

```json
{
  "id": "...", "type": "NIGHT", "description": "3 noche(s) — Apto 301 (tarifa base)",
  "quantity": "3.00", "unit_price": "120.00",
  "taxes": [], "tax_ids": [],
  "line_subtotal": "360.00", "line_tax_total": "0.00"
}
```

CRUD propio del modelo se añadirá cuando se construya la UI de edición
detallada de líneas.

## 10. Integrations

`/api/tenants/<id>/integrations/` — GET. Lista normalizada de las
integraciones del tenant. Sólo Google Calendar por defecto.

Response:
```json
[
  {
    "id": "google_calendar",
    "name": "Google Calendar",
    "description": "...",
    "status": "pending" | "connected" | "error",
    "icon": "📅",
    "color": "#4285F4",
    "last_sync": null,
    "details": "Conecta tu cuenta..."
  }
]
```

## 10. Operations (Sprint 4)

### Tasks

`/api/tenants/<id>/ops/tasks/` — list/create/retrieve/update/destroy.
`POST /api/tenants/<id>/ops/tasks/<task_id>/complete/` — atajo: setea
status=DONE y completed_at.

Filtros (querystring): `status`, `assigned_to_me=1`, `due_from`, `due_to`.

Body POST:
```json
{
  "property": "<uuid>",
  "type": "CLEANING" | "MAINTENANCE" | "INSPECTION" | "OTHER",
  "title": "Limpieza post check-out — Apto 301",
  "due_date": "2026-07-04",
  "notes": "Llaves en recepción",
  "assigned_to": "<user uuid>" | null
}
```

Permisos: requiere `booking` module. Usuarios con `system_role=CLEANER`
pasan automáticamente, pero sólo ven y pueden completar tareas
asignadas a ellos.

### Message Templates

`/api/tenants/<id>/ops/templates/` — CRUD.

Body:
```json
{
  "name": "Confirmación check-in",
  "channel": "WHATSAPP" | "EMAIL" | "INTERNAL",
  "subject": "Reserva confirmada — {{property_name}}",
  "body": "Hola {{guest_name}}, confirmamos tu reserva en {{property_name}}…",
  "is_active": true
}
```

Placeholders soportados:
`{{guest_name}}`, `{{property_name}}`, `{{property_address}}`,
`{{check_in}}`, `{{check_out}}`, `{{nights}}`, `{{total_amount}}`,
`{{balance_due}}`, `{{amount_paid}}`, `{{reservation_id}}`,
`{{tenant_name}}`.

### Render message for reservation

`POST /api/tenants/<id>/ops/render-message/`
```json
{ "template_id": "<uuid>", "reservation_id": "<uuid>" }
```
→ `{ "channel": "...", "subject": "...", "body": "..." }`

NO envía nada; el frontend usa wa.me / mailto / clipboard.

### Voucher PDF

`GET /api/tenants/<id>/ops/voucher/<reservation_id>.pdf`

Devuelve `application/pdf` con `Content-Disposition: attachment`. A4 con
detalles de la reserva, líneas, totales y saldo.

## 11. Integrations + Hardening (Sprint 5)

### Healthcheck

`GET /healthz` (sin auth)
→ `{"status": "ok"|"degraded", "db": true|false}` (200/503).

### Google Calendar credential

`GET /api/tenants/<id>/integrations/google-calendar/`
→ `{configured: false, message: "..."}` o el objeto completo (sin token).

`PUT /api/tenants/<id>/integrations/google-calendar/`
```json
{
  "calendar_id": "primary",
  "is_active": true,
  "refresh_token": "<plaintext refresh token>"
}
```
El `refresh_token` se cifra con Fernet al guardar y nunca se devuelve
en respuestas.

`DELETE /api/tenants/<id>/integrations/google-calendar/` — elimina la
credencial.

`POST /api/tenants/<id>/integrations/google-calendar/sync/<reservation_id>/`
→ `{status: "not_configured"|"stub_ok", reservation_id, calendar_id?}`.
Hoy es un stub; cuando se implemente el sync real, sólo cambia el cuerpo
del adapter en `apps/core/integrations.py`.

Permisos: el GET/PUT/DELETE requiere `users:admin`. El sync requiere
`booking:write`.

### Rate limiting

- `POST /api/auth/token/`: 10 intentos/min/IP. Excede → 429.
- `POST /api/auth/register/`: 5 intentos/h/IP. Excede → 429.
- Override: `RATELIMIT_ENABLE=False` (auto-off durante tests).

### Auditoría (django-simple-history)

Modelos con historial: `Tenant`, `TenantRole`, `User`, `InvitationCode`,
`Reservation`, `Payment`. Cada cambio crea una fila en `historical*`
con timestamp, tipo de cambio (`+ ~ -`) y `history_user` (capturado
automáticamente por el middleware).

Aún sin endpoint REST público — consultar desde Django Admin (sección
"Historical ..." de cada modelo) o queries puntuales:
```python
from apps.booking.models import Reservation
res = Reservation.objects.get(id=...)
for h in res.history.all():
    print(h.history_date, h.history_type, h.status, h.amount_paid)
```

## 12. Errores comunes

| Status | Cuándo                                                              |
| ------ | ------------------------------------------------------------------- |
| 400    | Validación: campo faltante, código inválido, subdominio en uso, etc. |
| 401    | Token expirado o ausente. Frontend hace refresh automático.          |
| 403    | Permisos insuficientes (RBAC) o intentando operar en otro tenant.    |
| 404    | Tenant no existe O está inactivo (middleware).                       |
| 405    | Endpoint deprecated (ej: POST /api/tenants/).                        |
