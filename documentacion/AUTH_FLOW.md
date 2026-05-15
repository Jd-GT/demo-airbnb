# Autenticación, Signup e Invitation Codes

Este documento explica el flujo completo de acceso a la plataforma. Es
distinto al de un SaaS self-service típico: **nadie puede crear una cuenta
sin un código emitido por alguien autorizado**.

## 1. Modelo mental: dos tipos de códigos

```
                            ┌──────────────────────────────────┐
                            │    InvitationCode                │
                            │                                  │
                            │   purpose:                       │
                            │   ├── CREATE_TENANT              │
                            │   │   (emite el SUPER-ADMIN)     │
                            │   │   → permite registrar una    │
                            │   │     empresa nueva            │
                            │   │                              │
                            │   └── JOIN_TENANT                │
                            │       (emite el OWNER del tenant)│
                            │       → permite que un MEMBER    │
                            │         se una a esa empresa     │
                            └──────────────────────────────────┘
```

Cada código tiene:

- `code`: 12 chars alfanuméricos auto-generados (uppercase). Editable
  manualmente desde el admin si el usuario quiere uno legible (ej:
  "INMOACME-2026").
- `max_uses`: cuántas veces se puede redimir (default 1).
- `uses_count`: contador atómico. Cuando llega a `max_uses`, el código
  se autodesactiva.
- `expires_at`: fecha límite, opcional.
- `is_active`: el OWNER puede desactivarlo manualmente.
- `notes`: texto libre para auditoría ("Para Carolina recepcionista").
- `created_by`: quién lo emitió.
- Para `JOIN_TENANT`: `tenant` (FK obligatorio) y `role` (opcional, si
  no se especifica el code asigna el rol default del tenant).

## 2. Flujo: alguien quiere abrir una empresa nueva

```
[Persona X quiere crear cuenta para su inmobiliaria]
         │
         ▼
[Contacta al super-admin del SaaS por canal externo (email, Whatsapp...)]
         │
         ▼
[Super-admin entra al Django Admin (/admin/)]
         │
         ├── Va a "Invitation codes" → "Add"
         ├── purpose: CREATE_TENANT
         ├── max_uses: 1
         ├── expires_at: opcional (ej: 7 días)
         └── notes: "Inmobiliaria Acme - lead 23"
         │
         ▼
[Django genera el code (ej: AB12CD34EF56) y se lo envía a Persona X]
         │
         ▼
[Persona X entra a /login en el frontend]
         ├── Click "Tengo un código de invitación"
         ├── Pega el código en "Código de invitación"
         ├── Selecciona "Para abrir una empresa nueva"
         ├── Llena: nombre completo, email, password
         ├── Llena: nombre comercial, subdominio
         └── Submit
         │
         ▼
[POST /api/auth/register/ con invitation_code + tenant_name + tenant_subdomain]
         │
         ▼
[Backend valida:]
         ├── Code existe, está activo, no expirado, no agotado
         ├── purpose == CREATE_TENANT
         ├── Subdominio no está en uso
         ├── Email no está en uso
         │
         ▼
[Backend crea (atómicamente):]
         ├── Tenant (is_active=True)
         ├── 2 roles default: "Admin Total" y "Solo Lectura"
         ├── User OWNER del tenant (is_primary_owner=True)
         └── Code.consume() → uses_count++ → si llega al max, is_active=False
         │
         ▼
[Backend devuelve tokens JWT + datos]
         │
         ▼
[Frontend guarda tokens en localStorage y redirige a /]
```

## 3. Flujo: alguien se une al equipo de una empresa existente

```
[Carolina trabaja en Inmobiliaria Acme y necesita acceso al PMS]
         │
         ▼
[OWNER de Acme entra a /settings]
         ├── Sección "Códigos de Invitación"
         ├── Pone max_uses=1, notes="Carolina"
         └── Click "Generar código"
         │
         ▼
[POST /api/tenants/<id>/invitation-codes/ → returns {code: "XYZ123ABC"}]
         │
         ▼
[OWNER se lo envía a Carolina por Whatsapp]
         │
         ▼
[Carolina entra a /login → "Tengo un código de invitación"]
         ├── Pega el código
         ├── Selecciona "Para entrar a una empresa"
         ├── Llena nombre, email, password
         ├── (Opcional) escribe el subdominio "acme" para confirmar
         └── Submit
         │
         ▼
[Backend valida igual que el caso anterior, pero:]
         ├── purpose == JOIN_TENANT → no se crea tenant nuevo
         ├── Si Carolina puso un subdominio, debe coincidir con el del code
         │
         ▼
[Backend crea User MEMBER con el rol que el code traía (o el default del tenant)]
         │
         ▼
[Carolina queda logueada y entra al PMS de Inmobiliaria Acme]
```

