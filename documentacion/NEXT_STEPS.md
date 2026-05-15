# Próximos pasos (Roadmap para el próximo dev/IA)

> Este documento es para que arranques sin perder tiempo decidiendo qué
> hacer. Está priorizado por valor de negocio + dependencias técnicas.
> Cuando completes algo, actualiza también `STATE.md` y
> `docs/ai/user_stories.md`.

## Cómo usar esto

1. Lee `README.md` y `STATE.md` primero (5 min).
2. Lee `ARCHITECTURE.md` y `AUTH_FLOW.md` (15 min).
3. Elige el siguiente bloque de "Sprint" pendiente.
4. Antes de codear, verifica que las premisas en `STATE.md` no han
   cambiado.

---

## Sprint 1.5 (lo que faltó pulir del Sprint 1)

**Estimación:** 1-2 días.

- [ ] Frontend: formulario de **crear/editar Property** con `react-hook-form`
      + `zod`. El backend ya soporta POST/PUT/PATCH/DELETE.
- [ ] Frontend: gestión de **Amenities** (CRUD) y picker de amenities
      en el form de Property.
- [ ] Frontend: páginas `/contactos` y `/leads` con CRUD. El backend ya
      soporta búsqueda en contactos.
- [ ] Frontend: convertir Lead → Reservation (botón en Lead).
- [ ] Frontend: matriz de permisos visual para crear/editar `TenantRole`
      (un grid de módulo × nivel con radios).
- [ ] Frontend: invitar usuarios desde `/settings` directamente (POST a
      `/users/`) además del flujo con código.

---

## Sprint 2 — Motor de reservas profesional

**Estimación:** 2 semanas.

> **Estado a 2026-05-14:** ✅ Backend completo. ⏳ Frontend (calendario
> interactivo, wizard nueva reserva, página de PriceRules y Taxes) y
> Google Calendar OAuth real **PENDIENTES**.

### Backend

- [x] **Modelo `PriceRule`** (épica 1, US-1.5).
  - Campos: `name`, `tenant`, `start_date`, `end_date`, `price_modifier`
    (decimal con flag `is_percent` o un `multiplier`/`fixed_delta`),
    `min_nights`, `applicable_property_ids` (M2M, vacío = todas),
    `specific_days_of_week` (JSON, opcional), `priority` (int para
    desempate cuando aplican varias).
  - Endpoint `/booking/price-rules/` CRUD.
  - Modificar `services.calculate_quote()` para que considere reglas
    activas que crucen el rango.
- [x] **Modelo `ReservationLine`** (épica 2, US-2.4).
  - Campos: `reservation`, `type` (NIGHT|FEE|EXTRA), `description`,
    `quantity`, `unit_price`, `tax_ids` (FK to Tax, M2M).
  - Al crear reserva, generar líneas automáticas (1 NIGHT por noche,
    1 FEE para limpieza). Soportar líneas EXTRA manuales.
  - El `total_amount` ahora se calcula como suma de líneas + impuestos.
- [x] **Modelo `Tax`** (épica 3, US-3.3).
  - Campos: `tenant`, `name`, `value`, `type` (PERCENT|FIXED), `is_active`.
- [x] **Comisiones de agente** (épica 2, US-2.5).
  - Cuando una `Reservation.agent` está set, calcular
    `agent_commission = subtotal * agent.commission_rate / 100`.
  - Guardar como campo computed o como `ReservationLine` invertido.
- [ ] **Calendar overlap visual**: endpoint `/booking/calendar?from=&to=`
      que devuelva un mapa propiedad → días bloqueados (más eficiente
      que el listado actual de reservations).

### Frontend

- [ ] Calendario interactivo (FullCalendar o react-big-calendar) con
      drag-and-drop para mover/extender reservas.
- [ ] Wizard "Nueva Reserva" en pasos: Propiedad → Fechas → Cotización
      (con desglose) → Cliente → Confirmación.
- [ ] Página de gestión de `PriceRule`s.
- [ ] Página de gestión de `Tax`es.

### Integración Google Calendar

- [ ] Backend: configurar `google-auth-oauthlib` y endpoint
      `/integrations/google/oauth-init/` que devuelva la URL de Google.
- [ ] Backend: callback `/integrations/google/oauth-callback/` que
      guarda el refresh_token cifrado en `Tenant.integration_config`.
- [ ] Backend: tarea (Celery o cronjob) que sincronice reservas
      confirmadas → eventos del calendario.
- [ ] Backend: webhook de Google → si alguien crea un evento allí,
      crear un Lead o Reservation DRAFT en el sistema.
- [ ] Frontend: botón "Conectar Google Calendar" en `/integraciones`.

---

## Sprint 3 — Finanzas y reportes

**Estimación:** 2 semanas.

> **Estado a 2026-05-14:** ✅ Backend y frontend completos. Pendiente
> sólo: ADR/RevPAR explícito en endpoint de analytics, voucher PDF
> (queda en Sprint 4) y export PDF de P&L (opcional).

- [x] **Modelo `Payment`** (épica 3, US-3.1, US-3.2).
  - Campos: `tenant`, `reservation`, `date`, `amount`, `type`
    (ADVANCE|BALANCE|REFUND), `method` (CASH|TRANSFER|OTHER), `reference`
    (texto libre — número de comprobante), `recorded_by` (User).
  - Sin pasarelas online. Registro manual a posteriori.
  - Endpoint `/finance/payments/` CRUD.
  - `Reservation.amount_paid` y `payment_status` se actualizan
    automáticamente al crear/borrar pagos.
