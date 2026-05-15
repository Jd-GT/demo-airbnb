# Estado del Proyecto — Qué hay y qué falta

> **Última actualización:** 2026-05-15 (hotfix 5.6 — reservas externas + CRM hardening).
>
> Esta es la fuente de verdad para saber qué está construido. Si vas a
> codear algo, valida aquí primero — y actualiza esta tabla cuando
> termines tu trabajo.

## Resumen ejecutivo

- ✅ Sprint 0 (acceso controlado, RBAC, privacidad, limpieza de mocks): **COMPLETO**.
- ✅ Sprint 1 (CRUD backend de propiedades, reservas, CRM, analytics): **COMPLETO**.
- ✅ Sprint 2 backend (motor de tarifas, líneas de reserva, comisiones, taxes): **COMPLETO**. UI de calendario drag&drop + sync Google Calendar real **PENDIENTES**.
- ✅ Sprint 3 backend + frontend (pagos manuales, contabilidad analítica, P&L, Excel): **COMPLETO**.
- ✅ Sprint 4 (tareas, vista CLEANER, plantillas, voucher PDF, esqueleto Google Calendar): **COMPLETO**.
- ✅ Sprint 5 (Fernet crypto, django-simple-history, rate limit, healthcheck): **COMPLETO**. Despliegue cloud real **PENDIENTE** (guía en `DEPLOYMENT.md`).

**Tests**: **71 verdes** (66 + 5 hotfix 5.6: contact dedup x3, platform-as-guest x2).

---

## Backend Django (`demoairbnb/`)

### App `ops` (NUEVA en Sprint 4)

| Feature                                                | Estado | Notas                                                                                |
| ------------------------------------------------------ | ------ | ------------------------------------------------------------------------------------ |
| Modelo `Task` (CLEANING/MAINTENANCE/INSPECTION/OTHER)  | ✅     | Status PENDING/IN_PROGRESS/DONE/CANCELLED. CRUD completo + acción `/complete/`.       |
| Auto-creación tarea limpieza al crear reserva          | ✅     | Idempotente. Vence el día de check-out.                                              |
| `_OpsTaskPermission` + queryset filter                 | ✅     | CLEANER ve sólo sus tareas y sólo puede setear IN_PROGRESS/DONE.                     |
| Modelo `MessageTemplate` (WHATSAPP/EMAIL/INTERNAL)     | ✅     | Placeholders renderizados server-side. CRUD completo.                                 |
| `POST /ops/render-message/`                            | ✅     | Devuelve `{channel, subject, body}`. NO envía nada — copy/paste del frontend.        |
| `GET /ops/voucher/{id}.pdf`                            | ✅     | reportlab. A4 con líneas + totales + saldo.                                           |

### App `core`

