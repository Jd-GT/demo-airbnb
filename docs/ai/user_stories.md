# Historias de Usuario y Épicas (SaaS PMS)

> **Notas de scope (actualizadas 2026-05-13)**
>
> - **No se integran pasarelas de pago.** Los pagos son **manuales**: el cliente paga
>   por WhatsApp/transferencia/efectivo y el operador los registra a posteriori
>   en el sistema. Cualquier US que mencionara Stripe, PayPal o "pago en línea"
>   fue eliminada. Sólo registramos los pagos que ya ocurrieron por fuera.
> - **Acceso por código.** Nadie puede crear una empresa nueva en la plataforma
>   sin un `CREATE_TENANT` invitation code emitido por el super-admin.
>   Igualmente, nadie se une a una empresa existente sin un `JOIN_TENANT` code
>   emitido por el dueño/admin de esa empresa. Ver Épica 0.
> - **Integraciones externas:** sólo Google Calendar queda como integración
>   real planeada. Airbnb / Booking / Stripe / Mailchimp se eliminaron del
>   producto (eran mocks de UI sin backend real).

---

## ÉPICA 0: Acceso Controlado a la Plataforma (Plataforma SaaS)
**Descripción:** Como Operador del SaaS, necesito controlar quién entra a la plataforma para evitar que cualquier persona cree una cuenta sin autorización.

*   [x] **US-0.1: Modelo de InvitationCode con propósito CREATE_TENANT / JOIN_TENANT**
*   [x] **US-0.2: Eliminar el endpoint público `POST /api/tenants/`**
*   [x] **US-0.3: Bloquear el flujo de signup público sin código válido**
*   [x] **US-0.4: Django Admin para que el super-admin emita y revoque CREATE_TENANT codes y active/desactive tenants**
*   [x] **US-0.5: Endpoint REST `/tenants/{id}/invitation-codes/` para que los OWNER emitan JOIN_TENANT codes**
*   [x] **US-0.6: Comando CLI `manage.py issue_invite_code` para super-admin**
*   [x] **US-0.7: Tenant.is_active enforced por TenantResolutionMiddleware (un tenant inactivo no puede operar)**

---

## ÉPICA 1: Gestión Centralizada del Inventario y CRM
**Descripción:** Como Host, necesito dejar de usar Excel para gestionar mis propiedades, tarifas y la base de datos de mis clientes, para tener una única fuente de verdad accesible desde cualquier lugar.

*   [x] **US-1.1: Creación de Propiedades** — backend CRUD listo (`/inventory/properties/`). Falta el formulario en el frontend (sólo hay listado).
    *   **Como** Administrador del Tenant.
    *   **Quiero** poder registrar una nueva propiedad llenando su nombre, dirección, capacidad (adultos/niños), tarifa base y tarifa de limpieza.
    *   **Para** tener mi inventario digitalizado y listo para recibir reservas.
*   [x] **US-1.1.1: Agregar usuarios con permisos a cada tenant** — backend listo (`TenantRole` + `TenantUserViewSet` con RBAC). Falta UI de matriz de permisos.
    *   **Como** Administrador del Tenant.
    *   **Quiero** poder crear nuevos usuarios para mi inmobiliaria y asignarles permisos específicos (Ej: solo lectura, editor de reservas, administrador total).
    *   **Para** que mi equipo pueda colaborar en la plataforma sin compartir contraseñas ni dar acceso irrestricto a todo el sistema.
*   [x] **US-1.2: Gestión de Comodidades (Amenities)** — backend CRUD listo. Falta UI.
    *   **Como** Staff/Administrador.
    *   **Quiero** asignar características (WiFi, Piscina, AC) a cada propiedad.
    *   **Para** que la información detallada esté disponible al enviar cotizaciones a los clientes.
*   [x] **US-1.3: Base de Datos Única de Contactos** — backend CRUD + búsqueda por nombre/email/phone. Falta UI.
*   [x] **US-1.4: Pipeline de Ventas (Leads / Cotizaciones)** — backend CRUD listo (`/crm/leads/`). Falta UI tipo Kanban.
*   [x] **US-1.5: Tarifas Dinámicas por Temporada** — implementada en Sprint 2. Modelo `PriceRule` con `is_percent`, `min_nights`, `priority`, M2M opcional a propiedades. `calculate_quote()` itera por noche aplicando la regla ganadora. Endpoint `/booking/price-rules/` CRUD.

---

## ÉPICA 2: Motor de Reservas y Calendario Unificado
**Descripción:** Como Host, necesito un sistema que cruce la disponibilidad y me permita crear reservas completas (con sus cobros adicionales y comisiones) sin riesgo de "overbooking".

*   [ ] **US-2.1: Calendario General de Ocupación** — el frontend tiene una vista mensual de sólo lectura. Falta vista tipo Gantt + drag & drop.
*   [x] **US-2.2: Creación de Reserva Manual (Directa)** — backend listo (`POST /booking/reservations/`) con validación de disponibilidad. Falta UI.
*   [x] **US-2.3: Validación de Overbooking** — implementada en `check_availability()`.
*   [x] **US-2.4: Desglose de Cobros (Líneas de Reserva)** — Sprint 2. Modelo `ReservationLine` (NIGHT/FEE/EXTRA/DISCOUNT) con M2M a `Tax`. Auto-generadas al crear reserva.
*   [x] **US-2.5: Asignación de Comisiones a Intermediarios** — Sprint 2. `agent_commission` se calcula automáticamente sobre `subtotal × agent.commission_rate` y se devenga como línea analítica de categoría COMMISSION.
*   [ ] **US-2.6: Calendario integrado con Google Calendar** — pendiente. Sólo está el placeholder de integración (`google_calendar`).

