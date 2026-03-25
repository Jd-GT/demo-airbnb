# Assumptions (Due to Missing or Ambiguous Specs)

1. `README.MD` did not define endpoint naming conventions, so tenant-scoped REST paths were standardized as `/api/tenants/{tenant_id}/{module}/...`.
2. Tenant onboarding endpoint was assumed necessary to satisfy seed requirements; implemented as `POST /api/tenants/` with owner payload.
3. `Amenity` was implemented as tenant-scoped to preserve strict isolation and allow per-tenant catalogs.
4. Reservation dates were implemented as `DateField` (`check_in`, `check_out`) for Sprint 1 simplicity.
5. Sprint 1 quote pricing uses only:
   - nightly subtotal = `nights * property.base_price`
   - total = `subtotal + property.cleaning_fee`
6. Dynamic price rules (`price_rules`), reservation lines, payments, taxes, analytics, and operational tasks were intentionally not implemented because they are outside Sprint 1 scope.
7. `source` on leads was implemented as optional FK to `Contact` to support CRM source traceability with current schema constraints.
8. OpenAPI contract generation uses drf-spectacular and runtime schema endpoints; static file export path is documented and can be regenerated.