| Feature                                            | Estado | Notas                                                                                  |
| -------------------------------------------------- | ------ | -------------------------------------------------------------------------------------- |
| Modelo `Tenant` con `is_active`                    | ✅     | Multi-tenant base.                                                                     |
| Modelo `TenantRole` con permisos JSON              | ✅     | RBAC granular por módulo.                                                              |
| Modelo `User` con `system_role` (OWNER/MEMBER/CLEANER) | ✅ | OWNER no se puede degradar ni desactivar.                                              |
| Modelo `InvitationCode` (CREATE_TENANT / JOIN_TENANT) | ✅  | Con `max_uses`, `expires_at`, `consume()` atómico.                                     |
| `TenantResolutionMiddleware` + `contextvars`       | ✅     | Resuelve tenant por header `X-Tenant-ID` o subdominio. Bloquea tenants inactivos.      |
| `TenantAwareManager`                               | ✅     | Filtro automático por tenant en queryset.                                              |
| `TenantModulePermission`                           | ✅     | Enforcement RBAC por endpoint.                                                          |
| Endpoint `POST /api/auth/register/`                | ✅     | Requiere `invitation_code` SIEMPRE. Ver `AUTH_FLOW.md`.                                |
| Endpoint `GET /api/me/`                            | ✅     | Usuario actual + tenant + permisos resueltos.                                          |
| Endpoint `GET/PATCH /api/tenants/{id}/`            | ✅     | `integration_config` se oculta a no-OWNER.                                             |
| Endpoint `POST /api/tenants/`                      | ❌ ELIMINADO | Antes era público, ahora no existe. Tenants se crean vía signup con código o admin. |
| Endpoint `/tenants/{id}/users/`                    | ✅     | Requiere USERS:read+. Sin esto el MEMBER ya no se entera de otros usuarios.            |
| Endpoint `/tenants/{id}/roles/`                    | ✅     | CRUD de roles con permisos.                                                            |
| Endpoint `/tenants/{id}/invitation-codes/`         | ✅     | Solo OWNER/USERS:admin. Crear, listar, desactivar.                                     |
| Endpoint `/tenants/{id}/integrations/`             | ✅     | Solo Google Calendar como placeholder real.                                            |
| Comando `manage.py issue_invite_code`              | ✅     | CLI para super-admin.                                                                  |
| Django Admin para `Tenant`, `InvitationCode`, `User` | ✅   | Acciones: activar/desactivar tenant, generar código, ver vencimientos.                  |
| Endpoint `GET /healthz`                            | ✅     | Sprint 5. Sin auth. Liveness + DB readiness.                                           |
| Rate limit en `/auth/token/` (10/min/IP)           | ✅     | Sprint 5. django-ratelimit. Auto-off durante tests.                                    |
| Rate limit en `/auth/register/` (5/h/IP)           | ✅     | Sprint 5.                                                                              |
| `apps/core/crypto.py` — Fernet helper              | ✅     | Sprint 5. `encrypt_secret/decrypt_secret`. Fallback dev.                               |
| `apps/core/integrations.py` — GoogleCalendar adapter | ✅   | Sprint 4. Modelo de credencial cifrada + adapter stub. Endpoints PUT/DELETE/sync.      |
| `django-simple-history` en Tenant/Role/User/Invitation/Reservation/Payment | ✅ | Sprint 5. Tablas `historical*` automáticas + middleware. Auditoría visible en admin. |

### App `inventory`

| Feature                          | Estado | Notas                                                                                |
| -------------------------------- | ------ | ------------------------------------------------------------------------------------ |
| Modelos `Property`, `Amenity`    | ✅     |                                                                                      |
| CRUD `properties` / `amenities`  | ✅     | Con cálculo de `monthly_revenue` y `occupancy_rate` on-the-fly.                      |
| `cost_center_id` (centro costo)  | ❌     | Falta el FK a `AnalyticAccount`. Sprint 3.                                            |
| Subida de fotos / metadata visual | ❌    | Frontend usa fallback hardcoded.                                                     |

### App `crm`

| Feature                          | Estado | Notas                                                                                |
| -------------------------------- | ------ | ------------------------------------------------------------------------------------ |
| Modelos `Contact`, `Lead`        | ✅     | `Contact.type` ∈ {GUEST, AGENT, PLATFORM}. `Lead.stage` ∈ {NEW, QUOTED, WON, LOST}. |
| **Contact con tax_id, address, nationality, notes** | ✅ | Hotfix 5.5. tax_id único por tenant cuando no es vacío.                                |
| CRUD `contacts` con search       | ✅     | Buscador por name/email/phone.                                                       |
| CRUD `leads`                     | ✅     |                                                                                      |
| **`GET /crm/contacts/<id>/stats/`** | ✅ | Hotfix 5.5. Reservas, noches, facturado, pagado lodging, pagado extras, saldo.           |
| Conversión Lead → Reservation    | ❌     | Sprint 2 frontend.                                                                   |

### App `booking`

