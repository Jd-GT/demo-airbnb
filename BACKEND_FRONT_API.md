# BACKEND_FRONT_API - Sprint 1 Contract

## Base
- Base URL: `/api`
- Auth: JWT Bearer (`Authorization: Bearer <access_token>`)
- Content-Type: `application/json`
- Tenant scope: Most endpoints require `tenant_id` in URL.

## Auth Endpoints

### POST `/api/auth/token/`
Request:
```json
{
  "email": "owner@tenant.com",
  "password": "ownerpass123"
}
```
Response `200`:
```json
{
  "access": "<jwt-access>",
  "refresh": "<jwt-refresh>"
}
```

### POST `/api/auth/token/refresh/`
Request:
```json
{
  "refresh": "<jwt-refresh>"
}
```
Response `200`:
```json
{
  "access": "<new-jwt-access>"
}
```

## Tenant Bootstrap

### POST `/api/tenants/`
Creates tenant + default roles + first OWNER.

Request:
```json
{
  "name": "Caribe Rentals",
  "subdomain": "caribe",
  "owner_email": "owner@caribe.com",
  "owner_full_name": "Main Owner",
  "owner_password": "strongpass123",
  "branding_config": {"primary_color": "#006d77"},
  "integration_config": {}
}
```
Response `201`:
```json
{
  "id": "uuid",
  "name": "Caribe Rentals",
  "subdomain": "caribe",
  "branding_config": {"primary_color": "#006d77"},
  "integration_config": {},
  "is_active": true,
  "created_at": "2026-03-11T00:00:00Z",
  "updated_at": "2026-03-11T00:00:00Z",
  "owner": {
    "id": "uuid",
    "email": "owner@caribe.com",
    "full_name": "Main Owner",
    "system_role": "OWNER"
  }
}
```

## Roles and Users (US-1.1.1)

Permission module: `users`
- read endpoints: `read+`
- create/update/delete endpoints: `write+`
- OWNER: always allowed