## 4. Flujo de login normal

Estándar JWT con rotación:

1. `POST /api/auth/token/` con `{email, password}` → `{access, refresh}`.
2. Frontend guarda tokens en `localStorage`.
3. Frontend llama `GET /api/me/` → obtiene `{user, tenant, permissions}`.
4. Tenant ID se guarda en `localStorage.tenant_id` y se usa en todas las
   URLs subsecuentes (`/api/tenants/<id>/...`).
5. Si una request da 401, se intenta `/api/auth/token/refresh/`.
6. Si el refresh falla, se hace logout y redirect a `/login`.

`access_token` dura 60 minutos, `refresh_token` 7 días (configurable
en `settings.py:SIMPLE_JWT`).

## 5. Endpoints de signup/auth

| Endpoint                             | Método | Permisos       | Descripción                                       |
| ------------------------------------ | ------ | -------------- | ------------------------------------------------- |
| `/api/auth/register/`                | POST   | AllowAny       | Signup con `invitation_code`. Único punto de entrada. |
| `/api/auth/token/`                   | POST   | AllowAny       | Login. Devuelve JWT.                              |
| `/api/auth/token/refresh/`           | POST   | AllowAny       | Refresh JWT.                                      |
| `/api/me/`                           | GET    | Auth           | User + tenant + permisos del current user.        |
| `/api/tenants/<id>/invitation-codes/`| GET/POST | USERS:admin  | Manejo de codes JOIN_TENANT del tenant.           |

## 6. Cómo emitir códigos

### Como super-admin (emite CREATE_TENANT)

Tres formas:

**a) Django Admin (recomendado para uso manual):**

```
Login en /admin/ con superuser
→ "Invitation codes" → "Add"
   - purpose: CREATE_TENANT
   - leave tenant blank
   - max_uses: 1
   - expires_at: opcional
   - notes: a quién y para qué
→ Save → copy `code`
```

**b) Acción "Generar código" desde el listado:**
En la lista de Invitation codes hay una acción que crea un nuevo
CREATE_TENANT code de un solo uso.

**c) Comando CLI:**

```bash
python manage.py issue_invite_code --notes "Lead Acme" --expires-days 7
# → Code generated: AB12CD34EF56
```

### Como OWNER de un tenant (emite JOIN_TENANT)

Desde el frontend, en `/settings` → "Códigos de Invitación" →
formulario "Generar código".

O por API:

```http
POST /api/tenants/{tenant_id}/invitation-codes/
Authorization: Bearer <jwt>
Content-Type: application/json

{
  "max_uses": 1,
  "notes": "Para Carolina (recepcionista)",
  "expires_at": null,
  "role_id": null
}
```

Si `role_id` es null, el código asigna el rol default del tenant
(`Solo Lectura`). Si se especifica, el nuevo usuario hereda ese rol.

## 7. Seguridad / consideraciones

- Los `code` se almacenan en plaintext (no son secretos de cifrado).
  Su seguridad viene de la longitud y aleatoriedad (12 chars
  alfanuméricos uppercase = ~62^12 = 3.2 * 10^21 combinaciones).
- `consume()` usa `F('uses_count') + 1` y un `update()` atómico para
  evitar race conditions cuando dos usuarios redimen el mismo code al
  mismo tiempo.
- La validación es **case-insensitive** y trimea espacios. El usuario
  puede pegar el código con espacios o lowercase y funciona.
- Si un tenant pasa a `is_active=False`, ningún signup contra él
  funciona y ningún usuario del tenant puede operar (el middleware lo
  bloquea con 404).
- El `OWNER` no se puede desactivar ni degradar — esto previene que
  alguien quede fuera de su propia empresa.

## 8. Cosas que faltan (Sprint 1+)

- [ ] Reset de password (forgot-password flow).
- [ ] Verificación de email al hacer signup.
- [ ] Soft-delete de usuarios (mantener histórico).
- [ ] 2FA opcional para OWNER.
- [ ] Webhooks cuando un code es redimido (para que el super-admin se
      entere por Slack/email).