| Feature                                                | Estado | Notas                                                                                |
| ------------------------------------------------------ | ------ | ------------------------------------------------------------------------------------ |
| Modelo `Reservation` (DRAFT/CONFIRMED/CHECKED_IN/CHECKED_OUT/CANCELLED) | ✅ | Status extendido en Sprint 2.                                              |
| Campos `tax_total`, `amount_paid`, `agent_commission`, `payment_status` | ✅ | Cache calculado para evitar agregaciones constantes.                       |
| `POST /booking/quote/`                                 | ✅     | Considera ahora reglas de precio dinámicas y rechaza si min_nights no cumple.        |
| `POST /booking/reservations/availability/`             | ✅     | Detecta overlaps.                                                                    |
| `POST /booking/reservations/`                          | ✅     | Crea reserva, calcula comisión, auto-genera líneas, devenga ingreso.                 |
| Modelo `ReservationLine` (líneas de cobro)             | ✅     | NIGHT/FEE/EXTRA/DISCOUNT con M2M a Tax. Auto-generadas al crear reserva.             |
| Modelo `PriceRule` (tarifas dinámicas)                 | ✅     | Por noche, con priority y especificidad. CRUD `/booking/price-rules/`.               |
| Comisiones de agente                                   | ✅     | Cálculo automático sobre subtotal × `agent.commission_rate`.                          |
| Sync con Google Calendar                               | ❌     | Sprint 4.                                                                            |

### App `finance`

| Feature                                | Estado | Notas                                                                                |
| -------------------------------------- | ------ | ------------------------------------------------------------------------------------ |
| `GET /finance/analytics/?year=&month=` | ✅     | Revenue + ADR por propiedad y mes.                                                   |
| Modelo `Tax` (PERCENT/FIXED) + CRUD    | ✅     | `/finance/taxes/`. Aplicable a líneas de reserva.                                    |
| Modelos `AnalyticAccount`, `AnalyticLine` | ✅  | Cost center auto-creado al crear Property. Categorías INCOME/CLEANING/MAINT/etc.     |
| `POST /finance/expenses/`              | ✅     | Registra gasto manual como AnalyticLine negativa.                                    |
| Modelo `Payment` (manual)              | ✅     | CASH/TRANSFER/OTHER, tipos ADVANCE/BALANCE/EXTRA/REFUND. Recalcula `payment_status`. |
| **Validación overpayment lodging**     | ✅     | Hotfix 5.5. Lodging no excede balance. EXTRA sin tope. REFUND ≤ amount_paid.          |
| **`Reservation.extras_received`**       | ✅     | Hotfix 5.5. Cache de pagos EXTRA, no afecta balance_due.                              |
| `GET /finance/profit-and-loss/`        | ✅     | income/expenses/net + by_category. Filtros por cuenta y rango de fechas.             |
| Export Excel (xlsx)                    | ✅     | `/finance/reports/pnl.xlsx`, `occupancy.xlsx`, `payments.xlsx` con openpyxl.         |
| Export PDF (voucher reserva)           | ❌     | Sprint 4. WeasyPrint.                                                                |
| ADR / RevPAR explícito en endpoint     | 🟡     | ADR calculado en `get_property_month_metrics`, falta exponerlo en analytics global.  |

### Tests (`apps/*/tests/`)

| Suite                                          | Estado | Cobertura                                                                              |
| ---------------------------------------------- | ------ | -------------------------------------------------------------------------------------- |
| `core/tests/test_core_flows.py`                | ✅     | Bootstrap tenant, OWNER protection, isolation, RBAC.                                   |
| `core/tests/test_auth_registration.py`         | ✅     | Signup con código JOIN, mismatch subdominio, código inválido, código tipo equivocado. |
| `core/tests/test_invitation_codes_api.py`      | ✅     | CRUD de códigos, permisos, cross-tenant.                                               |
| `core/tests/test_privacy.py`                   | ✅     | Solo Lectura sin USERS, MEMBER vía `/me/`, integration_config oculto.                  |
| `core/tests/test_integrations_api.py`          | ✅     | Solo Google Calendar, integraciones custom.                                            |
| `inventory/tests/test_property_metrics.py`     | ✅     | Calcula occupancy/revenue.                                                             |
| `booking/tests/test_booking_flows.py`          | ✅     | Quote + availability + create + reject overlap.                                        |
| `booking/tests/test_reservation_filters.py`    | ✅     | Filtros por fecha.                                                                     |
| `finance/tests/test_finance_analytics.py`      | ✅     | Cálculos de revenue.                                                                   |
| **Total**                                      |        | 28 tests verdes (a 2026-05-13).                                                        |

---

