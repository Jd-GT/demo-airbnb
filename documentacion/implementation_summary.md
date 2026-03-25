# Sprint 1 - Implementation Summary (Backend)

## Scope implemented
- Base Django + DRF backend architecture with modular apps:
  - `apps/core`
  - `apps/inventory`
  - `apps/crm`
  - `apps/booking`
  - `apps/finance` (placeholder for Sprint 2+)
- Multi-tenant foundation using shared-schema strategy with strict `tenant_id` scoping.
- JWT authentication using `djangorestframework-simplejwt`.
- Tenant-aware base abstractions:
  - `TenantAwareModel`
  - `TenantAwareManager`
  - tenant context middleware (`TenantResolutionMiddleware`)
- IAM/RBAC Sprint 1:
  - `Tenant`
  - `TenantRole` with JSON permissions per module (`none/read/write/admin`)
  - custom `User` model with `system_role` (`OWNER`, `MEMBER`, `CLEANER`)
  - owner invariants: first owner is `is_primary_owner=True`, cannot be downgraded or deactivated
  - backend permission enforcement via `TenantModulePermission` (never frontend-only)
- Automatic tenant seed behavior on tenant creation:
  - default role `Admin Total` with full admin permissions in all modules
  - default role `Solo Lectura` with read permissions in all modules
  - first tenant user created as immutable OWNER

## Sprint 1 APIs implemented
- Roles and users (required paths):
  - `POST /api/tenants/{id}/roles/`
  - `GET/PUT/DELETE /api/tenants/{id}/roles/{role_id}/`
  - `POST /api/tenants/{id}/users/`
  - `PATCH /api/tenants/{id}/users/{user_id}/`
- Inventory CRUD:
  - amenities CRUD
  - properties CRUD (with amenity assignments)
- CRM CRUD:
  - contacts CRUD
  - leads CRUD
- Booking Sprint 1 minimum:
  - reservation base model
  - availability check endpoint
  - reservation creation endpoint
  - quote endpoint with Sprint 1 pricing (`nights * base_price + cleaning_fee`)

## Supporting engineering work
- Django admin registrations for operational visibility.
- OpenAPI enabled via drf-spectacular (`/api/schema/`, Swagger, Redoc).
- Automated tests for critical flows:
  - tenant bootstrap seed
  - owner protection
  - tenant isolation
  - RBAC read/write enforcement
  - booking quote/availability/overbooking

## Verification summary
- Migrations created and applied successfully.
- Test suite executed successfully (`5` tests passing).
- System checks pass with no issues.