- [x] **Modelos `AnalyticAccount` + `AnalyticLine`** (épica 3, US-3.4 a 3.7).
  - Al crear `Property`, se crea su `AnalyticAccount` automáticamente.
  - Al confirmar reserva, se crea `AnalyticLine` positivo (INCOME).
  - Endpoint `/finance/expenses/` para gastos manuales (líneas negativas).
  - Endpoint `/finance/profit-and-loss/?account_id=&from_date=&to_date=`.
- [x] **Reportes Excel** con openpyxl: `/finance/reports/pnl.xlsx`,
      `/occupancy.xlsx`, `/payments.xlsx`.
- [ ] **ADR (Average Daily Rate)** y **RevPAR**: ADR ya se calcula en
      `get_property_month_metrics`, falta exponerlo en el endpoint global.

### Frontend

- [x] Página `/pagos` con form de registro y listado.
- [x] Página `/contabilidad` con P&L por cost center, gastos manuales y
      botones de descarga Excel.
- [x] Sidebar con los nuevos links.
- [ ] Página `/tarifas-dinamicas` (CRUD UI de PriceRule). Backend ya
      existe; falta la pantalla.
- [ ] Página `/impuestos` (CRUD UI de Tax). Backend listo.

---

## Sprint 4 — Operaciones y comunicación

**Estimación:** 1.5 semanas.

> **Estado a 2026-05-14:** ✅ COMPLETO (backend + frontend). Lo único
> que queda es el sync real de Google Calendar (sólo el adapter está
> hecho, falta el OAuth real + worker).

- [x] **Modelo `Task`** (épica 4, US-4.1 / US-4.2). En `apps/ops`.
- [x] **Auto-creación al checkout** vía `ensure_cleaning_task_for_reservation`.
- [x] **Vista CLEANER** en frontend: sidebar reducido + página `/tareas`
      filtrada automáticamente.
- [x] **Modelo `MessageTemplate`** (épica 4, US-4.3 / US-4.4) con
      placeholders. Endpoint `/ops/render-message/` y página `/plantillas`.
- [x] **Voucher PDF** (US-4.5) usando `reportlab`. Endpoint
      `/ops/voucher/<id>.pdf` y botón en `/plantillas`.
- [ ] **Google Calendar sync real**: el modelo `GoogleCalendarCredential`
      y el adapter ya existen. Falta:
  - Registrar la app en Google Cloud Console.
  - Endpoint `/integrations/google-calendar/oauth-init/` que devuelva
    la URL de Google.
  - Callback `/integrations/google-calendar/oauth-callback/` que cambie
    el `code` por `refresh_token` y lo guarde cifrado.
  - Implementar `GoogleCalendarAdapter.sync_reservation()` con la
    Calendar API.
  - Webhook reverso (Google → nuestro server) para crear Lead/Reservation
    cuando alguien crea evento manualmente en Google.

---

## Sprint 5 — Hardening y despliegue

**Estimación:** 1.5 semanas.

> **Estado a 2026-05-14:** ✅ Hardening completo. Falta sólo el deploy
> a AWS (ver `DEPLOYMENT.md`) y monitoring opcional.

- [x] **Auditoría con `django-simple-history`** (NFR-5.3). `HistoricalRecords`
      en `Tenant`, `TenantRole`, `User`, `InvitationCode`, `Reservation`,
      `Payment`. `HistoryRequestMiddleware` captura `history_user`.
- [ ] **Endpoint REST `/audit/?model=&object_id=`** — pendiente. Por
      ahora se consulta vía Django Admin.
- [x] **Encriptación de tokens** (NFR-5.5): `apps/core/crypto.py` con
      Fernet. `GoogleCalendarCredential.refresh_token_encrypted` lo usa.
      Para extender a `integration_config` arbitrario, basta envolver
      el setter del JSONField con `encrypt_secret()`.
- [x] **Rate limiting** (`django-ratelimit`): 10/min en login, 5/h en
      signup. Auto-off en tests.
- [x] **Healthcheck** `/healthz` para liveness probe.
- [ ] **Deployment a AWS** (NFR-5.4). Ver `DEPLOYMENT.md` para la guía.
- [ ] **Monitoring**: Sentry DSN como env var (configurable). CloudWatch
      Log Group apuntando al stdout del container.
- [ ] **CSP / security headers** vía middleware (`django-csp`). Configurar
      `SECURE_*` flags en producción.
- [ ] **Rotación de keys**: documentar el procedimiento para rotar
      `DJANGO_FERNET_KEY` (re-cifrar todos los tokens existentes con
      una key vieja → nueva).

---

## Cosas a NO hacer (decisiones tomadas)

- ❌ NO integrar pasarelas de pago (Stripe, PayPal). Acordado con el
      cliente. Pagos son siempre manuales.
- ❌ NO permitir signup público sin código. Es por diseño de negocio.
- ❌ NO añadir más integraciones OTA (Airbnb, Booking) hasta que las
      anteriores demuestren ROI. Empezamos con Google Calendar y vemos.
- ❌ NO hacer microservicios. Monolito modular es suficiente para el
      tamaño actual del equipo.
- ❌ NO usar Celery hasta que haya un job real que justifique el costo
      de infra (broker + workers). Para tareas de limpieza basta un
      cronjob sencillo.