## Frontend Next.js (`frontend/demo-airbnb/`)

### Páginas

| Ruta              | Estado    | Notas                                                                                  |
| ----------------- | --------- | -------------------------------------------------------------------------------------- |
| `/login`          | ✅        | Sprint 0. Código primero, helper textual del subdominio.                                |
| `/` (Dashboard)   | ✅        | KPIs, gráficos. Algunos números son fallback (gastos antes hardcoded).                  |
| `/propiedades`    | 🟡 lectura | CRUD pendiente.                                                                        |
| `/calendario`     | ✅        | Modal "+ Nueva reserva" (acepta huéspedes y plataformas). Drag & drop pendiente.        |
| `/reservas`       | ✅ NUEVO  | Hotfix 5.6. Tabla completa con filtros (estado, pago, ventana de tiempo, búsqueda) y crear. |
| `/finanzas`       | 🟡        | Mantiene el dashboard antiguo. Para registrar gastos reales usa `/contabilidad`.       |
| `/pagos`          | ✅ MEJORADO | Hotfix 5.5. KPIs separados (alojamiento/extras/reembolsos), panel de balance vivo por reserva, validación overpayment client-side, sugerencia automática de tipo. |
| `/clientes`       | ✅ NUEVO  | Hotfix 5.5. Mini-CRM. Listado + filtros + detalle + edit + reporte por cliente (reservas, noches, facturado, pagado, saldo). |
| `/contabilidad`   | ✅ NUEVO  | Sprint 3. P&L por cost center, gastos manuales, descarga Excel P&L y Ocupación.         |
| `/tareas`         | ✅ NUEVO  | Sprint 4. Listado, KPIs, filtro de estado, crear tarea manual, marcar hecha. CLEANER ve sólo las suyas. |
| `/plantillas`     | ✅ NUEVO  | Sprint 4. Editor con paleta de placeholders, renderizador por reserva, copy-to-clipboard, descarga voucher PDF. |
| `/integraciones`  | ✅ AMPL.  | Sprint 4. Panel "Configurar Google Calendar" para guardar refresh_token cifrado (sólo `users:admin`). |
| `/settings`       | ✅        | Sprint 0. Panel invitation codes + equipo, gating por permisos.                         |

### Helpers/Infra

| Componente                            | Estado | Notas                                                                                  |
| ------------------------------------- | ------ | -------------------------------------------------------------------------------------- |
| `lib/api.ts`                          | ✅ NUEVO | Reescrito en Sprint 0: `register()` único, `fetchCurrentUser()`, helpers de invitación. |
| `components/auth-provider.tsx`        | ✅ NUEVO | Carga `/api/me/`, expone `me`, `permissions`, helper `can(module, level)`.            |
| `components/app-shell.tsx`            | ✅      | Sidebar + nav.                                                                         |
| `components/page-feedback.tsx`        | ✅      | LoadingCard / ErrorCard / EmptyCard.                                                   |
| `hooks/use-async-data.ts`             | ✅      | Fetch con cancel.                                                                      |
| Validación con `react-hook-form` + `zod` | ❌  | Instalados pero no usados. Sprint 2.                                                   |

---

## Cosas eliminadas (limpieza Sprint 0)

- ❌ Endpoint público `POST /api/tenants/` — ahora se crea vía signup-con-código.
- ❌ Integraciones mock: Airbnb API, Booking.com API, Channel Manager, Stripe, Mailchimp.
  Quedó **sólo** Google Calendar como placeholder real para implementar.
- ❌ Función `registerNewTenant`/`registerJoinTenant` en el frontend → reemplazadas
  por `register()` único.
- ❌ Función `createTenant` en el frontend → no aplica más.
- ❌ Función `updateTenantInvitationCode` en el frontend → reemplazada por
  `createInvitationCode` / `deactivateInvitationCode`.
- ❌ US relacionadas con pasarelas de pago — borradas de `user_stories.md`.
- ❌ Campo legacy `branding_config.invitation_code` — **no es usado más** en
  validación de signup, queda solo por compatibilidad de los tenants existentes
  (se ignora). El nuevo flujo es 100% `InvitationCode` model.
