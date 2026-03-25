# Architecture Notes - Sprint 1

## Architectural style
- **Modular monolith** in Django, organized by bounded contexts (`core`, `inventory`, `crm`, `booking`, `finance`).
- **API-first contract** with documented endpoint behavior for frontend integration.
- **Shared-schema multi-tenant** model with strict tenant filtering and permission checks.

## Clean architecture decisions
- Views are kept thin; business rules are moved to services where required:
  - `apps/core/services.py` for tenant bootstrap and user lifecycle safeguards.
  - `apps/booking/services.py` for quote calculation, availability checks, and reservation creation.
- Tenant and RBAC concerns centralized in:
  - `apps/core/permissions.py`
  - `apps/core/constants.py`
  - `apps/core/middleware.py`
- Shared persistence behavior in base classes:
  - `TenantAwareModel`
  - `TenantAwareManager`

## RBAC model
- Permission levels: `none`, `read`, `write`, `admin`.
- Permission modules are centralized enum constants to avoid hardcoded strings across the codebase.
- OWNER bypasses module-level checks.
- MEMBER access depends on `TenantRole.permissions`.
- Permission checks are enforced in backend permission classes for every protected endpoint.

## Tenant isolation strategy
- URL-scoped tenant IDs (`/api/tenants/{tenant_id}/...`) + permission enforcement requiring `request.user.tenant_id == tenant_id`.
- Querysets are tenant-filtered in each viewset.
- Tenant resolution middleware sets request context and manager context for extra safety.

## Sprint boundary decisions
- Implemented only Sprint 1 operational backend.
- `finance` app exists as normalized module placeholder but no domain logic yet.
- Pricing engine intentionally simple for Sprint 1 (`/quote`) and prepared to evolve in Sprint 2 with dynamic rules.