### POST `/api/tenants/{tenant_id}/roles/`
Request:
```json
{
  "name": "Editor Reservas",
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
Response `201`: role object.

### GET `/api/tenants/{tenant_id}/roles/{role_id}/`
Response `200`: role object.

### PUT `/api/tenants/{tenant_id}/roles/{role_id}/`
Full replacement with same shape as create.

### DELETE `/api/tenants/{tenant_id}/roles/{role_id}/`
Response `204` empty body.

### POST `/api/tenants/{tenant_id}/users/`
Request:
```json
{
  "email": "agent@caribe.com",
  "full_name": "Agent User",
  "password": "agentpass123",
  "system_role": "MEMBER",
  "role_id": "uuid"
}
```
Response `201`: user object.

### PATCH `/api/tenants/{tenant_id}/users/{user_id}/`
Request example:
```json
{
  "role_id": "uuid",
  "is_active": true
}
```
Response `200`: user object.

Owner protection rule:
- primary OWNER cannot be deactivated (`is_active=false`) or downgraded to non-OWNER.

## Inventory

Permission module: `inventory`

### Properties
- `GET /api/tenants/{tenant_id}/inventory/properties/`
- `POST /api/tenants/{tenant_id}/inventory/properties/`
- `GET /api/tenants/{tenant_id}/inventory/properties/{property_id}/`
- `PUT/PATCH /api/tenants/{tenant_id}/inventory/properties/{property_id}/`
- `DELETE /api/tenants/{tenant_id}/inventory/properties/{property_id}/`

Create request example:
```json
{
  "name": "Apto 301",
  "address": "Calle 1 #2-3",
  "capacity_adults": 4,
  "capacity_kids": 2,
  "base_price": "180.00",
  "cleaning_fee": "45.00",
  "amenity_ids": ["uuid", "uuid"]
}
```

### Amenities
- `GET /api/tenants/{tenant_id}/inventory/amenities/`
- `POST /api/tenants/{tenant_id}/inventory/amenities/`
- `GET /api/tenants/{tenant_id}/inventory/amenities/{amenity_id}/`
- `PUT/PATCH /api/tenants/{tenant_id}/inventory/amenities/{amenity_id}/`
- `DELETE /api/tenants/{tenant_id}/inventory/amenities/{amenity_id}/`

Amenity request example:
```json
{
  "name": "WiFi",
  "icon_key": "fa-wifi"
}
```

## CRM

Permission module: `crm`

### Contacts
- `GET /api/tenants/{tenant_id}/crm/contacts/?search=<text>`
- `POST /api/tenants/{tenant_id}/crm/contacts/`
- `GET /api/tenants/{tenant_id}/crm/contacts/{contact_id}/`
- `PUT/PATCH /api/tenants/{tenant_id}/crm/contacts/{contact_id}/`
- `DELETE /api/tenants/{tenant_id}/crm/contacts/{contact_id}/`

Contact request example:
```json
{
  "name": "Juan Perez",
  "email": "juan@example.com",
  "phone": "+573001112233",
  "type": "GUEST",
  "commission_rate": "0.00"
}
```

### Leads
- `GET /api/tenants/{tenant_id}/crm/leads/`
- `POST /api/tenants/{tenant_id}/crm/leads/`
- `GET /api/tenants/{tenant_id}/crm/leads/{lead_id}/`
- `PUT/PATCH /api/tenants/{tenant_id}/crm/leads/{lead_id}/`
- `DELETE /api/tenants/{tenant_id}/crm/leads/{lead_id}/`

Lead request example:
```json
{
  "contact": "uuid",
  "source": "uuid",
  "stage": "NEW",
  "desired_check_in": "2026-04-10",
  "desired_check_out": "2026-04-15",
  "expected_revenue": "900.00",
  "notes": "Pregunta por descuento"
}
```

## Booking (Sprint 1)

Permission module: `booking`

### POST `/api/tenants/{tenant_id}/booking/quote/`
Permission level: `read+`

Request:
```json
{
  "property_id": "uuid",
  "check_in": "2026-04-01",
  "check_out": "2026-04-04"
}
```
Response `200`:
```json
{
  "property_id": "uuid",
  "check_in": "2026-04-01",
  "check_out": "2026-04-04",
  "nights": 3,
  "nightly_rate": "200.00",
  "subtotal_amount": "600.00",
  "cleaning_fee": "50.00",
  "total_amount": "650.00"
}
```

### POST `/api/tenants/{tenant_id}/booking/reservations/availability/`
Permission level: `read+`

Request:
```json
{
  "property_id": "uuid",
  "check_in": "2026-04-01",
  "check_out": "2026-04-04"
}
```
Response `200`:
```json
{
  "available": false,
  "conflicting_reservation_ids": ["uuid"],
  "property_id": "uuid"
}
```

### POST `/api/tenants/{tenant_id}/booking/reservations/`
Permission level: `write+`

Request:
```json
{
  "property_id": "uuid",
  "guest_id": "uuid",
  "agent_id": "uuid",
  "check_in": "2026-04-01",
  "check_out": "2026-04-04",
  "status": "CONFIRMED"
}
```
Response `201`:
```json
{
  "id": "uuid",
  "property": "uuid",
  "guest": "uuid",
  "agent": "uuid",
  "check_in": "2026-04-01",
  "check_out": "2026-04-04",
  "nights": 3,
  "subtotal_amount": "600.00",
  "cleaning_fee": "50.00",
  "total_amount": "650.00",
  "status": "CONFIRMED",
  "created_at": "2026-03-11T00:00:00Z",
  "updated_at": "2026-03-11T00:00:00Z"
}
```

### GET `/api/tenants/{tenant_id}/booking/reservations/`
### GET `/api/tenants/{tenant_id}/booking/reservations/{reservation_id}/`
Permission level: `read+`

## Common Validation Errors

### `400 Bad Request`
Example:
```json
{
  "check_out": ["check_out must be after check_in."]
}
```

### `403 Forbidden`
Example:
```json
{
  "detail": "You do not have permission to perform this action."
}
```

### `404 Not Found`
Returned when tenant-scoped object does not exist in requested tenant.

## Frontend Integration Notes
- Always scope requests using the authenticated user tenant route (`/api/tenants/{tenant_id}/...`).
- Do not send tenant IDs from user-editable UI state without server-side confirmation.
- Use JWT refresh flow proactively when receiving `401`.
- For booking flow:
  1. call `/booking/quote/`
  2. call `/booking/reservations/availability/`
  3. call `/booking/reservations/` only if available
- Treat role permissions as backend authority; hide UI actions, but always expect backend to enforce final decision.

## OpenAPI
- Runtime schema: `/api/schema/`
- Swagger UI: `/api/schema/swagger/`
- Redoc: `/api/schema/redoc/`