---

## ÉPICA 3: Control Financiero y Reportes de Rentabilidad (P&L)
**Descripción:** Como Host, necesito saber exactamente cuánto entra, cuánto sale, quién me debe dinero, y si un apartamento específico es rentable o está dando pérdidas.

*   [x] **US-3.1: Registro de Anticipos (Caja)** — Sprint 3. Modelo `Payment` con type=ADVANCE. Backend + UI `/pagos`.
*   [x] **US-3.2: Cobro de Saldos (Check-in)** — Sprint 3. type=BALANCE. `payment_status` se recalcula automáticamente.
*   [x] **US-3.3: Impuestos Configurables** — Sprint 3. Modelo `Tax` (PERCENT/FIXED) + endpoint CRUD. Aplicable a `ReservationLine` vía M2M.
*   [x] **US-3.4: Creación de Centros de Costo (Cuentas Analíticas)** — Sprint 3. `AnalyticAccount` con `OneToOne` a `Property`. Auto-creado en `Property.save()`.
*   [x] **US-3.5: Devengo Automático de Ingresos** — Sprint 3. `accrue_reservation_income()` crea la línea INCOME al confirmar la reserva. Idempotente. También crea la línea COMMISSION si hay agente.
*   [x] **US-3.6: Registro de Gastos Operativos** — Sprint 3. Endpoint `/finance/expenses/` + UI en `/contabilidad`. Categorías: CLEANING_COST, MAINTENANCE, UTILITIES, COMMISSION, OTHER_EXPENSE.
*   [x] **US-3.7: Reporte de Rentabilidad por Propiedad (P&L)** — Sprint 3. Endpoint `/finance/profit-and-loss/` y UI `/contabilidad`. Export Excel.
*   [x] **US-3.8: Reporte de Ocupación y revenue mensual** — `FinanceAnalyticsView` + `get_property_month_metrics` (incluye ADR). Export Excel `/finance/reports/occupancy.xlsx`.

---

## ÉPICA 4: Automatización Operativa y Comunicación
**Descripción:** Como Host, necesito reducir el tiempo de tareas mecánicas (avisar de limpiezas, enviar confirmaciones por WhatsApp) para enfocarme en crecer el negocio.

*   [ ] **US-4.1: Generación de Tareas de Limpieza** — pendiente. Falta el modelo `Task`.
*   [ ] **US-4.2: Notificación al Personal (Dashboard CLEANER)** — pendiente. El `system_role=CLEANER` ya está en el modelo `User`, falta vista filtrada.
*   [ ] **US-4.3: Plantillas de Correo/Mensajes** — pendiente.
*   [ ] **US-4.4: Envío de Confirmación de Reserva** — pendiente.
*   [ ] **US-4.5: Descarga de Voucher PDF** — pendiente. Requiere WeasyPrint en backend.

---

## ÉPICA 5: Requerimientos No Funcionales (NFRs)
**Descripción:** Como Arquitecto/Propietario, necesito que el sistema sea seguro, rápido, escalable y mantenible para garantizar la continuidad del negocio y la protección de datos, sin importar cuántas propiedades o Tenants se agreguen.

*   [x] **NFR-5.1: Aislamiento de Datos (Multitenancy)** — `TenantAwareManager` + `TenantResolutionMiddleware` + `TenantModulePermission`. Tests automatizados validan que un OWNER no puede operar en otro tenant ni leer códigos de invitación ajenos.
*   [ ] **NFR-5.2: Rendimiento y Tiempos de Carga** — pendiente. No hay caché, no hay benchmarks. Postgres index básicos en multi-tenant.
*   [ ] **NFR-5.3: Trazabilidad y Auditoría (Logs)** — pendiente. No está integrado `django-simple-history`.
*   [ ] **NFR-5.4: Disponibilidad (Uptime)** — pendiente. No hay infra desplegada todavía.
*   [x] **NFR-5.5: Seguridad y Privacidad de Datos** — passwords con bcrypt (default Django). `Tenant.integration_config` se oculta a usuarios no-OWNER. La rotación / cifrado a nivel de DB de tokens externos queda pendiente.
*   [ ] **NFR-5.6: Diseño Responsivo (Mobile-First)** — frontend usa Tailwind con utilidades responsive, falta auditoría sistemática.

---

## Estado de Sprints

| Sprint | Foco | Estado |
| --- | --- | --- |
| **Sprint 0** | Acceso controlado (Épica 0) + UX de signup + privacidad de settings | ✅ Completo (2026-05-13) |
| **Sprint 1** | Inventario, CRM, Reservas básicas, RBAC | ✅ Backend completo. Frontend mayoritariamente lectura. |
| **Sprint 2** | Motor de tarifas dinámicas (`PriceRule`), líneas de reserva, comisiones, taxes | ✅ Backend completo (2026-05-14). Frontend de calendario drag&drop, wizard nueva reserva, CRUD UI de PriceRule/Tax y Google Calendar real **pendientes**. |
| **Sprint 3** | Pagos manuales, contabilidad analítica, P&L, Excel | ✅ Backend + frontend completos (2026-05-14). |
| **Sprint 4** | Tareas de limpieza, vista CLEANER, plantillas, voucher PDF, Google Calendar real | ⏳ Pendiente |
| **Sprint 5** | NFRs (auditoría, encriptación tokens, despliegue cloud) | ⏳ Pendiente |
